from dataclasses import dataclass, replace
from enum import StrEnum

from app.ras_audit.persistence import RasAuditCaseSnapshot, SqlAlchemyRasAuditRepository

RAS_WORKFLOW_CONTRACT_VERSION = "1.0.0"


class RasWorkflowError(ValueError):
    pass


class RasWorkflowStatusError(ValueError):
    pass


class RasWorkflowState(StrEnum):
    DETECTED = "detected"
    AWAITING_FACTS = "awaiting_facts"
    RULE_RESOLVED = "rule_resolved"
    CALCULATED = "calculated"
    COUNTERPART_ASSESSED = "counterpart_assessed"
    REPORTED = "reported"
    BLOCKED = "blocked"
    FAILED = "failed"


_ALLOWED_TRANSITIONS: dict[RasWorkflowState, frozenset[RasWorkflowState]] = {
    RasWorkflowState.DETECTED: frozenset(
        {
            RasWorkflowState.AWAITING_FACTS,
            RasWorkflowState.RULE_RESOLVED,
            RasWorkflowState.BLOCKED,
            RasWorkflowState.FAILED,
        }
    ),
    RasWorkflowState.AWAITING_FACTS: frozenset(
        {
            RasWorkflowState.RULE_RESOLVED,
            RasWorkflowState.BLOCKED,
            RasWorkflowState.FAILED,
        }
    ),
    RasWorkflowState.RULE_RESOLVED: frozenset(
        {
            RasWorkflowState.CALCULATED,
            RasWorkflowState.AWAITING_FACTS,
            RasWorkflowState.BLOCKED,
            RasWorkflowState.FAILED,
        }
    ),
    RasWorkflowState.CALCULATED: frozenset(
        {
            RasWorkflowState.COUNTERPART_ASSESSED,
            RasWorkflowState.BLOCKED,
            RasWorkflowState.FAILED,
        }
    ),
    RasWorkflowState.COUNTERPART_ASSESSED: frozenset(
        {RasWorkflowState.REPORTED, RasWorkflowState.FAILED}
    ),
    RasWorkflowState.REPORTED: frozenset(),
    RasWorkflowState.BLOCKED: frozenset(),
    RasWorkflowState.FAILED: frozenset(),
}


@dataclass(frozen=True)
class RasWorkflowCase:
    candidate_id: str
    state: RasWorkflowState = RasWorkflowState.DETECTED
    missing_facts: tuple[str, ...] = ()
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise RasWorkflowError("candidate id is required")
        if any(not fact.strip() for fact in self.missing_facts):
            raise RasWorkflowError("missing fact names cannot be blank")
        if self.state is RasWorkflowState.AWAITING_FACTS and not self.missing_facts:
            raise RasWorkflowError("awaiting facts requires missing facts")
        if self.state in {RasWorkflowState.BLOCKED, RasWorkflowState.FAILED} and (
            self.reason_code is None or not self.reason_code.strip()
        ):
            raise RasWorkflowError("blocked and failed states require a reason")

    def transition(
        self,
        target: RasWorkflowState,
        *,
        missing_facts: tuple[str, ...] = (),
        reason_code: str | None = None,
    ) -> "RasWorkflowCase":
        if target not in _ALLOWED_TRANSITIONS[self.state]:
            raise RasWorkflowError(
                f"invalid RAS workflow transition: {self.state} -> {target}"
            )
        return replace(
            self,
            state=target,
            missing_facts=tuple(sorted(set(missing_facts))),
            reason_code=reason_code,
        )


@dataclass(frozen=True)
class RasWorkflowCaseStatus:
    candidate_id: str
    state: RasWorkflowState
    missing_facts: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class RasWorkflowAuditStatus:
    audit_id: str
    parent_audit_id: str | None
    status: str
    total_candidates: int
    page: int
    page_size: int
    report_available: bool
    cases: tuple[RasWorkflowCaseStatus, ...]


class RasAuditWorkflowService:
    def __init__(self, repository: SqlAlchemyRasAuditRepository) -> None:
        self._repository = repository

    def status(
        self,
        *,
        audit_id: str,
        session_id: str,
        file_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> RasWorkflowAuditStatus:
        if page < 1 or not 1 <= page_size <= 100:
            raise RasWorkflowStatusError("invalid RAS workflow pagination")
        snapshot = self._repository.get(audit_id.strip())
        if snapshot is None:
            raise RasWorkflowStatusError("RAS audit was not found")
        if snapshot.session_id != session_id or snapshot.file_id != file_id:
            raise RasWorkflowStatusError("RAS audit access denied")
        start = (page - 1) * page_size
        selected_cases = snapshot.cases[start : start + page_size]
        events = self._repository.list_events(snapshot.audit_id)
        return RasWorkflowAuditStatus(
            audit_id=snapshot.audit_id,
            parent_audit_id=snapshot.parent_audit_id,
            status=snapshot.status,
            total_candidates=len(snapshot.cases),
            page=page,
            page_size=page_size,
            report_available=any(
                event.event_type == "report_generated" for event in events
            ),
            cases=tuple(_case_status(case) for case in selected_cases),
        )


def workflow_state_from_assessment(output: dict[str, object]) -> RasWorkflowState:
    missing_facts = output.get("missing_facts")
    if isinstance(missing_facts, list) and missing_facts:
        return RasWorkflowState.AWAITING_FACTS
    calculation_status = output.get("calculation_status")
    resolution_status = output.get("legal_resolution_status")
    if calculation_status == "calculated_provisional":
        return RasWorkflowState.COUNTERPART_ASSESSED
    if resolution_status == "resolved_provisional":
        return RasWorkflowState.RULE_RESOLVED
    return RasWorkflowState.BLOCKED


def _case_status(case: RasAuditCaseSnapshot) -> RasWorkflowCaseStatus:
    missing_facts = _string_tuple(case.payload.get("missing_facts"))
    raw_state = case.payload.get("workflow_state")
    try:
        state = (
            RasWorkflowState(raw_state)
            if isinstance(raw_state, str)
            else (
                RasWorkflowState.AWAITING_FACTS
                if missing_facts
                else RasWorkflowState.DETECTED
            )
        )
    except ValueError as exc:
        raise RasWorkflowStatusError("invalid persisted RAS workflow state") from exc
    return RasWorkflowCaseStatus(
        candidate_id=case.candidate_id,
        state=state,
        missing_facts=missing_facts,
        status=case.status,
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return ()
    return tuple(sorted(set(value)))
