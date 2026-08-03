from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse


class WithholdingRegime(StrEnum):
    RESIDENT = "resident"
    NONRESIDENT = "nonresident"
    NON_DETERMINED = "non_determined"


class WithholdingBaseField(StrEnum):
    TAX_BASE = "tax_base"
    PAYMENT_AMOUNT = "payment_amount"


@dataclass(frozen=True)
class WithholdingValidationRule:
    rule_id: str
    version: str
    regime: WithholdingRegime
    rate_category: str
    rate: Decimal
    base_field: WithholdingBaseField
    valid_from: date
    valid_to: date | None
    source_url: str
    source_locator: str
    conditions: str


class WithholdingRuleReferenceError(ValueError):
    pass


_REQUIRED_COLUMNS = {
    "rule_id",
    "version",
    "regime",
    "rate_category",
    "rate",
    "base_field",
    "valid_from",
    "valid_to",
    "source_url",
    "source_locator",
    "conditions",
}


def load_withholding_validation_rules(
    source_path: Path,
) -> tuple[WithholdingValidationRule, ...]:
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or not _REQUIRED_COLUMNS.issubset(
                reader.fieldnames,
            ):
                raise WithholdingRuleReferenceError(
                    "invalid withholding rule columns",
                )
            rules = tuple(_parse_rule(row) for row in reader)
    except OSError as exc:
        raise WithholdingRuleReferenceError(
            "withholding rules cannot be read",
        ) from exc
    if not rules:
        raise WithholdingRuleReferenceError("withholding rule reference is empty")
    if len({rule.rule_id for rule in rules}) != len(rules):
        raise WithholdingRuleReferenceError("duplicate withholding rule id")
    _reject_overlaps(rules)
    return rules


def _parse_rule(row: dict[str, str | None]) -> WithholdingValidationRule:
    values = {key: (value or "").strip() for key, value in row.items()}
    required_values = _REQUIRED_COLUMNS.difference({"valid_to"})
    if any(not values[column] for column in required_values):
        raise WithholdingRuleReferenceError("withholding rule has an empty value")
    try:
        rule = WithholdingValidationRule(
            rule_id=values["rule_id"],
            version=values["version"],
            regime=WithholdingRegime(values["regime"]),
            rate_category=values["rate_category"],
            rate=Decimal(values["rate"]),
            base_field=WithholdingBaseField(values["base_field"]),
            valid_from=date.fromisoformat(values["valid_from"]),
            valid_to=(
                date.fromisoformat(values["valid_to"])
                if values["valid_to"]
                else None
            ),
            source_url=values["source_url"],
            source_locator=values["source_locator"],
            conditions=values["conditions"],
        )
    except (InvalidOperation, ValueError) as exc:
        raise WithholdingRuleReferenceError(
            "invalid withholding rule value",
        ) from exc
    if not Decimal(0) <= rule.rate <= Decimal(100):
        raise WithholdingRuleReferenceError("invalid withholding rate")
    if rule.valid_to is not None and rule.valid_to < rule.valid_from:
        raise WithholdingRuleReferenceError("invalid withholding validity period")
    parsed_url = urlparse(rule.source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise WithholdingRuleReferenceError("invalid withholding source URL")
    return rule


def _reject_overlaps(rules: tuple[WithholdingValidationRule, ...]) -> None:
    grouped: dict[tuple[WithholdingRegime, str], list[WithholdingValidationRule]] = {}
    for rule in rules:
        grouped.setdefault((rule.regime, rule.rate_category), []).append(rule)
    for candidates in grouped.values():
        ordered = sorted(candidates, key=lambda rule: rule.valid_from)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.valid_to is None or current.valid_from <= previous.valid_to:
                raise WithholdingRuleReferenceError(
                    "overlapping withholding rule periods",
                )
