from datetime import date
from decimal import Decimal
from pathlib import Path

from app.ras_audit.legal_rules import load_ras_legal_rules
from app.ras_audit.rule_resolution import (
    RasFactSource,
    RasLegalFact,
    RasRuleResolutionRequest,
    RasRuleResolutionStatus,
    RasRuleResolver,
)
from app.ras_audit.tax_event_rules import load_ras_tax_event_rules
from app.ras_audit.theoretical_calculation import (
    RasTheoreticalCalculation,
    RasTheoreticalCalculationStatus,
    RasTheoreticalCalculator,
    load_ras_calculation_parameters,
)

ROOT = Path(__file__).resolve().parents[4]
RULES = load_ras_legal_rules(
    ROOT / "docs/reference/bf-ras-legal-rules.csv",
    repository_root=ROOT,
)
PARAMETERS = load_ras_calculation_parameters(
    ROOT / "docs/reference/bf-ras-calculation-parameters.csv",
    repository_root=ROOT,
)
EVENT_RULES = load_ras_tax_event_rules(
    ROOT / "docs/reference/bf-ras-tax-event-rules.csv",
    repository_root=ROOT,
)


def test_calculates_flat_rate_with_decimal_and_explicit_currency() -> None:
    transaction_date = date(2026, 4, 1)
    facts = _facts(
        regime="resident",
        operation_type="service_any",
        residence_status="resident",
        ifu_status="registered",
        payer_type="eligible_service_payer",
        service_use_location="BF",
        exemption_status="not_exempt",
        tax_base_amount="100000.50",
        currency="XOF",
        payment_status="paid",
        payment_date="2026-04-01",
    )

    result = _calculate(transaction_date, facts)

    assert result.status is RasTheoreticalCalculationStatus.CALCULATED_PROVISIONAL
    assert result.base_amount == Decimal("100000.50")
    assert result.rate_percent == 5
    assert result.expected_amount == Decimal("5000.025")
    assert result.currency == "XOF"
    assert result.rounding_policy == "none_exact_decimal_source_rounding_unavailable"


def test_refuses_to_allocate_full_tax_base_to_partial_payment() -> None:
    transaction_date = date(2026, 4, 1)
    facts = _facts(
        regime="resident",
        operation_type="service_any",
        residence_status="resident",
        ifu_status="registered",
        payer_type="eligible_service_payer",
        service_use_location="BF",
        exemption_status="not_exempt",
        tax_base_amount="100000",
        payment_amount="40000",
        currency="XOF",
        payment_status="paid",
        payment_date="2026-04-01",
    )

    result = _calculate(transaction_date, facts)

    assert result.status is RasTheoreticalCalculationStatus.NOT_CALCULABLE
    assert result.reason == "partial_payment_tax_base_allocation_unresolved"
    assert result.expected_amount is None


def test_accepts_explicit_payment_equal_to_tax_base() -> None:
    transaction_date = date(2026, 4, 1)
    facts = _facts(
        regime="resident",
        operation_type="service_any",
        residence_status="resident",
        ifu_status="registered",
        payer_type="eligible_service_payer",
        service_use_location="BF",
        exemption_status="not_exempt",
        tax_base_amount="100000",
        payment_amount="100000",
        currency="XOF",
        payment_status="paid",
        payment_date="2026-04-01",
    )

    result = _calculate(transaction_date, facts)

    assert result.status is RasTheoreticalCalculationStatus.CALCULATED_PROVISIONAL
    assert result.expected_amount == 5000


def test_refuses_payment_amount_above_explicit_tax_base() -> None:
    transaction_date = date(2026, 4, 1)
    facts = _facts(
        regime="resident",
        operation_type="service_any",
        residence_status="resident",
        ifu_status="registered",
        payer_type="eligible_service_payer",
        service_use_location="BF",
        exemption_status="not_exempt",
        tax_base_amount="100000",
        payment_amount="120000",
        currency="XOF",
        payment_status="paid",
        payment_date="2026-04-01",
    )

    result = _calculate(transaction_date, facts)

    assert result.status is RasTheoreticalCalculationStatus.NOT_CALCULABLE
    assert result.reason == "payment_amount_exceeds_tax_base"


