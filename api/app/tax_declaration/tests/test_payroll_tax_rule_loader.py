from datetime import date
from pathlib import Path

import pytest

from app.tax_declaration.payroll_tax_rule_loader import (
    PayrollTaxRuleReferenceError,
    PayrollTaxRuleType,
    load_payroll_tax_validation_rules,
)


def test_loads_complete_iuts_reference() -> None:
    rules = load_payroll_tax_validation_rules(_reference_path())

    brackets = [
        rule for rule in rules if rule.rule_type is PayrollTaxRuleType.BRACKET
    ]
    reductions = [
        rule
        for rule in rules
        if rule.rule_type is PayrollTaxRuleType.FAMILY_REDUCTION
    ]
    deadline = next(
        rule for rule in rules if rule.rule_type is PayrollTaxRuleType.DEADLINE
    )
    assert len(brackets) == 7
    assert len(reductions) == 5
    assert brackets[0].lower_bound == 0
    assert brackets[-1].upper_bound is None
    assert deadline.deadline_day == 10
    assert deadline.small_withholding_threshold == 5000
    assert all(rule.valid_from == date(2024, 1, 1) for rule in rules)
    assert all(rule.source_url.startswith("https://dgi.bf/") for rule in rules)


def test_rejects_non_contiguous_iuts_brackets(tmp_path: Path) -> None:
    source = tmp_path / "rules.csv"
    content = _reference_path().read_text(encoding="utf-8")
    source.write_text(
        content.replace(",2,30000,50000,", ",2,30100,50000,"),
        encoding="utf-8",
    )

    with pytest.raises(PayrollTaxRuleReferenceError, match="non-contiguous"):
        load_payroll_tax_validation_rules(source)


def test_rejects_non_https_source(tmp_path: Path) -> None:
    source = tmp_path / "rules.csv"
    source.write_text(
        _reference_path()
        .read_text(encoding="utf-8")
        .replace("https://dgi.bf/", "http://dgi.bf/", 1),
        encoding="utf-8",
    )

    with pytest.raises(PayrollTaxRuleReferenceError, match="HTTPS"):
        load_payroll_tax_validation_rules(source)


def _reference_path() -> Path:
    return (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "bf-iuts-validation-rules.csv"
    )
