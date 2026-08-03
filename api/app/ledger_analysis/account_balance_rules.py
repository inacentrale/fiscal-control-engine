import csv
from dataclasses import dataclass
from pathlib import Path

NORMAL_SIDES = {"debit", "credit", "variable"}


@dataclass(frozen=True)
class AccountBalanceRule:
    account_prefix: str
    normal_side: str
    nature: str
    description: str
    source_url: str


def load_account_balance_rules(path: Path) -> tuple[AccountBalanceRule, ...]:
    rules: list[AccountBalanceRule] = []
    seen_prefixes: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as rules_file:
        for row_number, row in enumerate(csv.DictReader(rules_file), start=2):
            prefix = (row.get("account_prefix") or "").strip()
            normal_side = (row.get("normal_side") or "").strip().lower()
            if not prefix.isdigit():
                raise ValueError(f"invalid account prefix at row {row_number}")
            if prefix in seen_prefixes:
                raise ValueError(f"duplicate account prefix at row {row_number}")
            if normal_side not in NORMAL_SIDES:
                raise ValueError(f"invalid normal side at row {row_number}")
            seen_prefixes.add(prefix)
            rules.append(
                AccountBalanceRule(
                    account_prefix=prefix,
                    normal_side=normal_side,
                    nature=(row.get("nature") or "").strip(),
                    description=(row.get("description") or "").strip(),
                    source_url=(row.get("source_url") or "").strip(),
                ),
            )
    return tuple(rules)


def find_account_balance_rule(
    account: object,
    rules: tuple[AccountBalanceRule, ...],
) -> AccountBalanceRule | None:
    normalized_account = _normalize_account(account)
    matching_rules = tuple(
        rule for rule in rules if normalized_account.startswith(rule.account_prefix)
    )
    if not matching_rules:
        return None
    return max(matching_rules, key=lambda rule: len(rule.account_prefix))


def _normalize_account(account: object) -> str:
    value = str(account).strip()
    if value.endswith(".0") and value[:-2].isdigit():
        return value[:-2]
    return value