def test_calculates_nonresident_in_source_currency_without_conversion() -> None:
    transaction_date = date(2025, 4, 1)
    facts = _facts(
        regime="nonresident",
        operation_type="service_any",
        residence_status="nonresident",
        stable_establishment_status="false",
        payer_type="eligible_service_payer",
        service_use_location="BF",
        treaty_override_status="false",
        exemption_status="not_exempt",
        payment_amount="1000",
        currency="USD",
        payment_status="put_in_payment",
        payment_date="2025-04-01",
    )

    result = _calculate(transaction_date, facts)

    assert result.expected_amount == 200
    assert result.currency == "USD"


def test_calculates_irf_progressive_from_external_parameters() -> None:
    transaction_date = date(2025, 4, 1)
    facts = _facts(
        regime="rent",
        operation_type="real_estate_rental",
        payer_type="eligible_rent_tenant",
        exemption_status="not_exempt",
        gross_rent_excluding_vat="500000",
        currency="XOF",
        rent_accrual_status="accrued",
        tax_period_end_date="2025-04-01",
    )

    result = _calculate(transaction_date, facts)

    assert result.expected_amount == 55_500
    assert tuple(step.result for step in result.steps) == (
        Decimal("250000"),
        Decimal("18000"),
        Decimal("37500"),
    )
    assert result.parameter_versions == ("v2018",) * 4
    assert set(result.source_locators) == {"article 125", "article 126"}


def test_verified_exemption_calculates_zero_not_a_missing_amount() -> None:
    transaction_date = date(2025, 4, 1)
    facts = _facts(
        regime="resident",
        operation_type="service_any",
        residence_status="resident",
        payer_type="eligible_service_payer",
        service_use_location="BF",
        exemption_status="exempt",
        exemption_evidence="DGI-reference",
        tax_base_amount="900000",
        payment_amount="400000",
        currency="XOF",
    )

    result = _calculate(transaction_date, facts)

    assert result.status is RasTheoreticalCalculationStatus.EXEMPTION_PROVISIONAL
    assert result.expected_amount == 0
    assert result.base_amount == 900_000


def test_does_not_calculate_when_legal_resolution_is_incomplete() -> None:
    transaction_date = date(2026, 4, 1)
    facts = _facts(
        regime="resident",
        operation_type="service_any",
        residence_status="resident",
    )
    resolution = RasRuleResolver(RULES, EVENT_RULES).resolve(
        RasRuleResolutionRequest(transaction_date=transaction_date, facts=facts)
    )

    result = RasTheoreticalCalculator(
        rules=RULES,
        parameters=PARAMETERS,
    ).calculate(
        transaction_date=transaction_date,
        facts=facts,
        resolution=resolution,
    )

    assert resolution.status is RasRuleResolutionStatus.MISSING_FACTS
    assert result.status is RasTheoreticalCalculationStatus.NOT_CALCULABLE
    assert result.expected_amount is None
    assert result.reason == "legal_rule_is_not_resolved"


def test_refuses_rent_calculation_in_wrong_currency() -> None:
    transaction_date = date(2025, 4, 1)
    facts = _facts(
        regime="rent",
        operation_type="real_estate_rental",
        payer_type="eligible_rent_tenant",
        exemption_status="not_exempt",
        gross_rent_excluding_vat="500000",
        currency="EUR",
        rent_accrual_status="accrued",
        tax_period_end_date="2025-04-01",
    )
    resolution = RasRuleResolver(RULES, EVENT_RULES).resolve(
        RasRuleResolutionRequest(transaction_date=transaction_date, facts=facts)
    )

    assert resolution.status is RasRuleResolutionStatus.CURRENCY_MISMATCH
    result = RasTheoreticalCalculator(
        rules=RULES,
        parameters=PARAMETERS,
    ).calculate(
        transaction_date=transaction_date,
        facts=facts,
        resolution=resolution,
    )
    assert result.status is RasTheoreticalCalculationStatus.NOT_CALCULABLE


def _calculate(
    transaction_date: date,
    facts: tuple[RasLegalFact, ...],
) -> RasTheoreticalCalculation:
    resolution = RasRuleResolver(RULES, EVENT_RULES).resolve(
        RasRuleResolutionRequest(transaction_date=transaction_date, facts=facts)
    )
    return RasTheoreticalCalculator(
        rules=RULES,
        parameters=PARAMETERS,
    ).calculate(
        transaction_date=transaction_date,
        facts=facts,
        resolution=resolution,
    )


def _facts(**values: str) -> tuple[RasLegalFact, ...]:
    return tuple(
        RasLegalFact(
            name=name,
            value=value,
            source=RasFactSource.USER,
            evidence_reference=f"user:{name}",
        )
        for name, value in values.items()
    )
