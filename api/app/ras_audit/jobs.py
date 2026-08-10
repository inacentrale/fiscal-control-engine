from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.agent_persistence.models import (
    RasAuditCandidateJobModel,
    RasAuditCaseModel,
    RasAuditRunModel,
)

RAS_JOB_MAX_CONCURRENCY = 4
RAS_JOB_MAX_ATTEMPTS = 3
RAS_JOB_LEASE_SECONDS = 60


class RasCandidateJobError(ValueError):
    pass


class RasCandidateJobState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RasCandidateJob:
    job_id: str
    audit_id: str
    candidate_id: str
    input_digest: str
    state: RasCandidateJobState
    attempt_count: int
    result_audit_id: str | None = None
    error_code: str | None = None
    updated_at: datetime | None = None


class RasCandidateJobRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        self._now = now

    def enqueue(
        self,
        *,
        audit_id: str,
        candidate_id: str,
        session_id: str | None,
        file_id: str | None,
        input_token: str,
    ) -> RasCandidateJob:
        digest = sha256(input_token.encode("utf-8")).hexdigest()
        with self._session_factory() as session:
            audit = session.get(RasAuditRunModel, audit_id)
            if audit is None:
                raise RasCandidateJobError("RAS audit was not found")
            if audit.session_id != session_id or audit.file_id != file_id:
                raise RasCandidateJobError("RAS audit access denied")
            candidate_exists = session.scalar(
                select(RasAuditCaseModel.case_id).where(
                    RasAuditCaseModel.audit_id == audit_id,
                    RasAuditCaseModel.candidate_id == candidate_id,
                )
            )
            if candidate_exists is None:
                raise RasCandidateJobError("candidate does not belong to RAS audit")
            existing = session.scalar(
                select(RasAuditCandidateJobModel).where(
                    RasAuditCandidateJobModel.audit_id == audit_id,
                    RasAuditCandidateJobModel.candidate_id == candidate_id,
                    RasAuditCandidateJobModel.input_digest == digest,
                )
            )
            if existing is not None:
                return _snapshot(existing)
            now = self._now()
            model = RasAuditCandidateJobModel(
                job_id=uuid4().hex,
                audit_id=audit_id,
                candidate_id=candidate_id,
                input_digest=digest,
                state=RasCandidateJobState.PENDING.value,
                attempt_count=0,
                created_at=now,
                updated_at=now,
            )
            session.add(model)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(
                    select(RasAuditCandidateJobModel).where(
                        RasAuditCandidateJobModel.audit_id == audit_id,
                        RasAuditCandidateJobModel.candidate_id == candidate_id,
                        RasAuditCandidateJobModel.input_digest == digest,
                    )
                )
                if existing is None:
                    raise
                return _snapshot(existing)
            return _snapshot(model)

    def claim(self, job_id: str) -> RasCandidateJob | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(RasAuditCandidateJobModel)
                .where(RasAuditCandidateJobModel.job_id == job_id)
                .with_for_update()
            )
            if model is None:
                return None
            now = self._now()
            reclaimable = (
                model.state == RasCandidateJobState.RUNNING.value
                and _as_utc(model.updated_at)
                <= now - timedelta(seconds=RAS_JOB_LEASE_SECONDS)
            )
            if model.state not in {
                RasCandidateJobState.PENDING.value,
                RasCandidateJobState.FAILED.value,
            } and not reclaimable:
                return None
            if model.attempt_count >= RAS_JOB_MAX_ATTEMPTS:
                return None
            model.state = RasCandidateJobState.RUNNING.value
            model.attempt_count += 1
            model.error_code = None
            model.updated_at = now
            session.commit()
            return _snapshot(model)

    def get(self, job_id: str) -> RasCandidateJob | None:
        with self._session_factory() as session:
            model = session.get(RasAuditCandidateJobModel, job_id)
            return _snapshot(model) if model is not None else None

    def complete(self, job_id: str, *, result_audit_id: str) -> RasCandidateJob:
        return self._finish(
            job_id,
            state=RasCandidateJobState.COMPLETED,
            result_audit_id=result_audit_id,
        )

    def fail(self, job_id: str, *, error_code: str) -> RasCandidateJob:
        return self._finish(
            job_id, state=RasCandidateJobState.FAILED, error_code=error_code
        )

    def cancel(self, job_id: str) -> RasCandidateJob:
        with self._session_factory() as session:
            model = session.scalar(
                select(RasAuditCandidateJobModel)
                .where(RasAuditCandidateJobModel.job_id == job_id)
                .with_for_update()
            )
            if model is None:
                raise RasCandidateJobError("RAS candidate job was not found")
            if model.state not in {
                RasCandidateJobState.PENDING.value,
                RasCandidateJobState.FAILED.value,
            }:
                raise RasCandidateJobError("RAS candidate job cannot be cancelled")
            model.state = RasCandidateJobState.CANCELLED.value
            model.updated_at = self._now()
            session.commit()
            return _snapshot(model)

    def _finish(
        self,
        job_id: str,
        *,
        state: RasCandidateJobState,
        result_audit_id: str | None = None,
        error_code: str | None = None,
    ) -> RasCandidateJob:
        with self._session_factory() as session:
            model = session.scalar(
                select(RasAuditCandidateJobModel)
                .where(RasAuditCandidateJobModel.job_id == job_id)
                .with_for_update()
            )
            if model is None or model.state != RasCandidateJobState.RUNNING.value:
                raise RasCandidateJobError("RAS candidate job is not running")
            model.state = state.value
            model.result_audit_id = result_audit_id
            model.error_code = error_code
            model.updated_at = self._now()
            session.commit()
            return _snapshot(model)


def run_candidate_jobs(
    jobs: Iterable[RasCandidateJob],
    worker: Callable[[RasCandidateJob], None],
    *,
    max_concurrency: int = RAS_JOB_MAX_CONCURRENCY,
) -> None:
    if not 1 <= max_concurrency <= RAS_JOB_MAX_CONCURRENCY:
        raise RasCandidateJobError("invalid RAS job concurrency")
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        tuple(executor.map(worker, jobs))


def _snapshot(model: RasAuditCandidateJobModel) -> RasCandidateJob:
    return RasCandidateJob(
        job_id=model.job_id,
        audit_id=model.audit_id,
        candidate_id=model.candidate_id,
        input_digest=model.input_digest,
        state=RasCandidateJobState(model.state),
        attempt_count=model.attempt_count,
        result_audit_id=model.result_audit_id,
        error_code=model.error_code,
        updated_at=_as_utc(model.updated_at),
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
