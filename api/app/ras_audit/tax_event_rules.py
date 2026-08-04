import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from hashlib import sha256
from pathlib import Path


class RasTaxEventRuleError(ValueError):
    pass


class RasTaxEventRuleStatus(StrEnum):
    ACTIVE_PROVISIONAL = "active_provisional"
    BLOCKED_MISSING_SOURCE = "blocked_missing_source"


@dataclass(frozen=True)
class RasTaxEventRule:
    policy_id: str
    version: str
    jurisdiction: str
    regime: str
    event_fact: str
    event_value: str
    event_date_fact: str
    valid_from: date
    valid_to: date | None
    status: RasTaxEventRuleStatus
    source_path: str
    source_sha256: str
    source_url: str
    source_locator: str
    notes: str


def load_ras_tax_event_rules(
    path: Path,
    *,
    repository_root: Path,
) -> tuple[RasTaxEventRule, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            _validate_columns(reader.fieldnames)
            rules = tuple(
                _parse_rule(row, row_number)
                for row_number, row in enumerate(reader, start=2)
            )
    except OSError as exc:
        raise RasTaxEventRuleError("RAS tax event rules cannot be read") from exc
    if not rules:
        raise RasTaxEventRuleError("RAS tax event rules are empty")
    if len({rule.policy_id for rule in rules}) != len(rules):
        raise RasTaxEventRuleError("duplicate RAS tax event policy id")
    for rule in rules:
        _verify_source(rule, repository_root)
    _validate_overlaps(rules)
    return rules


def applicable_tax_event_rules(
    rules: tuple[RasTaxEventRule, ...],
    *,
    jurisdiction: str,
    regime: str,
    event_date: date,
) -> tuple[RasTaxEventRule, ...]:
    return tuple(
        rule
        for rule in rules
        if rule.jurisdiction == jurisdiction
        and rule.regime == regime
        and rule.valid_from <= event_date
        and (rule.valid_to is None or event_date <= rule.valid_to)
    )


def _parse_rule(row: dict[str, str | None], row_number: int) -> RasTaxEventRule:
    values = {key: (value or "").strip() for key, value in row.items()}
    optional = {"valid_to", "notes"}
    if any(not values[field] for field in _required_columns() - optional):
        raise RasTaxEventRuleError(
            f"incomplete RAS tax event rule at row {row_number}"
        )
    try:
        valid_from = date.fromisoformat(values["valid_from"])
        valid_to = (
            date.fromisoformat(values["valid_to"])
            if values["valid_to"]
            else None
        )
        status = RasTaxEventRuleStatus(values["activation_status"])
    except ValueError as exc:
        raise RasTaxEventRuleError(
            f"invalid RAS tax event rule at row {row_number}"
        ) from exc
    if valid_to is not None and valid_to < valid_from:
        raise RasTaxEventRuleError(
            f"invalid RAS tax event validity at row {row_number}"
        )
    digest = values["source_sha256"].lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise RasTaxEventRuleError(
            f"invalid RAS tax event source hash at row {row_number}"
        )
    return RasTaxEventRule(
        policy_id=values["policy_id"],
        version=values["version"],
        jurisdiction=values["jurisdiction"].upper(),
        regime=values["regime"],
        event_fact=values["event_fact"],
        event_value=values["event_value"],
        event_date_fact=values["event_date_fact"],
        valid_from=valid_from,
        valid_to=valid_to,
        status=status,
        source_path=values["source_path"],
        source_sha256=digest,
        source_url=values["source_url"],
        source_locator=values["source_locator"],
        notes=values["notes"],
    )


def _verify_source(rule: RasTaxEventRule, repository_root: Path) -> None:
    root = repository_root.resolve()
    source = (root / rule.source_path).resolve()
    if not source.is_relative_to(root) or not source.is_file():
        raise RasTaxEventRuleError(
            f"RAS tax event source is unavailable: {rule.policy_id}"
        )
    if sha256(source.read_bytes()).hexdigest() != rule.source_sha256:
        raise RasTaxEventRuleError(
            f"RAS tax event source hash mismatch: {rule.policy_id}"
        )


def _validate_overlaps(rules: tuple[RasTaxEventRule, ...]) -> None:
    active = tuple(
        rule
        for rule in rules
        if rule.status is RasTaxEventRuleStatus.ACTIVE_PROVISIONAL
    )
    for index, left in enumerate(active):
        for right in active[index + 1 :]:
            if (
                left.jurisdiction == right.jurisdiction
                and left.regime == right.regime
                and _dates_overlap(left, right)
            ):
                raise RasTaxEventRuleError(
                    "overlapping active RAS tax event rules: "
                    f"{left.policy_id}, {right.policy_id}"
                )


def _dates_overlap(left: RasTaxEventRule, right: RasTaxEventRule) -> bool:
    left_end = left.valid_to or date.max
    right_end = right.valid_to or date.max
    return left.valid_from <= right_end and right.valid_from <= left_end


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    if set(fieldnames or ()) != _required_columns():
        raise RasTaxEventRuleError("invalid RAS tax event rule columns")


def _required_columns() -> set[str]:
    return {
        "policy_id",
        "version",
        "jurisdiction",
        "regime",
        "event_fact",
        "event_value",
        "event_date_fact",
        "valid_from",
        "valid_to",
        "activation_status",
        "source_path",
        "source_sha256",
        "source_url",
        "source_locator",
        "notes",
    }
