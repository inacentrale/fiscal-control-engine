from pathlib import Path

import pytest

from app.ledger_analysis.account_balance_rules import (
    find_account_balance_rule,
    load_account_balance_rules,
)


def _rules_path() -> Path:
    candidates = (
        Path("/workspace/docs/reference/syscohada-account-balance-rules.csv"),
        Path("../docs/reference/syscohada-account-balance-rules.csv"),
        Path("docs/reference/syscohada-account-balance-rules.csv"),
    )
    return next(path for path in candidates if path.is_file())


def test_most_specific_syscohada_prefix_wins() -> None:
    rules = load_account_balance_rules(_rules_path())

    expected_sides = {
        "401100": "credit",
        "409100": "debit",
        "411100": "debit",
        "419100": "credit",
        "44585100": "variable",
    }
    for account, expected_side in expected_sides.items():
        rule = find_account_balance_rule(account, rules)
        assert rule is not None
        assert rule.normal_side == expected_side


def test_rejects_duplicate_account_prefix(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.csv"
    rules_path.write_text(
        "account_prefix,normal_side,nature,description,source_url\n"
        "4,variable,third_parties,,https://example.test\n"
        "4,debit,third_parties,,https://example.test\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate account prefix"):
        load_account_balance_rules(rules_path)
