import csv
from collections.abc import Sequence
from pathlib import Path

from app.account_mapping.classifier import ClassificationRule
from app.account_mapping.domain import RasCategory

REQUIRED_RULE_COLUMNS = {
    "category",
    "keywords",
    "confidence",
    "justification",
    "action_required",
}


class InvalidClassificationRuleError(ValueError):
    pass


def load_classification_rules(source_path: Path) -> tuple[ClassificationRule, ...]:
    with source_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        _validate_columns(reader.fieldnames)
        return tuple(_build_rule(row) for row in reader if row)


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    columns = set(fieldnames or [])
    missing_columns = REQUIRED_RULE_COLUMNS - columns
    if missing_columns:
        raise InvalidClassificationRuleError(
            f"missing rule columns: {', '.join(sorted(missing_columns))}",
        )


def _build_rule(row: dict[str, str]) -> ClassificationRule:
    category = _read_category(row["category"])
    keywords = tuple(
        keyword.strip()
        for keyword in row["keywords"].split(";")
        if keyword.strip()
    )
    if not keywords:
        raise InvalidClassificationRuleError("classification rule needs keywords")

    return ClassificationRule(
        category=category,
        keywords=keywords,
        confidence=row["confidence"].strip(),
        justification=row["justification"].strip(),
        action_required=row["action_required"].strip(),
    )


def _read_category(value: str) -> RasCategory:
    try:
        return RasCategory(value.strip())
    except ValueError as exc:
        raise InvalidClassificationRuleError(
            f"unknown RAS category: {value}",
        ) from exc
