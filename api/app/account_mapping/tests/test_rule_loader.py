from pathlib import Path

import pytest

from app.account_mapping.domain import RasCategory
from app.account_mapping.rule_loader import (
    InvalidClassificationRuleError,
    load_classification_rules,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_load_classification_rules_from_csv() -> None:
    rules = load_classification_rules(FIXTURES_DIR / "ras_classification_rules.csv")

    assert len(rules) == 4
    assert rules[0].category is RasCategory.NON_RESIDENT_SERVICES
    assert rules[0].keywords == (
        "etranger",
        "non resident",
        "frais de siege",
        "redevance",
    )
    assert rules[0].confidence == "medium"


def test_load_classification_rules_rejects_missing_columns(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.csv"
    rules_path.write_text("category,keywords\nresident_services,honoraires\n")

    with pytest.raises(InvalidClassificationRuleError, match="missing rule columns"):
        load_classification_rules(rules_path)


def test_load_classification_rules_rejects_unknown_category(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.csv"
    rules_path.write_text(
        "category,keywords,confidence,justification,action_required\n"
        "unknown,honoraires,medium,Justification,Action\n",
        encoding="utf-8",
    )

    with pytest.raises(InvalidClassificationRuleError, match="unknown RAS category"):
        load_classification_rules(rules_path)
