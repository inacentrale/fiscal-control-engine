from pathlib import Path

import pytest

from app.ledger_analysis.posting_key_rules import load_posting_key_rules


def test_loads_versioned_posting_key_rules() -> None:
    workspace_rules_path = Path(
        "/workspace/docs/reference/sap-posting-key-rules.csv",
    )
    repository_rules_path = (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "sap-posting-key-rules.csv"
    )
    rules_path = (
        workspace_rules_path
        if workspace_rules_path.is_file()
        else repository_rules_path
    )

    rules = load_posting_key_rules(rules_path)
    rules_by_key = {rule.posting_key: rule for rule in rules}

    assert rules_by_key["40"].side == "debit"
    assert rules_by_key["50"].side == "credit"
    assert rules_by_key["09"].category == "special_gl"
    assert rules_by_key["75"].account_type == "asset"


def test_rejects_duplicate_posting_keys(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.csv"
    rules_path.write_text(
        "posting_key,side,account_type,category,description,source_url\n"
        "40,debit,general_ledger,standard,Debit,https://example.test\n"
        "40,credit,general_ledger,standard,Credit,https://example.test\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate posting key"):
        load_posting_key_rules(rules_path)
