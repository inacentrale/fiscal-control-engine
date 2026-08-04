import csv
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path

from app.ras_audit.counterpart import (
    RasCounterpartAssessment,
    RasCounterpartStatus,
)
from app.ras_audit.rule_resolution import RasRuleResolution
from app.ras_audit.theoretical_calculation import (
    RasTheoreticalCalculation,
    RasTheoreticalCalculationStatus,
)


class RasAccountingAssessmentError(ValueError):
    pass


class RasAccountingAssessmentStatus(StrEnum):
    PROVISIONAL_RECONCILED = "provisional_reconciled"
    PROVISIONAL_AMOUNT_MISMATCH = "provisional_amount_mismatch"
    PROVISIONAL_RAS_NOT_FOUND = "provisional_ras_not_found_in_gl"
    POTENTIAL_RELATED_ENTRY = "potential_related_entry"
    CURRENCY_MISMATCH = "currency_mismatch"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class RasAccountingAssessmentPolicy:
    version: str
    currency: str
    tolerance: Decimal
    policy_kind: str
    notes: str


@dataclass(frozen=True)
class RasAccountingAssessment:
    status: RasAccountingAssessmentStatus
    candidate_entry_id: str
    expected_amount: Decimal | None
    recorded_amount: Decimal | None
    difference: Decimal | None
    currency: str | None
    tolerance: Decimal | None
    policy_version: str | None
    missing_facts: tuple[str, ...]
    issues: tuple[str, ...]
    potential_adjustments_present: bool
    basis_is_complete: bool


@dataclass(frozen=True)
class RasAccountingAssessmentToolReport:
    sheet_name: str
    source_row_count: int
    rejected_row_count: int
    source_scope_complete: bool
    resolution: RasRuleResolution
    calculation: RasTheoreticalCalculation
    assessment: RasAccountingAssessment


