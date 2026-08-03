from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse

from app.tax_declaration.withholding_rule_loader import WithholdingRegime


class WithholdingDeadlineSchedule(StrEnum):
    NEXT_MONTH_DAY = "next_month_day"


@dataclass(frozen=True)
class WithholdingDeadlineRule:
    rule_id: str
    version: str
    regime: WithholdingRegime
    schedule: WithholdingDeadlineSchedule
    deadline_day: int
    valid_from: date
    valid_to: date | None
    source_url: str
    source_locator: str


class WithholdingDeadlineReferenceError(ValueError):
    pass


_REQUIRED_COLUMNS = {
    "rule_id",
    "version",
    "regime",
    "schedule",
    "deadline_day",
    "valid_from",
    "valid_to",
    "source_url",
    "source_locator",
}


def load_withholding_deadline_rules(
    source_path: Path,
) -> tuple[WithholdingDeadlineRule, ...]:
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or not _REQUIRED_COLUMNS.issubset(
                reader.fieldnames,
            ):
                raise WithholdingDeadlineReferenceError(
                    "invalid withholding deadline columns",
                )
            rules = tuple(_parse_rule(row) for row in reader)
    except OSError as exc:
        raise WithholdingDeadlineReferenceError(
            "withholding deadlines cannot be read",
        ) from exc
    if not rules:
        raise WithholdingDeadlineReferenceError(
            "withholding deadline reference is empty",
        )
    if len({rule.rule_id for rule in rules}) != len(rules):
        raise WithholdingDeadlineReferenceError(
            "duplicate withholding deadline rule id",
        )
    _reject_overlaps(rules)
    return rules


def _parse_rule(row: dict[str, str | None]) -> WithholdingDeadlineRule:
    values = {key: (value or "").strip() for key, value in row.items()}
    required_values = _REQUIRED_COLUMNS.difference({"valid_to"})
    if any(not values[column] for column in required_values):
        raise WithholdingDeadlineReferenceError(
            "withholding deadline has an empty value",
        )
    try:
        rule = WithholdingDeadlineRule(
            rule_id=values["rule_id"],
            version=values["version"],
            regime=WithholdingRegime(values["regime"]),
            schedule=WithholdingDeadlineSchedule(values["schedule"]),
            deadline_day=int(values["deadline_day"]),
            valid_from=date.fromisoformat(values["valid_from"]),
            valid_to=(
                date.fromisoformat(values["valid_to"])
                if values["valid_to"]
                else None
            ),
            source_url=values["source_url"],
            source_locator=values["source_locator"],
        )
    except ValueError as exc:
        raise WithholdingDeadlineReferenceError(
            "invalid withholding deadline value",
        ) from exc
    if not 1 <= rule.deadline_day <= 28:
        raise WithholdingDeadlineReferenceError(
            "invalid withholding deadline day",
        )
    if rule.valid_to is not None and rule.valid_to < rule.valid_from:
        raise WithholdingDeadlineReferenceError(
            "invalid withholding deadline period",
        )
    parsed_url = urlparse(rule.source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise WithholdingDeadlineReferenceError(
            "invalid withholding deadline source URL",
        )
    return rule


def _reject_overlaps(rules: tuple[WithholdingDeadlineRule, ...]) -> None:
    grouped: dict[WithholdingRegime, list[WithholdingDeadlineRule]] = {}
    for rule in rules:
        grouped.setdefault(rule.regime, []).append(rule)
    for candidates in grouped.values():
        ordered = sorted(candidates, key=lambda rule: rule.valid_from)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.valid_to is None or current.valid_from <= previous.valid_to:
                raise WithholdingDeadlineReferenceError(
                    "overlapping withholding deadline periods",
                )
