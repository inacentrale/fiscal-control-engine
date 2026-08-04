from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.agent_persistence.models import (
    RasAuditCaseModel,
    RasAuditEventModel,
    RasAuditRunModel,
)


@dataclass(frozen=True)
class RasAuditCaseSnapshot:
    candidate_id: str
    status: str
    certainty: str
    payload: dict[str, object]

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.status.strip():
            raise ValueError("RAS audit case identity and status are required")
        if self.certainty not in {
            "supported_provisional",
            "potential",
            "indeterminate",
        }:
            raise ValueError("invalid RAS audit case certainty")


@dataclass(frozen=True)
class RasAuditSnapshot:
    audit_id: str
    source_sha256: str
    status: str
    reference_versions: tuple[str, ...]
    fact_context: dict[str, object]
    cases: tuple[RasAuditCaseSnapshot, ...]
    created_at: datetime
    session_id: str | None = None
    file_id: str | None = None
    parent_audit_id: str | None = None
    agent_run_id: str | None = None


@dataclass(frozen=True)
class RasAuditEventSnapshot:
    sequence: int
    event_type: str
    metadata: dict[str, object]
    created_at: datetime


class SqlAlchemyRasAuditRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        self._now = now

    def save(self, snapshot: RasAuditSnapshot) -> None:
        _validate_snapshot(snapshot)
        with self._session_factory() as session:
            session.add(
                RasAuditRunModel(
                    audit_id=snapshot.audit_id,
                    parent_audit_id=snapshot.parent_audit_id,
                    agent_run_id=snapshot.agent_run_id,
                    session_id=snapshot.session_id,
                    file_id=snapshot.file_id,
                    source_sha256=snapshot.source_sha256,
                    status=snapshot.status,
                    reference_versions=list(snapshot.reference_versions),
                    fact_context=snapshot.fact_context,
                    created_at=snapshot.created_at,
                )
            )
            for case in snapshot.cases:
                session.add(
                    RasAuditCaseModel(
                        case_id=uuid4().hex,
                        audit_id=snapshot.audit_id,
                        candidate_id=case.candidate_id,
                        status=case.status,
                        certainty=case.certainty,
                        payload=case.payload,
                        created_at=snapshot.created_at,
                    )
                )
            session.add(
                RasAuditEventModel(
                    event_id=uuid4().hex,
                    audit_id=snapshot.audit_id,
                    sequence=0,
                    event_type=(
                        "audit_derived"
                        if snapshot.parent_audit_id is not None
                        else "audit_created"
                    ),
                    metadata_payload={
                        "status": snapshot.status,
                        "case_count": len(snapshot.cases),
                        "parent_audit_id": snapshot.parent_audit_id,
                    },
                    created_at=snapshot.created_at,
                )
            )
            session.commit()

    def get(self, audit_id: str) -> RasAuditSnapshot | None:
        with self._session_factory() as session:
            audit = session.get(RasAuditRunModel, audit_id)
            if audit is None:
                return None
            cases = session.scalars(
                select(RasAuditCaseModel)
                .where(RasAuditCaseModel.audit_id == audit_id)
                .order_by(RasAuditCaseModel.candidate_id)
            ).all()
            return RasAuditSnapshot(
                audit_id=audit.audit_id,
                parent_audit_id=audit.parent_audit_id,
                agent_run_id=audit.agent_run_id,
                source_sha256=audit.source_sha256,
                status=audit.status,
                reference_versions=tuple(audit.reference_versions),
                fact_context=dict(audit.fact_context),
                cases=tuple(
                    RasAuditCaseSnapshot(
                        candidate_id=case.candidate_id,
                        status=case.status,
                        certainty=case.certainty,
                        payload=dict(case.payload),
                    )
                    for case in cases
                ),
                created_at=_as_utc(audit.created_at),
                session_id=audit.session_id,
                file_id=audit.file_id,
            )

    def append_event(
        self,
        audit_id: str,
        *,
        event_type: str,
        metadata: dict[str, object],
    ) -> None:
        normalized_type = event_type.strip()
        if not normalized_type:
            raise ValueError("RAS audit event type is required")
        with self._session_factory() as session:
            audit = session.scalar(
                select(RasAuditRunModel)
                .where(RasAuditRunModel.audit_id == audit_id)
                .with_for_update()
            )
            if audit is None:
                raise ValueError("RAS audit was not found")
            last_sequence = session.scalar(
                select(func.max(RasAuditEventModel.sequence)).where(
                    RasAuditEventModel.audit_id == audit_id
                )
            )
            session.add(
                RasAuditEventModel(
                    event_id=uuid4().hex,
                    audit_id=audit_id,
                    sequence=(last_sequence if last_sequence is not None else -1) + 1,
                    event_type=normalized_type,
                    metadata_payload=metadata,
                    created_at=self._now(),
                )
            )
            session.commit()

    def list_events(self, audit_id: str) -> tuple[RasAuditEventSnapshot, ...]:
        with self._session_factory() as session:
            events = session.scalars(
                select(RasAuditEventModel)
                .where(RasAuditEventModel.audit_id == audit_id)
                .order_by(RasAuditEventModel.sequence)
            ).all()
            return tuple(
                RasAuditEventSnapshot(
                    sequence=event.sequence,
                    event_type=event.event_type,
                    metadata=dict(event.metadata_payload),
                    created_at=_as_utc(event.created_at),
                )
                for event in events
            )


def _validate_snapshot(snapshot: RasAuditSnapshot) -> None:
    digest = snapshot.source_sha256.strip().lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("invalid RAS audit source hash")
    if not snapshot.audit_id.strip() or not snapshot.status.strip():
        raise ValueError("RAS audit identity and status are required")
    if snapshot.created_at.tzinfo is None:
        raise ValueError("RAS audit timestamp must be timezone aware")
    if not snapshot.reference_versions:
        raise ValueError("RAS audit reference versions are required")
    candidate_ids = tuple(case.candidate_id for case in snapshot.cases)
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("duplicate RAS audit candidate")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
