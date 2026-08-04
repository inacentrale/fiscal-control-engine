from datetime import date
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

ROOT = Path(__file__).resolve().parents[4]


def _resolver() -> RasRuleResolver:
    return RasRuleResolver(
        load_ras_legal_rules(
            ROOT / "docs/reference/bf-ras-legal-rules.csv",
            repository_root=ROOT,
        ),
        load_ras_tax_event_rules(
            ROOT / "docs/reference/bf-ras-tax-event-rules.csv",
            repository_root=ROOT,
        ),
    )


def test_resolves_resident_standard_with_scope_and_rate_evidence() -> None:
    result = _resolver().resolve(
        _request(
            date(2024, 6, 1),
            regime="resident",
            operation_type="service_any",
            residence_status="resident",
            ifu_status="registered",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            exemption_status="not_exempt",
            tax_base_amount="100000",
            currency="XOF",
            payment_status="paid",
            payment_date="2024-06-01",
        )
    )

    assert result.status is RasRuleResolutionStatus.RESOLVED_PROVISIONAL
    assert result.rule_id == "resident_standard_2024"
    assert result.rate_percent == 5
    assert {evidence.source_kind for evidence in result.evidence} == {
        "scope",
        "rate",
        "tax_event",
    }
    assert all(len(evidence.source_sha256) == 64 for evidence in result.evidence)


def test_derives_rule_family_without_requiring_regime_as_user_fact() -> None:
    result = _resolver().resolve(
        _request(
            date(2024, 6, 1),
            operation_type="service_any",
            residence_status="resident",
            ifu_status="registered",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            exemption_status="not_exempt",
            tax_base_amount="100000",
            currency="XOF",
            payment_status="paid",
            payment_date="2024-06-01",
        )
    )

    assert result.status is RasRuleResolutionStatus.RESOLVED_PROVISIONAL
    assert result.rule_id == "resident_standard_2024"
    assert "regime" not in result.missing_facts


def test_does_not_guess_rule_family_when_discriminating_facts_are_missing() -> None:
    result = _resolver().resolve(
        _request(
            date(2024, 6, 1),
            operation_type="service_any",
            tax_base_amount="100000",
            currency="XOF",
        )
    )

    assert result.status is RasRuleResolutionStatus.MISSING_FACTS
    assert result.rule_id is None
    assert "residence_status" in result.missing_facts


def test_resolves_dated_temporary_staffing_rule() -> None:
    result = _resolver().resolve(
        _request(
            date(2025, 3, 1),
            regime="resident",
            operation_type="temporary_staffing",
            residence_status="resident",
            ifu_status="registered",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            exemption_status="not_exempt",
            tax_base_amount="250000",
            currency="XOF",
        )
    )

    assert result.rule_id == "resident_temporary_staffing_2025"
    assert result.rate_percent == 2


def test_returns_missing_facts_instead_of_guessing_ifu() -> None:
    result = _resolver().resolve(
        _request(
            date(2026, 3, 1),
            regime="resident",
            operation_type="service_any",
            residence_status="resident",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            exemption_status="not_exempt",
            tax_base_amount="100000",
            currency="XOF",
        )
    )

    assert result.status is RasRuleResolutionStatus.MISSING_FACTS
    assert "ifu_status" in result.missing_facts
    assert result.rule_id is None


def test_requires_sourced_tax_event_and_date_before_resolving() -> None:
    result = _resolver().resolve(
        _request(
            date(2025, 4, 1),
            include_tax_event=False,
            regime="resident",
            operation_type="service_any",
            residence_status="resident",
            ifu_status="registered",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            exemption_status="not_exempt",
            tax_base_amount="100000",
            currency="XOF",
        )
    )

    assert result.status is RasRuleResolutionStatus.MISSING_FACTS
    assert result.missing_facts == ("payment_status", "payment_date")
    assert result.evidence[0].source_kind == "tax_event"


def test_rejects_tax_event_date_different_from_rule_date() -> None:
    result = _resolver().resolve(
        _request(
            date(2025, 4, 1),
            regime="resident",
            operation_type="service_any",
            residence_status="resident",
            ifu_status="registered",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            exemption_status="not_exempt",
            tax_base_amount="100000",
            currency="XOF",
            payment_date="2025-04-02",
        )
    )

    assert result.status is RasRuleResolutionStatus.TAX_EVENT_DATE_MISMATCH


