from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.tax_declaration.corporate_income_tax_rule_loader import (
    CorporateIncomeTaxRuleReferenceError,
    CorporateIncomeTaxRuleType,
    CorporateMinimumTaxCalculationMode,
    load_corporate_income_tax_validation_rules,
)


def test_loads_complete_is_reference() -> None:
    rules = load_corporate_income_tax_validation_rules(_reference_path())

    rate = next(
        rule for rule in rules if rule.rule_type is CorporateIncomeTaxRuleType.RATE
    )
    floors = [
        rule
        for rule in rules
        if rule.rule_type is CorporateIncomeTaxRuleType.MINIMUM_TAX_FLOOR
    ]
    deadline = next(
        rule
        for rule in rules
        if rule.rule_type is CorporateIncomeTaxRuleType.DEADLINE
    )
    installment = next(
        rule
        for rule in rules
        if rule.rule_type is CorporateIncomeTaxRuleType.INSTALLMENT
    )
    treatments = [
        rule
        for rule in rules
        if rule.rule_type is CorporateIncomeTaxRuleType.MINIMUM_TAX_TREATMENT
    ]
    assert rate.rate == Decimal("27.50")
    assert len(floors) == 2
    normal_floor = next(rule for rule in floors if rule.regime == "real_normal")
    simplified_floor = next(
        rule for rule in floors if rule.regime == "real_simplified"
    )
    assert normal_floor.floor_amount == Decimal("1000000")
    assert simplified_floor.floor_amount == Decimal("300000")
    assert normal_floor.rate == Decimal("0.50")
    assert normal_floor.base_field == "annual_turnover_excluding_tax"
    assert normal_floor.base_rounding_unit == Decimal("100000")
    assert deadline.deadline_month == 4
    assert deadline.deadline_day == 30
    assert installment.rate == Decimal("75.00")
    assert len(treatments) == 5
    assert {
        rule.calculation_mode for rule in treatments
    } == set(CorporateMinimumTaxCalculationMode)
    assert all(rule.valid_from == date(2024, 1, 1) for rule in rules)
    assert all(rule.source_url.startswith("https://dgi.bf/") for rule in rules)


def test_rejects_minimum_floor_rule_without_regime(tmp_path: Path) -> None:
    source = tmp_path / "rules.csv"
    source.write_text(
        _reference_path().read_text(encoding="utf-8").replace(
            ",real_normal,1000000,",
            ",,1000000,",
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        CorporateIncomeTaxRuleReferenceError,
        match="minimum tax floor",
    ):
        load_corporate_income_tax_validation_rules(source)


def test_rejects_non_https_source(tmp_path: Path) -> None:
    source = tmp_path / "rules.csv"
    source.write_text(
        _reference_path()
        .read_text(encoding="utf-8")
        .replace("https://dgi.bf/", "http://dgi.bf/", 1),
        encoding="utf-8",
    )

    with pytest.raises(CorporateIncomeTaxRuleReferenceError, match="HTTPS"):
        load_corporate_income_tax_validation_rules(source)


def _reference_path() -> Path:
    return (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "bf-is-validation-rules.csv"
    )
