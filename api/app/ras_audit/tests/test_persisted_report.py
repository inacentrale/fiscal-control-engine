from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, create_database_engine, create_session_factory
from app.ras_audit.persisted_report import (
    PersistedRasAuditReportError,
    PersistedRasAuditReportService,
)
from app.ras_audit.persistence import (
    RasAuditCaseSnapshot,
    RasAuditSnapshot,
    SqlAlchemyRasAuditRepository,
)


def test_generates_report_only_from_persisted_cases(tmp_path: Path) -> None:
    repository = SqlAlchemyRasAuditRepository(_session_factory(tmp_path))
    repository.save(_audit(_case_payload()))

    report = PersistedRasAuditReportService(repository).generate("audit-1")
    repeated = PersistedRasAuditReportService(repository).generate("audit-1")

    assert report.case_count == 1
    assert report.amount_summaries[0].expected_amount == 5000
    assert report.recorded_amount_summaries[0].recorded_amount == 5000
    assert report.details[0].candidate_id == "entry-1"
    assert repeated.report_id == report.report_id
    assert [event.event_type for event in repository.list_events("audit-1")] == [
        "audit_created",
        "report_generated",
        "report_generated",
    ]


def test_rejects_corrupted_persisted_case(tmp_path: Path) -> None:
    repository = SqlAlchemyRasAuditRepository(_session_factory(tmp_path))
    payload = _case_payload()
    payload["expected_amount"] = "not-a-number"
    repository.save(_audit(payload))

    with pytest.raises(PersistedRasAuditReportError, match="invalid"):
        PersistedRasAuditReportService(repository).generate("audit-1")


def _audit(payload: dict[str, object]) -> RasAuditSnapshot:
    return RasAuditSnapshot(
        audit_id="audit-1",
        source_sha256="a" * 64,
        status="completed_provisional",
        reference_versions=("legal-v1",),
        fact_context={"message_sha256": "b" * 64},
        cases=(
            RasAuditCaseSnapshot(
                candidate_id="entry-1",
                status="provisional_reconciled",
                certainty="supported_provisional",
                payload=payload,
            ),
        ),
        created_at=datetime(2026, 8, 4, tzinfo=UTC),
    )


def _case_payload() -> dict[str, object]:
    return {
        "candidate_id": "entry-1",
        "status": "provisional_reconciled",
        "certainty": "supported_provisional",
        "rule_id": "resident-standard",
        "rule_version": "legal-v1",
        "expected_amount": "5000",
        "recorded_amount": "5000",
        "difference": "0",
        "currency": "XOF",
        "missing_facts": [],
        "issues": [],
        "legal_source_locators": ["CGI:article"],
        "basis_is_complete": True,
    }


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'report.db'}")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)
