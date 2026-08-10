from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.ras_audit.jobs import (
    RAS_JOB_MAX_ATTEMPTS,
    RasCandidateJobError,
    RasCandidateJobRepository,
    RasCandidateJobState,
    run_candidate_jobs,
)
from app.ras_audit.persistence import (
    RasAuditCaseSnapshot,
    RasAuditSnapshot,
    SqlAlchemyRasAuditRepository,
)


def test_candidate_job_is_idempotent_retryable_and_cancellable() -> None:
    repository = _repository()
    first = repository.enqueue(
        audit_id="audit-1",
        candidate_id="candidate-1",
        session_id=None,
        file_id=None,
        input_token="attestation-1",
    )
    duplicate = repository.enqueue(
        audit_id="audit-1",
        candidate_id="candidate-1",
        session_id=None,
        file_id=None,
        input_token="attestation-1",
    )
    assert duplicate.job_id == first.job_id
    assert duplicate.input_digest != "attestation-1"

    claimed = repository.claim(first.job_id)
    assert claimed is not None
    assert claimed.state is RasCandidateJobState.RUNNING
    failed = repository.fail(first.job_id, error_code="temporary_failure")
    assert failed.state is RasCandidateJobState.FAILED
    assert repository.claim(first.job_id) is not None
    repository.fail(first.job_id, error_code="temporary_failure")
    assert repository.claim(first.job_id) is not None
    repository.fail(first.job_id, error_code="temporary_failure")
    assert repository.claim(first.job_id) is None
    assert failed.attempt_count < RAS_JOB_MAX_ATTEMPTS

    cancellable = repository.enqueue(
        audit_id="audit-1",
        candidate_id="candidate-2",
        session_id=None,
        file_id=None,
        input_token="attestation-2",
    )
    cancelled = repository.cancel(cancellable.job_id)
    assert cancelled.state is RasCandidateJobState.CANCELLED
    assert repository.claim(cancellable.job_id) is None


def test_candidate_job_completion_and_bounded_runner() -> None:
    repository = _repository()
    jobs = tuple(
        repository.enqueue(
            audit_id="audit-1",
            candidate_id=f"candidate-{index}",
            session_id=None,
            file_id=None,
            input_token=f"attestation-{index}",
        )
        for index in range(1, 4)
    )
    processed: set[str] = set()

    def worker(job: object) -> None:
        assert hasattr(job, "job_id")
        processed.add(job.job_id)

    run_candidate_jobs(jobs, worker, max_concurrency=2)
    assert processed == {job.job_id for job in jobs}
    claimed = repository.claim(jobs[0].job_id)
    assert claimed is not None
    completed = repository.complete(
        jobs[0].job_id, result_audit_id="derived-audit-1"
    )
    assert completed.state is RasCandidateJobState.COMPLETED
    assert completed.result_audit_id == "derived-audit-1"
    assert repository.claim(jobs[0].job_id) is None

    with pytest.raises(RasCandidateJobError, match="concurrency"):
        run_candidate_jobs(jobs, worker, max_concurrency=5)


def test_candidate_job_rejects_wrong_scope_or_candidate() -> None:
    repository = _repository()
    with pytest.raises(RasCandidateJobError, match="access denied"):
        repository.enqueue(
            audit_id="audit-1",
            candidate_id="candidate-1",
            session_id="other-session",
            file_id=None,
            input_token="attestation",
        )


def test_interrupted_running_job_is_reclaimed_after_lease_timeout() -> None:
    clock = [datetime(2026, 8, 10, tzinfo=UTC)]
    repository = _repository(now=lambda: clock[0])
    job = repository.enqueue(
        audit_id="audit-1",
        candidate_id="candidate-1",
        session_id=None,
        file_id=None,
        input_token="attestation",
    )
    first_claim = repository.claim(job.job_id)
    assert first_claim is not None
    assert repository.claim(job.job_id) is None

    clock[0] += timedelta(seconds=61)
    reclaimed = repository.claim(job.job_id)
    assert reclaimed is not None
    assert reclaimed.attempt_count == 2
    with pytest.raises(RasCandidateJobError, match="does not belong"):
        repository.enqueue(
            audit_id="audit-1",
            candidate_id="unknown",
            session_id=None,
            file_id=None,
            input_token="attestation",
        )


def _repository(
    now: Callable[[], datetime] | None = None,
) -> RasCandidateJobRepository:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    SqlAlchemyRasAuditRepository(session_factory).save(
        RasAuditSnapshot(
            audit_id="audit-1",
            source_sha256="a" * 64,
            status="pending",
            reference_versions=("rules-v1",),
            fact_context={},
            cases=(
                *(
                    RasAuditCaseSnapshot(
                        candidate_id=f"candidate-{index}",
                        status="pending",
                        certainty="indeterminate",
                        payload={},
                    )
                    for index in range(1, 4)
                ),
            ),
            created_at=datetime(2026, 8, 10, tzinfo=UTC),
        )
    )
    if now is None:
        return RasCandidateJobRepository(session_factory)
    return RasCandidateJobRepository(session_factory, now=now)
