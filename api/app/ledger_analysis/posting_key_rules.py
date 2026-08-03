import csv
from dataclasses import dataclass
from pathlib import Path

POSTING_KEY_SIDES = {"debit", "credit"}


@dataclass(frozen=True)
class PostingKeyRule:
    posting_key: str
    side: str
    account_type: str
    category: str
    description: str
    source_url: str


def load_posting_key_rules(path: Path) -> tuple[PostingKeyRule, ...]:
    with path.open(encoding="utf-8", newline="") as rules_file:
        rows = tuple(csv.DictReader(rules_file))

    rules: list[PostingKeyRule] = []
    seen_keys: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        posting_key = (row.get("posting_key") or "").strip()
        side = (row.get("side") or "").strip().lower()
        if len(posting_key) != 2 or not posting_key.isdigit():
            raise ValueError(f"invalid posting key at row {row_number}")
        if posting_key in seen_keys:
            raise ValueError(f"duplicate posting key at row {row_number}")
        if side not in POSTING_KEY_SIDES:
            raise ValueError(f"invalid posting key side at row {row_number}")
        seen_keys.add(posting_key)
        rules.append(
            PostingKeyRule(
                posting_key=posting_key,
                side=side,
                account_type=(row.get("account_type") or "").strip(),
                category=(row.get("category") or "").strip(),
                description=(row.get("description") or "").strip(),
                source_url=(row.get("source_url") or "").strip(),
            ),
        )
    return tuple(rules)