def test_unpaid_resident_charge_is_not_a_triggered_withholding_event() -> None:
    result = _resolver().resolve(
        _request(
            date(2025, 4, 1),
            include_tax_event=False,
            regime="resident",
            operation_type="service_any",
            residence_status="resident",
            ifu_status="registered",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            exemption_status="not_exempt",
            tax_base_amount="100000",
            currency="XOF",
            payment_status="not_paid",
        )
    )

    assert result.status is RasRuleResolutionStatus.NOT_APPLICABLE_TAX_EVENT
    assert result.missing_facts == ()


def test_applies_resident_threshold_only_after_all_facts_are_known() -> None:
    result = _resolver().resolve(
        _request(
            date(2024, 6, 1),
            regime="resident",
            operation_type="service_any",
            residence_status="resident",
            ifu_status="registered",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            exemption_status="not_exempt",
            tax_base_amount="49999",
            currency="XOF",
        )
    )

    assert result.status is RasRuleResolutionStatus.NOT_APPLICABLE_THRESHOLD
    assert result.rule_id == "resident_standard_2024"


def test_nonresident_treaty_case_is_blocked_without_treaty_source() -> None:
    result = _resolver().resolve(
        _request(
            date(2025, 4, 1),
            regime="nonresident",
            operation_type="service_any",
            residence_status="nonresident",
            stable_establishment_status="false",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            treaty_override_status="true",
            exemption_status="not_exempt",
            payment_amount="100000",
            currency="XOF",
        )
    )

    assert result.status is RasRuleResolutionStatus.BLOCKED_SOURCE_GAP
    assert result.alternative_rule_ids == ("nonresident_treaty_override",)
    assert "treaty_source_confirmation" in result.missing_facts


def test_nonresident_without_treaty_override_resolves_twenty_percent() -> None:
    result = _resolver().resolve(
        _request(
            date(2025, 4, 1),
            regime="nonresident",
            operation_type="service_any",
            residence_status="nonresident",
            stable_establishment_status="false",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            treaty_override_status="false",
            exemption_status="not_exempt",
            payment_amount="100000",
            currency="XOF",
        )
    )

    assert result.status is RasRuleResolutionStatus.RESOLVED_PROVISIONAL
    assert result.rate_percent == 20


def test_rent_resolves_to_progressive_method_not_invented_flat_rate() -> None:
    result = _resolver().resolve(
        _request(
            date(2025, 4, 1),
            regime="rent",
            operation_type="real_estate_rental",
            payer_type="eligible_rent_tenant",
            exemption_status="not_exempt",
            gross_rent_excluding_vat="500000",
            currency="XOF",
        )
    )

    assert result.status is RasRuleResolutionStatus.RESOLVED_PROVISIONAL
    assert result.calculation_method == "irf_progressive"
    assert result.rate_percent is None


def test_exemption_requires_evidence_and_is_not_a_zero_guessed_by_llm() -> None:
    result = _resolver().resolve(
        _request(
            date(2025, 4, 1),
            regime="resident",
            operation_type="service_any",
            residence_status="resident",
            payer_type="eligible_service_payer",
            service_use_location="BF",
            exemption_status="exempt",
            exemption_evidence="DGI-attestation-reference",
            tax_base_amount="100000",
            currency="XOF",
        )
    )

    assert result.status is RasRuleResolutionStatus.EXEMPTION_PROVISIONAL
    assert result.rate_percent == 0


def test_non_determined_rate_stays_blocked_without_scope_article() -> None:
    result = _resolver().resolve(
        _request(
            date(2026, 4, 1),
            regime="non_determined",
            operation_type="manual_or_teaching",
        )
    )

    assert result.status is RasRuleResolutionStatus.BLOCKED_SOURCE_GAP
    assert result.rate_percent is None
    assert result.rule_id is None


def _request(
    transaction_date: date,
    include_tax_event: bool = True,
    **facts: str,
) -> RasRuleResolutionRequest:
    regime = facts.get("regime")
    if include_tax_event and regime in {"resident", "nonresident", "rent"}:
        event_facts = {
            "resident": {
                "payment_status": "paid",
                "payment_date": transaction_date.isoformat(),
            },
            "nonresident": {
                "payment_status": "put_in_payment",
                "payment_date": transaction_date.isoformat(),
            },
            "rent": {
                "rent_accrual_status": "accrued",
                "tax_period_end_date": transaction_date.isoformat(),
            },
        }[regime]
        facts = {**event_facts, **facts}
    return RasRuleResolutionRequest(
        transaction_date=transaction_date,
        facts=tuple(
            RasLegalFact(
                name=name,
                value=value,
                source=RasFactSource.USER,
                evidence_reference=f"user:{name}",
            )
            for name, value in facts.items()
        ),
    )
