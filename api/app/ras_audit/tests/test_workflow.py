from datetime import UTC, datetime

import pytest

from app.database import Base, create_database_engine, create_session_factory
from app.ras_audit.persistence import (
    RasAuditCaseSnapshot,
    RasAuditSnapshot,
    SqlAlchemyRasAuditRepository,
)
from app.ras_audit.workflow import (
    RAS_WORKFLOW_CONTRACT_VERSION,
    RasAuditWorkflowService,
    RasWorkflowCase,
    RasWorkflowError,
    RasWorkflowState,
    RasWorkflowStatusError,
    workflow_state_from_assessment,
)


def test_workflow_contract_has_stable_semantic_version() -> None:
    assert RAS_WORKFLOW_CONTRACT_VERSION == "1.0.0"


def test_candidate_waits_for_explicit_missing_facts_then_progresses() -> None:
    detected = RasWorkflowCase(candidate_id="candidate-1")

    waiting = detected.transition(
        RasWorkflowState.AWAITING_FACTS,
        missing_facts=("residence", "tax_event_date"),
    )
    resolved = waiting.transition(RasWorkflowState.RULE_RESOLVED)
    calculated = resolved.transition(RasWorkflowState.CALCULATED)
    assessed = calculated.transition(RasWorkflowState.COUNTERPART_ASSESSED)
    reported = assessed.transition(RasWorkflowState.REPORTED)

    assert reported.state is RasWorkflowState.REPORTED
    assert reported.missing_facts == ()


def test_workflow_rejects_skipping_deterministic_steps() -> None:
    detected = RasWorkflowCase(candidate_id="candidate-1")

    with pytest.raises(RasWorkflowError, match="invalid RAS workflow transition"):
        detected.transition(RasWorkflowState.REPORTED)


def test_workflow_requires_reasons_and_missing_facts() -> None:
    with pytest.raises(RasWorkflowError, match="awaiting facts"):
        RasWorkflowCase(
            candidate_id="candidate-1",
            state=RasWorkflowState.AWAITING_FACTS,
        )
    with pytest.raises(RasWorkflowError, match="require a reason"):
        RasWorkflowCase(
            candidate_id="candidate-1",
            state=RasWorkflowState.FAILED,
        )


@pytest.mark.parametrize(
    ("output", "expected"),
    (
        ({"missing_facts": ["residence"]}, RasWorkflowState.AWAITING_FACTS),
        (
            {
                "missing_facts": [],
                "legal_resolution_status": "resolved_provisional",
                "calculation_status": "calculated_provisional",
            },
            RasWorkflowState.COUNTERPART_ASSESSED,
        ),
        (
            {
                "missing_facts": [],
                "legal_resolution_status": "resolved_provisional",
                "calculation_status": "not_calculable",
            },
            RasWorkflowState.RULE_RESOLVED,
        ),
        ({"missing_facts": []}, RasWorkflowState.BLOCKED),
    ),
)
def test_derives_state_from_deterministic_assessment(
    output: dict[str, object],
    expected: RasWorkflowState,
) -> None:
    assert workflow_state_from_assessment(output) is expected


def test_workflow_status_is_scoped_paginated_and_reports_missing_facts() -> None:
    repository = _repository()
    repository.save(
        RasAuditSnapshot(
            audit_id="audit-1",
            source_sha256="a" * 64,
            status="candidate_inventory_pending_legal_facts",
            reference_versions=("rules-v1",),
            fact_context={},
            cases=(
                _snapshot_case("candidate-1", "awaiting_facts"),
                _snapshot_case("candidate-2", "detected"),
            ),
            created_at=datetime(2026, 8, 10, tzinfo=UTC),
            session_id="session-1",
            file_id="file-1",
        )
    )
    repository.append_event(
        "audit-1",
        event_type="report_generated",
        metadata={"report_id": "report-1"},
    )
    service = RasAuditWorkflowService(repository)

    status = service.status(
        audit_id="audit-1",
        session_id="session-1",
        file_id="file-1",
        page=1,
        page_size=1,
    )

    assert status.total_candidates == 2
    assert status.report_available is True
    assert [case.candidate_id for case in status.cases] == ["candidate-1"]
    assert status.cases[0].state is RasWorkflowState.AWAITING_FACTS
    assert status.cases[0].missing_facts == ("residence",)

    with pytest.raises(RasWorkflowStatusError, match="access denied"):
        service.status(
            audit_id="audit-1",
            session_id="other-session",
            file_id="file-1",
        )


def _repository() -> SqlAlchemyRasAuditRepository:
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SqlAlchemyRasAuditRepository(create_session_factory(engine))


def _snapshot_case(candidate_id: str, state: str) -> RasAuditCaseSnapshot:
    missing_facts = ["residence"] if state == "awaiting_facts" else []
    return RasAuditCaseSnapshot(
        candidate_id=candidate_id,
        status="indeterminate_missing_data",
        certainty="indeterminate",
        payload={
            "candidate_id": candidate_id,
            "workflow_state": state,
            "missing_facts": missing_facts,
        },
    )
