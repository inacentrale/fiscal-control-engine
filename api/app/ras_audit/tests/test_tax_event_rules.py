from datetime import date
from pathlib import Path

import pytest

from app.ras_audit.tax_event_rules import (
    RasTaxEventRuleError,
    applicable_tax_event_rules,
    load_ras_tax_event_rules,
)

ROOT = Path(__file__).resolve().parents[4]
REFERENCE = ROOT / "docs/reference/bf-ras-tax-event-rules.csv"


def test_loads_distinct_sourced_events_by_regime() -> None:
    rules = load_ras_tax_event_rules(REFERENCE, repository_root=ROOT)

    assert {rule.regime for rule in rules} == {"resident", "nonresident", "rent"}
    assert {rule.event_value for rule in rules} == {
        "paid",
        "put_in_payment",
        "accrued",
    }
    assert all(len(rule.source_sha256) == 64 for rule in rules)


def test_selects_event_policy_by_regime_and_date() -> None:
    rules = load_ras_tax_event_rules(REFERENCE, repository_root=ROOT)

    selected = applicable_tax_event_rules(
        rules,
        jurisdiction="BF",
        regime="nonresident",
        event_date=date(2025, 1, 1),
    )

    assert [rule.event_value for rule in selected] == ["put_in_payment"]


def test_rejects_modified_legal_source(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("modified", encoding="utf-8")
    reference = tmp_path / "events.csv"
    reference.write_text(
        REFERENCE.read_text(encoding="utf-8").replace(
            "docs/source-corpus/fiscal/bf-ras-residents.md",
            "source.md",
        ),
        encoding="utf-8",
    )

    with pytest.raises(RasTaxEventRuleError, match="hash mismatch"):
        load_ras_tax_event_rules(reference, repository_root=tmp_path)
