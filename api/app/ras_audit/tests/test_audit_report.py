from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.ras_audit.accounting_assessment import (
    RasAccountingAssessment,
    RasAccountingAssessmentStatus,
)
from app.ras_audit.audit_report import (
    RasAuditReportCase,
    RasAuditReportGenerator,
    RasReportCertainty,
)
from app.ras_audit.rule_resolution import (
    RasRuleEvidence,
    RasRuleResolution,
    RasRuleResolutionStatus,
)
from app.ras_audit.theoretical_calculation import (
    RasTheoreticalCalculation,
    RasTheoreticalCalculationStatus,
)

SOURCE_HASH = "a" * 64


def test_report_separates_currencies_and_certainty_levels() -> None:
    report = RasAuditReportGenerator().generate(
        source_sha256=SOURCE_HASH,
        cases=(
            _case("CANDIDATE-XOF", "XOF", "5000", "4000", complete=True),
            _case("CANDIDATE-USD", "USD", "200", "200", complete=True),
            _case("CANDIDATE-POTENTIAL", "XOF", "1000", "1000", potential=True),
            _case("CANDIDATE-UNKNOWN", None, None, None, complete=False),
        ),
        reference_versions=("rules-v1", "policy-v1"),
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert report.case_count == 4
    assert dict(report.certainty_counts) == {
        "indeterminate": 1,
        "potential": 1,
        "supported_provisional": 2,
    }
    summaries = {
        (summary.certainty, summary.currency): summary
        for summary in report.amount_summaries
    }
    assert (
        summaries[
            (RasReportCertainty.SUPPORTED_PROVISIONAL, "XOF")
        ].difference
        == -1000
    )
    assert summaries[(RasReportCertainty.SUPPORTED_PROVISIONAL, "USD")].difference == 0
    assert summaries[(RasReportCertainty.POTENTIAL, "XOF")].case_count == 1
    assert len(summaries) == 3
    recorded_summaries = {
        (summary.certainty, summary.currency): summary
        for summary in report.recorded_amount_summaries
    }
    assert (
        recorded_summaries[
            (RasReportCertainty.SUPPORTED_PROVISIONAL, "XOF")
        ].recorded_amount
        == 4000
    )
    assert (
        recorded_summaries[
            (RasReportCertainty.POTENTIAL, "XOF")
        ].recorded_amount
        == 1000
    )


def test_report_summarizes_recorded_amounts_even_without_expected_amount() -> None:
    detail = RasAuditReportGenerator().generate(
        source_sha256=SOURCE_HASH,
        cases=(_case("CANDIDATE-OPEN", "XOF", None, "2500", complete=False),),
        reference_versions=("rules-v1",),
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert detail.amount_summaries == ()
    assert detail.recorded_amount_summaries[0].recorded_amount == 2500


def test_report_identifier_is_reproducible_and_order_independent() -> None:
    cases = (
        _case("CANDIDATE-B", "XOF", "5000", "5000", complete=True),
        _case("CANDIDATE-A", "XOF", "1000", "0", complete=True),
    )
    generator = RasAuditReportGenerator()

    first = generator.generate(
        source_sha256=SOURCE_HASH,
        cases=cases,
        reference_versions=("policy-v1", "rules-v1"),
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    second = generator.generate(
        source_sha256=SOURCE_HASH,
        cases=tuple(reversed(cases)),
        reference_versions=("rules-v1", "policy-v1"),
        generated_at=datetime(2026, 2, 1, tzinfo=UTC),
    )

    assert first.report_id == second.report_id
    assert tuple(detail.candidate_id for detail in first.details) == (
        "CANDIDATE-A",
        "CANDIDATE-B",
    )


def test_report_identifier_changes_with_trace_or_completeness() -> None:
    generator = RasAuditReportGenerator()
    original = generator.generate(
        source_sha256=SOURCE_HASH,
        cases=(_case("CANDIDATE-A", "XOF", "5000", "5000", complete=True),),
        reference_versions=("rules-v1", "policy-v1"),
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    changed_detail = replace(
        original.details[0],
        issues=("new_accounting_issue",),
        basis_is_complete=False,
    )
    changed = generator.generate_from_details(
        source_sha256=SOURCE_HASH,
        details=(changed_detail,),
        reference_versions=("rules-v1", "policy-v1"),
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert original.report_id != changed.report_id


def test_json_and_csv_exports_preserve_trace_without_raw_ledger_cells() -> None:
    report = RasAuditReportGenerator().generate(
        source_sha256=SOURCE_HASH,
        cases=(_case("HASHED-CANDIDATE", "XOF", "5000", "4000", complete=True),),
        reference_versions=("rules-v1",),
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    generator = RasAuditReportGenerator()

    json_export = generator.to_json(report)
    csv_export = generator.to_csv(report)

    assert "HASHED-CANDIDATE" in json_export
    assert "article 207" in json_export
    assert "HASHED-CANDIDATE" in csv_export
    assert "expected_amount" in csv_export
    assert "SYN-TIERS" not in json_export + csv_export
    assert "Honoraires confidentiels" not in json_export + csv_export


def test_report_rejects_duplicate_candidates() -> None:
    case = _case("DUPLICATE", "XOF", "5000", "5000", complete=True)

    with pytest.raises(ValueError, match="duplicate"):
        RasAuditReportGenerator().generate(
            source_sha256=SOURCE_HASH,
            cases=(case, case),
            reference_versions=("rules-v1",),
        )


def _case(
    candidate_id: str,
    currency: str | None,
    expected: str | None,
    recorded: str | None,
    *,
    complete: bool = False,
    potential: bool = False,
) -> RasAuditReportCase:
    expected_amount = Decimal(expected) if expected is not None else None
    recorded_amount = Decimal(recorded) if recorded is not None else None
    difference = (
        recorded_amount - expected_amount
        if expected_amount is not None and recorded_amount is not None
        else None
    )
    status = (
        RasAccountingAssessmentStatus.POTENTIAL_RELATED_ENTRY
        if potential
        else (
            RasAccountingAssessmentStatus.PROVISIONAL_RECONCILED
            if difference == 0
            else (
                RasAccountingAssessmentStatus.PROVISIONAL_AMOUNT_MISMATCH
                if difference is not None
                else RasAccountingAssessmentStatus.INDETERMINATE
            )
        )
    )
    assessment = RasAccountingAssessment(
        status=status,
        candidate_entry_id=candidate_id,
        expected_amount=expected_amount,
        recorded_amount=recorded_amount,
        difference=difference,
        currency=currency,
        tolerance=Decimal("0") if complete else None,
        policy_version="policy-v1" if complete else None,
        missing_facts=() if complete else ("confirmed_document_link",),
        issues=(),
        potential_adjustments_present=False,
        basis_is_complete=complete,
    )
    resolution = RasRuleResolution(
        status=RasRuleResolutionStatus.RESOLVED_PROVISIONAL,
        rule_id="RULE-1",
        rule_version="rules-v1",
        calculation_method="flat_rate",
        rate_percent=Decimal("5"),
        missing_facts=(),
        alternative_rule_ids=(),
        evidence=(
            RasRuleEvidence(
                source_kind="rate",
                source_url="https://example.invalid/legal-source",
                source_locator="article 207",
                source_sha256="b" * 64,
            ),
        ),
        source_assurance="synthetic",
        fact_sources=(("currency", "gl"),),
    )
    calculation = RasTheoreticalCalculation(
        status=(
            RasTheoreticalCalculationStatus.CALCULATED_PROVISIONAL
            if expected_amount is not None
            else RasTheoreticalCalculationStatus.NOT_CALCULABLE
        ),
        rule_id="RULE-1" if expected_amount is not None else None,
        rule_version="rules-v1" if expected_amount is not None else None,
        base_fact_name="tax_base_amount" if expected_amount is not None else None,
        base_amount=expected_amount,
        expected_amount=expected_amount,
        currency=currency,
        calculation_method="flat_rate" if expected_amount is not None else None,
        rate_percent=Decimal("5") if expected_amount is not None else None,
        steps=(),
        parameter_versions=(),
        source_locators=("article 207",) if expected_amount is not None else (),
        rounding_policy="none_exact_decimal",
        reason=None if expected_amount is not None else "missing_facts",
    )
    return RasAuditReportCase(
        candidate_id=candidate_id,
        assessment=assessment,
        resolution=resolution,
        calculation=calculation,
    )
