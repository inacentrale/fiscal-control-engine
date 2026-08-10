from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.ras_audit.candidate_detection import (
    RasCandidateAssessment,
    RasCandidateDetectionReport,
    RasCandidateStatus,
    candidate_requires_category_split,
)
from app.ras_audit.counterpart import (
    RasCounterpartAssessment,
    RasCounterpartReport,
    RasCounterpartStatus,
)
from app.ras_audit.domain import RasAuditStatus
from app.ras_audit.persistence import (
    RasAuditCaseSnapshot,
    RasAuditSnapshot,
    SqlAlchemyRasAuditRepository,
)
from app.ras_audit.workflow import RAS_WORKFLOW_CONTRACT_VERSION, RasWorkflowState


@dataclass(frozen=True)
class RasBatchAuditResult:
    audit_id: str
    candidate_count: int
    potential_count: int
    indeterminate_count: int
    status_counts: tuple[tuple[str, int], ...]
    review_candidate_ids: tuple[str, ...]
    remaining_candidate_count: int
    source_scope_complete: bool
    source_scope_blockers: tuple[str, ...]


@dataclass(frozen=True)
class RasBatchCandidateContext:
    period: str | None
    document_reference: str | None
    account_number: str | None
    operation_nature: str | None
    supplier_reference: str | None


class RasBatchAuditService:
    def __init__(
        self,
        repository: SqlAlchemyRasAuditRepository,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._now = now

    def persist(
        self,
        *,
        source_sha256: str,
        sheet_name: str,
        detection: RasCandidateDetectionReport,
        counterparts: RasCounterpartReport,
        reference_versions: tuple[str, ...],
        source_scope_complete: bool,
        source_scope_blockers: tuple[str, ...] = (),
        source_scope_policy_version: str = "ras-uploaded-sheet-scope-v2",
        session_id: str | None = None,
        file_id: str | None = None,
        candidate_contexts: dict[str, RasBatchCandidateContext] | None = None,
    ) -> RasBatchAuditResult:
        counterpart_by_id = {
            item.candidate_entry_id: item for item in counterparts.assessments
        }
        cases = tuple(
            _case(
                candidate,
                counterpart_by_id.get(candidate.accounting_entry_id),
                (candidate_contexts or {}).get(candidate.accounting_entry_id),
            )
            for candidate in detection.candidates
        )
        created_at = self._now()
        snapshot = RasAuditSnapshot(
            audit_id=uuid4().hex,
            session_id=session_id,
            file_id=file_id,
            source_sha256=source_sha256,
            status="candidate_inventory_pending_legal_facts",
            reference_versions=reference_versions,
            fact_context={
                "mode": "gl_only_batch",
                "sheet_name": sheet_name,
                "user_fact_values_applied": False,
                "source_scope_complete": source_scope_complete,
                "source_scope_blockers": list(source_scope_blockers),
                "source_scope_policy_version": source_scope_policy_version,
            },
            cases=cases,
            created_at=created_at,
        )
        equivalent = self._repository.find_equivalent(snapshot)
        if equivalent is None:
            self._repository.save(snapshot)
            audit_id = snapshot.audit_id
        else:
            audit_id = equivalent.audit_id
        counts = Counter(case.status for case in cases)
        return RasBatchAuditResult(
            audit_id=audit_id,
            candidate_count=len(cases),
            potential_count=sum(case.certainty == "potential" for case in cases),
            indeterminate_count=sum(
                case.certainty == "indeterminate" for case in cases
            ),
            status_counts=tuple(sorted(counts.items())),
            review_candidate_ids=tuple(case.candidate_id for case in cases[:20]),
            remaining_candidate_count=max(0, len(cases) - 20),
            source_scope_complete=source_scope_complete,
            source_scope_blockers=source_scope_blockers,
        )


def _case(
    candidate: RasCandidateAssessment,
    counterpart: RasCounterpartAssessment | None,
    context: RasBatchCandidateContext | None = None,
) -> RasAuditCaseSnapshot:
    is_indeterminate = candidate.status is RasCandidateStatus.INDETERMINATE or bool(
        candidate.missing_facts
    )
    status = (
        RasAuditStatus.INDETERMINATE.value
        if is_indeterminate
        else RasAuditStatus.APPLICABILITY_PROBABLE.value
    )
    certainty = "indeterminate" if is_indeterminate else "potential"
    missing_facts = tuple(
        sorted(
            set(candidate.missing_facts)
            | {"legal_facts_per_candidate"}
            | (
                {"candidate_requires_category_split"}
                if candidate_requires_category_split(candidate)
                else set()
            )
        )
    )
    issues = (
        (f"counterpart:{counterpart.status.value}", *counterpart.issues)
        if counterpart is not None
        else ("counterpart:not_evaluated_for_candidate",)
    )
    currency, recorded_amount = _single_recorded_amount(counterpart)
    return RasAuditCaseSnapshot(
        candidate_id=candidate.candidate_id,
        status=status,
        certainty=certainty,
        payload={
            "candidate_id": candidate.candidate_id,
            "status": status,
            "certainty": certainty,
            "rule_id": None,
            "rule_version": None,
            "expected_amount": None,
            "recorded_amount": recorded_amount,
            "difference": None,
            "currency": currency,
            "missing_facts": list(missing_facts),
            "issues": list(issues),
            "legal_source_locators": [],
            "basis_is_complete": False,
            "workflow_contract_version": RAS_WORKFLOW_CONTRACT_VERSION,
            "workflow_state": RasWorkflowState.AWAITING_FACTS.value,
            "candidate_status": candidate.status.value,
            "signal_ids": list(candidate.signal_ids),
            "operation_hints": list(candidate.operation_hints),
            "account_mapping_ids": list(candidate.account_mapping_ids),
            "period": context.period if context else None,
            "document_reference": context.document_reference if context else None,
            "account_number": context.account_number if context else None,
            "operation_nature": context.operation_nature if context else None,
            "supplier_reference": context.supplier_reference if context else None,
        },
    )


def _single_recorded_amount(
    counterpart: RasCounterpartAssessment | None,
) -> tuple[str | None, str | None]:
    if (
        counterpart is None
        or counterpart.status is not RasCounterpartStatus.FOUND_IN_SAME_ENTRY
        or len(counterpart.recorded_amounts) != 1
    ):
        return None, None
    amount = counterpart.recorded_amounts[0]
    return amount.currency, str(amount.amount)
