from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.tax_declaration.withholding_rule_loader import (
    WithholdingBaseField,
    WithholdingRegime,
    WithholdingRuleReferenceError,
    load_withholding_validation_rules,
)


def test_loads_versioned_official_withholding_rules() -> None:
    rules = load_withholding_validation_rules(_reference_path())

    resident_2026 = next(
        rule
        for rule in rules
        if rule.rule_id == "resident_temporary_staffing_service_2026"
    )
    assert resident_2026.regime is WithholdingRegime.RESIDENT
    assert resident_2026.rate == Decimal("2")
    assert resident_2026.base_field is WithholdingBaseField.TAX_BASE
    assert resident_2026.valid_from == date(2026, 1, 1)
    assert resident_2026.valid_to is None
    assert resident_2026.source_url.startswith("https://www.finances.gov.bf/")
    assert resident_2026.source_locator == "article 15 / CGI article 207"


def test_separates_2024_2025_and_2026_categories() -> None:
    rules = load_withholding_validation_rules(_reference_path())

    categories_by_version = {
        version: {
            rule.rate_category
            for rule in rules
            if rule.regime is WithholdingRegime.RESIDENT
            and rule.version == version
        }
        for version in ("v2024", "v2025", "v2026")
    }

    assert "temporary_work_company" not in categories_by_version["v2024"]
    assert "temporary_work_company" in categories_by_version["v2025"]
    assert "temporary_staffing_service" in categories_by_version["v2026"]
    assert "temporary_work_company" not in categories_by_version["v2026"]


def test_rejects_overlapping_periods(tmp_path: Path) -> None:
    source = tmp_path / "rules.csv"
    source.write_text(
        _header()
        + "r1,v1,resident,standard,5,tax_base,2025-01-01,2025-12-31,"
        "https://dgi.bf/verification/CGI,article 207,condition\n"
        + "r2,v2,resident,standard,5,tax_base,2025-12-31,,"
        "https://dgi.bf/verification/CGI,article 207,condition\n",
        encoding="utf-8",
    )

    with pytest.raises(
        WithholdingRuleReferenceError,
        match="overlapping withholding rule periods",
    ):
        load_withholding_validation_rules(source)


@pytest.mark.parametrize(
    "replacement",
    [
        "r1,v1,resident,standard,-1,tax_base,2025-01-01,,"
        "https://dgi.bf/verification/CGI,article 207,condition\n",
        "r1,v1,resident,standard,5,tax_base,2025-01-01,,"
        "http://dgi.bf/verification/CGI,article 207,condition\n",
        "r1,v1,unknown,standard,5,tax_base,2025-01-01,,"
        "https://dgi.bf/verification/CGI,article 207,condition\n",
    ],
)
def test_rejects_invalid_external_rule_values(
    tmp_path: Path,
    replacement: str,
) -> None:
    source = tmp_path / "rules.csv"
    source.write_text(_header() + replacement, encoding="utf-8")

    with pytest.raises(WithholdingRuleReferenceError):
        load_withholding_validation_rules(source)


def _reference_path() -> Path:
    return (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "bf-withholding-validation-rules.csv"
    )


def _header() -> str:
    return (
        "rule_id,version,regime,rate_category,rate,base_field,valid_from,"
        "valid_to,source_url,source_locator,conditions\n"
    )