def load_ras_accounting_assessment_policies(
    path: Path,
) -> tuple[RasAccountingAssessmentPolicy, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            _validate_columns(reader.fieldnames)
            policies = tuple(
                _parse_policy(row, row_number)
                for row_number, row in enumerate(reader, start=2)
            )
    except OSError as exc:
        raise RasAccountingAssessmentError(
            "RAS accounting assessment policy cannot be read"
        ) from exc
    if not policies:
        raise RasAccountingAssessmentError("RAS accounting policy is empty")
    if len({policy.currency for policy in policies}) != len(policies):
        raise RasAccountingAssessmentError("duplicate RAS accounting currency policy")
    return policies


class RasAccountingAssessor:
    def __init__(
        self,
        policies: tuple[RasAccountingAssessmentPolicy, ...],
    ) -> None:
        if not policies:
            raise ValueError("RAS accounting assessment policies are required")
        self._policies = {policy.currency: policy for policy in policies}

    def assess(
        self,
        *,
        calculation: RasTheoreticalCalculation,
        counterpart: RasCounterpartAssessment,
    ) -> RasAccountingAssessment:
        if calculation.status is RasTheoreticalCalculationStatus.NOT_CALCULABLE:
            return self._indeterminate(
                counterpart,
                missing_facts=(calculation.reason or "theoretical_calculation",),
            )
        if calculation.expected_amount is None or calculation.currency is None:
            return self._indeterminate(
                counterpart,
                missing_facts=("theoretical_amount_or_currency",),
            )
        if counterpart.status is RasCounterpartStatus.INDETERMINATE:
            return self._indeterminate(
                counterpart,
                missing_facts=counterpart.missing_facts,
                issues=counterpart.issues,
            )
        if counterpart.status is RasCounterpartStatus.POTENTIAL_RELATED_ENTRY:
            return RasAccountingAssessment(
                status=RasAccountingAssessmentStatus.POTENTIAL_RELATED_ENTRY,
                candidate_entry_id=counterpart.candidate_entry_id,
                expected_amount=calculation.expected_amount,
                recorded_amount=_amount_for_currency(
                    counterpart,
                    calculation.currency,
                ),
                difference=None,
                currency=calculation.currency,
                tolerance=None,
                policy_version=None,
                missing_facts=("confirmed_document_link",),
                issues=counterpart.issues,
                potential_adjustments_present=bool(
                    counterpart.potential_adjustment_amounts
                ),
                basis_is_complete=False,
            )
        currencies = {amount.currency for amount in counterpart.recorded_amounts}
        if currencies and currencies != {calculation.currency}:
            return RasAccountingAssessment(
                status=RasAccountingAssessmentStatus.CURRENCY_MISMATCH,
                candidate_entry_id=counterpart.candidate_entry_id,
                expected_amount=calculation.expected_amount,
                recorded_amount=None,
                difference=None,
                currency=calculation.currency,
                tolerance=None,
                policy_version=None,
                missing_facts=("same_currency_counterpart",),
                issues=counterpart.issues,
                potential_adjustments_present=bool(
                    counterpart.potential_adjustment_amounts
                ),
                basis_is_complete=False,
            )
        recorded = _amount_for_currency(counterpart, calculation.currency)
        if counterpart.status is RasCounterpartStatus.NOT_FOUND_IN_SCOPE:
            recorded = Decimal("0")
        if recorded is None:
            return self._indeterminate(
                counterpart,
                missing_facts=("recorded_ras_amount",),
            )
        policy = self._policies.get(calculation.currency) or self._policies.get("*")
        if policy is None:
            return self._indeterminate(
                counterpart,
                missing_facts=("accounting_tolerance_policy",),
            )
        difference = recorded - calculation.expected_amount
        reconciled = abs(difference) <= policy.tolerance
        if reconciled:
            status = RasAccountingAssessmentStatus.PROVISIONAL_RECONCILED
        elif counterpart.status is RasCounterpartStatus.NOT_FOUND_IN_SCOPE:
            status = RasAccountingAssessmentStatus.PROVISIONAL_RAS_NOT_FOUND
        else:
            status = RasAccountingAssessmentStatus.PROVISIONAL_AMOUNT_MISMATCH
        issues = (
            *counterpart.issues,
            *_difference_issues(recorded, calculation.expected_amount),
        )
        return RasAccountingAssessment(
            status=status,
            candidate_entry_id=counterpart.candidate_entry_id,
            expected_amount=calculation.expected_amount,
            recorded_amount=recorded,
            difference=difference,
            currency=calculation.currency,
            tolerance=policy.tolerance,
            policy_version=policy.version,
            missing_facts=(),
            issues=issues,
            potential_adjustments_present=bool(
                counterpart.potential_adjustment_amounts
            ),
            basis_is_complete=(
                counterpart.status
                in {
                    RasCounterpartStatus.FOUND_IN_SAME_ENTRY,
                    RasCounterpartStatus.NOT_FOUND_IN_SCOPE,
                }
            ),
        )
    def _indeterminate(
        self,
        counterpart: RasCounterpartAssessment,
        *,
        missing_facts: tuple[str, ...],
        issues: tuple[str, ...] = (),
    ) -> RasAccountingAssessment:
        return RasAccountingAssessment(
            status=RasAccountingAssessmentStatus.INDETERMINATE,
            candidate_entry_id=counterpart.candidate_entry_id,
            expected_amount=None,
            recorded_amount=None,
            difference=None,
            currency=None,
            tolerance=None,
            policy_version=None,
            missing_facts=missing_facts,
            issues=issues,
            potential_adjustments_present=bool(
                counterpart.potential_adjustment_amounts
            ),
            basis_is_complete=False,
        )


def _difference_issues(
    recorded: Decimal,
    expected: Decimal,
) -> tuple[str, ...]:
    if recorded < 0:
        return ("net_ras_reversal_exceeds_recording",)
    if Decimal("0") < recorded < expected:
        return ("partial_ras_recorded",)
    if recorded > expected:
        return ("ras_recorded_above_expected",)
    return ()


def _amount_for_currency(
    counterpart: RasCounterpartAssessment,
    currency: str,
) -> Decimal | None:
    amounts = tuple(
        item.amount
        for item in counterpart.recorded_amounts
        if item.currency == currency
    )
    return sum(amounts, Decimal("0")) if amounts else None


def _parse_policy(
    row: dict[str, str | None],
    row_number: int,
) -> RasAccountingAssessmentPolicy:
    values = {key: (value or "").strip() for key, value in row.items()}
    if any(not values[field] for field in _required_columns()):
        raise RasAccountingAssessmentError(
            f"incomplete RAS accounting policy at row {row_number}"
        )
    try:
        tolerance = Decimal(values["tolerance"])
    except InvalidOperation as exc:
        raise RasAccountingAssessmentError(
            f"invalid RAS accounting tolerance at row {row_number}"
        ) from exc
    if not tolerance.is_finite() or tolerance < 0:
        raise RasAccountingAssessmentError(
            f"invalid RAS accounting tolerance at row {row_number}"
        )
    return RasAccountingAssessmentPolicy(
        version=values["version"],
        currency=values["currency"].upper(),
        tolerance=tolerance,
        policy_kind=values["policy_kind"],
        notes=values["notes"],
    )


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    missing = _required_columns() - set(fieldnames or ())
    if missing:
        raise RasAccountingAssessmentError(
            f"missing accounting policy columns: {', '.join(sorted(missing))}"
        )


def _required_columns() -> set[str]:
    return {"version", "currency", "tolerance", "policy_kind", "notes"}
