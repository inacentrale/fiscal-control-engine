from decimal import Decimal
from pathlib import Path

from app.ras_audit.accounting_assessment import (
    RasAccountingAssessmentStatus,
    RasAccountingAssessor,
    load_ras_accounting_assessment_policies,
)
from app.ras_audit.counterpart import (
    RasCounterpartAmount,
    RasCounterpartAssessment,
    RasCounterpartStatus,
)
from app.ras_audit.theoretical_calculation import (
    RasCalculationStep,
    RasTheoreticalCalculation,
    RasTheoreticalCalculationStatus,
)

ROOT = Path(__file__).resolve().parents[4]


def _assessor() -> RasAccountingAssessor:
    return RasAccountingAssessor(
        load_ras_accounting_assessment_policies(
            ROOT / "docs/reference/ras-accounting-assessment-policy.csv"
        )
    )


def test_reconciles_exact_amount_in_same_piece() -> None:
    result = _assessor().assess(
        calculation=_calculation("5000", "XOF"),
        counterpart=_counterpart(
            RasCounterpartStatus.FOUND_IN_SAME_ENTRY,
            (RasCounterpartAmount("XOF", Decimal("5000")),),
        ),
    )

    assert result.status is RasAccountingAssessmentStatus.PROVISIONAL_RECONCILED
    assert result.difference == 0
    assert result.basis_is_complete is True
    assert result.policy_version == "1.0.0"


def test_reports_amount_mismatch_without_applying_adjustment_implicitly() -> None:
    counterpart = _counterpart(
        RasCounterpartStatus.FOUND_IN_SAME_ENTRY,
        (RasCounterpartAmount("XOF", Decimal("4000")),),
        potential_adjustments=(RasCounterpartAmount("XOF", Decimal("1000")),),
    )

    result = _assessor().assess(
        calculation=_calculation("5000", "XOF"),
        counterpart=counterpart,
    )

    assert result.status is RasAccountingAssessmentStatus.PROVISIONAL_AMOUNT_MISMATCH
    assert result.recorded_amount == 4_000
    assert result.difference == -1_000
    assert result.potential_adjustments_present is True
    assert "partial_ras_recorded" in result.issues


def test_qualifies_over_withholding_and_net_reversal_separately() -> None:
    over = _assessor().assess(
        calculation=_calculation("5000", "XOF"),
        counterpart=_counterpart(
            RasCounterpartStatus.FOUND_IN_SAME_ENTRY,
            (RasCounterpartAmount("XOF", Decimal("6000")),),
        ),
    )
    reversed_amount = _assessor().assess(
        calculation=_calculation("5000", "XOF"),
        counterpart=_counterpart(
            RasCounterpartStatus.FOUND_IN_SAME_ENTRY,
            (RasCounterpartAmount("XOF", Decimal("-1000")),),
        ),
    )

    assert "ras_recorded_above_expected" in over.issues
    assert "net_ras_reversal_exceeds_recording" in reversed_amount.issues


def test_reports_ras_not_found_only_from_complete_counterpart_scope() -> None:
    result = _assessor().assess(
        calculation=_calculation("5000", "XOF"),
        counterpart=_counterpart(RasCounterpartStatus.NOT_FOUND_IN_SCOPE, ()),
    )

    assert result.status is RasAccountingAssessmentStatus.PROVISIONAL_RAS_NOT_FOUND
    assert result.recorded_amount == 0
    assert result.difference == -5_000
    assert result.basis_is_complete is True


def test_zero_expected_and_no_counterpart_is_reconciled() -> None:
    result = _assessor().assess(
        calculation=_calculation(
            "0",
            "XOF",
            status=RasTheoreticalCalculationStatus.EXEMPTION_PROVISIONAL,
        ),
        counterpart=_counterpart(RasCounterpartStatus.NOT_FOUND_IN_SCOPE, ()),
    )

    assert result.status is RasAccountingAssessmentStatus.PROVISIONAL_RECONCILED
    assert result.difference == 0


def test_keeps_related_piece_unconfirmed() -> None:
    result = _assessor().assess(
        calculation=_calculation("5000", "XOF"),
        counterpart=_counterpart(
            RasCounterpartStatus.POTENTIAL_RELATED_ENTRY,
            (RasCounterpartAmount("XOF", Decimal("5000")),),
            issues=("document_link_not_confirmed",),
        ),
    )

    assert result.status is RasAccountingAssessmentStatus.POTENTIAL_RELATED_ENTRY
    assert result.basis_is_complete is False
    assert result.missing_facts == ("confirmed_document_link",)


def test_refuses_cross_currency_comparison() -> None:
    result = _assessor().assess(
        calculation=_calculation("5000", "XOF"),
        counterpart=_counterpart(
            RasCounterpartStatus.FOUND_IN_SAME_ENTRY,
            (RasCounterpartAmount("EUR", Decimal("8")),),
        ),
    )

    assert result.status is RasAccountingAssessmentStatus.CURRENCY_MISMATCH
    assert result.difference is None


def test_incomplete_calculation_stays_indeterminate() -> None:
    calculation = RasTheoreticalCalculation(
        status=RasTheoreticalCalculationStatus.NOT_CALCULABLE,
        rule_id=None,
        rule_version=None,
        base_fact_name=None,
        base_amount=None,
        expected_amount=None,
        currency=None,
        calculation_method=None,
        rate_percent=None,
        steps=(),
        parameter_versions=(),
        source_locators=(),
        rounding_policy="not_applicable",
        reason="legal_rule_is_not_resolved",
    )

    result = _assessor().assess(
        calculation=calculation,
        counterpart=_counterpart(RasCounterpartStatus.NOT_FOUND_IN_SCOPE, ()),
    )

    assert result.status is RasAccountingAssessmentStatus.INDETERMINATE
    assert result.missing_facts == ("legal_rule_is_not_resolved",)


def _calculation(
    amount: str,
    currency: str,
    *,
    status: RasTheoreticalCalculationStatus = (
        RasTheoreticalCalculationStatus.CALCULATED_PROVISIONAL
    ),
) -> RasTheoreticalCalculation:
    expected = Decimal(amount)
    return RasTheoreticalCalculation(
        status=status,
        rule_id="SYN-RULE",
        rule_version="v1",
        base_fact_name="tax_base_amount",
        base_amount=Decimal("100000"),
        expected_amount=expected,
        currency=currency,
        calculation_method="flat_rate",
        rate_percent=Decimal("5"),
        steps=(RasCalculationStep("flat_rate", "base * rate / 100", expected),),
        parameter_versions=(),
        source_locators=("synthetic-source",),
        rounding_policy="none_exact_decimal",
        reason=None,
    )


def _counterpart(
    status: RasCounterpartStatus,
    amounts: tuple[RasCounterpartAmount, ...],
    *,
    potential_adjustments: tuple[RasCounterpartAmount, ...] = (),
    issues: tuple[str, ...] = (),
) -> RasCounterpartAssessment:
    return RasCounterpartAssessment(
        candidate_entry_id="SYN-CANDIDATE",
        expense_line_ids=("SYN-EXPENSE",),
        status=status,
        counterpart_line_ids=tuple(
            f"SYN-RAS-{index}" for index, _ in enumerate(amounts)
        ),
        recorded_amounts=amounts,
        potential_adjustment_line_ids=tuple(
            f"SYN-ADJUST-{index}"
            for index, _ in enumerate(potential_adjustments)
        ),
        potential_adjustment_amounts=potential_adjustments,
        missing_facts=(),
        issues=issues,
    )
