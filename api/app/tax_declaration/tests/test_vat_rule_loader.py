from pathlib import Path

import pytest

from app.tax_declaration.vat_rule_loader import (
    VatRuleReferenceError,
    load_vat_validation_rules,
)


def test_loads_versioned_and_sourced_vat_rule(tmp_path: Path) -> None:
    source = _write_rules(
        tmp_path,
        "r14,v1,arithmetic,14,tax_amount,sum,01|02,,0,,,"
        "https://dgi.example/form.pdf,line 14\n",
    )

    rules = load_vat_validation_rules(source)

    assert rules[0].rule_id == "r14"
    assert rules[0].operand_lines == ("01", "02")
    assert rules[0].source_locator == "line 14"


def test_rejects_duplicate_rule_ids(tmp_path: Path) -> None:
    row = (
        "r14,v1,arithmetic,14,tax_amount,sum,01|02,,0,,,"
        "https://dgi.example/form.pdf,line 14\n"
    )
    source = _write_rules(tmp_path, row + row)

    with pytest.raises(VatRuleReferenceError, match="duplicate"):
        load_vat_validation_rules(source)


def test_rejects_unsupported_operator(tmp_path: Path) -> None:
    source = _write_rules(
        tmp_path,
        "r14,v1,arithmetic,14,tax_amount,subtract,01|02,,0,,,"
        "https://dgi.example/form.pdf,line 14\n",
    )

    with pytest.raises(VatRuleReferenceError, match="operator"):
        load_vat_validation_rules(source)


def _write_rules(tmp_path: Path, rows: str) -> Path:
    source = tmp_path / "rules.csv"
    source.write_text(
        "rule_id,version,layer,target_line,target_field,operator,operand_lines,"
        "expected_value,tolerance,valid_from,valid_to,source_url,source_locator\n"
        + rows,
        encoding="utf-8",
    )
    return source
