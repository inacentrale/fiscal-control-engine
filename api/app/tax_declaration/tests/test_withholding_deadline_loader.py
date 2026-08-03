from datetime import date
from pathlib import Path

import pytest

from app.tax_declaration.withholding_deadline_loader import (
    WithholdingDeadlineReferenceError,
    WithholdingDeadlineSchedule,
    load_withholding_deadline_rules,
)
from app.tax_declaration.withholding_rule_loader import WithholdingRegime


def test_loads_deadlines_for_all_supported_regimes() -> None:
    rules = load_withholding_deadline_rules(_reference_path())

    assert {rule.regime for rule in rules} == set(WithholdingRegime)
    resident = next(
        rule for rule in rules if rule.regime is WithholdingRegime.RESIDENT
    )
    assert resident.schedule is WithholdingDeadlineSchedule.NEXT_MONTH_DAY
    assert resident.deadline_day == 15
    assert resident.valid_from == date(2021, 1, 1)
    assert resident.source_locator == "article 208"


@pytest.mark.parametrize("deadline_day", ["0", "29", "invalide"])
def test_rejects_invalid_deadline_day(
    tmp_path: Path,
    deadline_day: str,
) -> None:
    source = tmp_path / "deadlines.csv"
    source.write_text(
        _header()
        + f"r1,v1,resident,next_month_day,{deadline_day},2024-01-01,,"
        "https://dgi.bf/verification/CGI,article 208\n",
        encoding="utf-8",
    )

    with pytest.raises(WithholdingDeadlineReferenceError):
        load_withholding_deadline_rules(source)


def test_rejects_overlapping_deadline_periods(tmp_path: Path) -> None:
    source = tmp_path / "deadlines.csv"
    source.write_text(
        _header()
        + "r1,v1,resident,next_month_day,15,2024-01-01,2024-12-31,"
        "https://dgi.bf/verification/CGI,article 208\n"
        + "r2,v2,resident,next_month_day,15,2024-12-31,,"
        "https://dgi.bf/verification/CGI,article 208\n",
        encoding="utf-8",
    )

    with pytest.raises(
        WithholdingDeadlineReferenceError,
        match="overlapping withholding deadline periods",
    ):
        load_withholding_deadline_rules(source)


def _reference_path() -> Path:
    return (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "bf-withholding-deadline-rules.csv"
    )


def _header() -> str:
    return (
        "rule_id,version,regime,schedule,deadline_day,valid_from,valid_to,"
        "source_url,source_locator\n"
    )
