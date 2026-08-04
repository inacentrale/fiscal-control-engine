from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.ras_audit.legal_rules import RasLegalRule, load_ras_legal_rules
from app.ras_audit.rule_resolution import (
    RasFactSource,
    RasLegalFact,
    RasRuleResolution,
    RasRuleResolutionRequest,
    RasRuleResolutionStatus,
    RasRuleResolver,
)
from app.ras_audit.tax_event_rules import load_ras_tax_event_rules

ROOT = Path(__file__).resolve().parents[4]
RULES = load_ras_legal_rules(
    ROOT / "docs/reference/bf-ras-legal-rules.csv",
    repository_root=ROOT,
)
EVENT_RULES = load_ras_tax_event_rules(
    ROOT / "docs/reference/bf-ras-tax-event-rules.csv",
    repository_root=ROOT,
)
ACTIVE_RULES = tuple(rule for rule in RULES if rule.is_active)
BLOCKED_RULES = tuple(rule for rule in RULES if not rule.is_active)
CONDITION_FACTS = (
    "operation_type",
    "residence_status",
    "stable_establishment_status",
    "ifu_status",
    "beneficiary_type",
    "payer_type",
    "service_use_location",
    "treaty_override_status",
    "exemption_status",
)


@pytest.mark.parametrize("rule", ACTIVE_RULES, ids=lambda rule: rule.rule_id)
def test_each_active_rule_resolves_on_its_start_boundary(rule: RasLegalRule) -> None:
    result = _resolve(rule, rule.valid_from)

    assert result.status in {
        RasRuleResolutionStatus.RESOLVED_PROVISIONAL,
        RasRuleResolutionStatus.EXEMPTION_PROVISIONAL,
    }
    assert result.rule_id == rule.rule_id


@pytest.mark.parametrize(
    "rule",
    tuple(rule for rule in ACTIVE_RULES if rule.valid_to is not None),
    ids=lambda rule: rule.rule_id,
)
def test_each_closed_active_rule_resolves_on_its_end_boundary(
    rule: RasLegalRule,
) -> None:
    assert rule.valid_to is not None
    result = _resolve(rule, rule.valid_to)

    assert result.rule_id == rule.rule_id


@pytest.mark.parametrize("rule", ACTIVE_RULES, ids=lambda rule: rule.rule_id)
def test_each_active_rule_refuses_every_missing_required_fact(
    rule: RasLegalRule,
) -> None:
    transaction_date = rule.valid_from
    complete_facts = _facts_for_rule(rule, transaction_date)

    for required_fact in rule.required_facts:
        incomplete = tuple(
            fact for fact in complete_facts if fact.name != required_fact
        )
        result = RasRuleResolver(RULES, EVENT_RULES).resolve(
            RasRuleResolutionRequest(
                transaction_date=transaction_date,
                facts=incomplete,
            )
        )

        assert result.rule_id != rule.rule_id
        assert result.status not in {
            RasRuleResolutionStatus.RESOLVED_PROVISIONAL,
            RasRuleResolutionStatus.EXEMPTION_PROVISIONAL,
        }


@pytest.mark.parametrize("rule", BLOCKED_RULES, ids=lambda rule: rule.rule_id)
def test_each_blocked_rule_stays_non_activatable_with_all_declared_facts(
    rule: RasLegalRule,
) -> None:
    result = _resolve(rule, rule.valid_from)

    assert result.status is not RasRuleResolutionStatus.RESOLVED_PROVISIONAL
    assert result.status is not RasRuleResolutionStatus.EXEMPTION_PROVISIONAL
    assert result.rule_id is None


def _resolve(rule: RasLegalRule, transaction_date: date) -> RasRuleResolution:
    return RasRuleResolver(RULES, EVENT_RULES).resolve(
        RasRuleResolutionRequest(
            transaction_date=transaction_date,
            facts=_facts_for_rule(rule, transaction_date),
        )
    )


def _facts_for_rule(
    rule: RasLegalRule,
    transaction_date: date,
) -> tuple[RasLegalFact, ...]:
    values = {
        fact_name: str(getattr(rule, fact_name))
        for fact_name in CONDITION_FACTS
        if getattr(rule, fact_name) != "*"
    }
    for required_fact in rule.required_facts:
        values.setdefault(required_fact, _required_value(rule, required_fact))
    if rule.regime == "resident":
        values.update(
            payment_status="paid",
            payment_date=transaction_date.isoformat(),
        )
    elif rule.regime == "nonresident":
        values.update(
            payment_status="put_in_payment",
            payment_date=transaction_date.isoformat(),
        )
    elif rule.regime == "rent":
        values.update(
            rent_accrual_status="accrued",
            tax_period_end_date=transaction_date.isoformat(),
        )
    return tuple(
        RasLegalFact(
            name=name,
            value=value,
            source=RasFactSource.USER,
            evidence_reference=f"matrix-contract:{rule.rule_id}:{name}",
        )
        for name, value in values.items()
    )


def _required_value(rule: RasLegalRule, fact_name: str) -> str:
    if fact_name in {
        "tax_base_amount",
        "payment_amount",
        "gross_rent_excluding_vat",
    }:
        minimum = rule.minimum_amount or Decimal("0")
        return str(minimum + Decimal("100000"))
    if fact_name == "currency":
        return rule.amount_currency or "XOF"
    if fact_name in {
        "exemption_evidence",
        "scope_source_confirmation",
        "treaty_source_confirmation",
    }:
        return "documented-reference"
    return "documented-value"
