from datetime import UTC, datetime

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


def test_generates_report_only_from_persisted_cases() -> None:
    repository = SqlAlchemyRasAuditRepository(_session_factory())
    repository.save(_audit(_case_payload()))

    report = PersistedRasAuditReportService(repository).generate("audit-1")
    repeated = PersistedRasAuditReportService(repository).generate("audit-1")

    assert report.case_count == 1
    assert report.amount_summaries[0].expected_amount == 5000
    assert report.recorded_amount_summaries[0].recorded_amount == 5000
    assert report.details[0].candidate_id == "entry-1"
    assert report.details[0].period == "2026-P08"
    assert report.details[0].tax_base_amount == 100000
    assert report.details[0].rate_percent == 5
    assert report.details[0].action_code == "document_review"
    assert repeated.report_id == report.report_id
    assert [event.event_type for event in repository.list_events("audit-1")] == [
        "audit_created",
        "report_generated",
        "report_generated",
    ]


def test_rejects_corrupted_persisted_case() -> None:
    repository = SqlAlchemyRasAuditRepository(_session_factory())
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
        "period": "2026-P08",
        "document_reference": "entry-1",
        "account_number": "622100",
        "operation_nature": "service_any",
        "tax_event": "payment_date:2026-08-01",
        "tax_base_amount": "100000",
        "rate_percent": "5",
        "tolerance": "0",
        "status_label": "RAS rapprochee provisoirement",
        "review_priority": "normal",
        "action_code": "document_review",
        "explanation": "Montant dans la tolerance.",
        "missing_fact_labels": [],
        "issue_labels": [],
    }


def _session_factory() -> sessionmaker[Session]:
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)
