from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse


class PayrollTaxRuleType(StrEnum):
    BRACKET = "bracket"
    FAMILY_REDUCTION = "family_reduction"
    DEADLINE = "deadline"


@dataclass(frozen=True)
class PayrollTaxValidationRule:
    rule_id: str
    version: str
    rule_type: PayrollTaxRuleType
    sequence: int | None
    lower_bound: Decimal | None
    upper_bound: Decimal | None
    rate: Decimal | None
    dependent_count: int | None
    deadline_day: int | None
    small_withholding_threshold: Decimal | None
    valid_from: date
    valid_to: date | None
    source_url: str
    source_locator: str


class PayrollTaxRuleReferenceError(ValueError):
    pass


_REQUIRED_COLUMNS = {
    "rule_id",
    "version",
    "rule_type",
    "sequence",
    "lower_bound",
    "upper_bound",
    "rate",
    "dependent_count",
    "deadline_day",
    "small_withholding_threshold",
    "valid_from",
    "valid_to",
    "source_url",
    "source_locator",
}


def load_payroll_tax_validation_rules(
    source_path: Path,
) -> tuple[PayrollTaxValidationRule, ...]:
    try:
        with source_path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or not _REQUIRED_COLUMNS.issubset(
                reader.fieldnames,
            ):
                raise PayrollTaxRuleReferenceError(
                    "invalid IUTS validation rule columns",
                )
            rules = tuple(_parse_rule(row) for row in reader)
    except OSError as exc:
        raise PayrollTaxRuleReferenceError(
            "IUTS validation rule reference cannot be read",
        ) from exc
    if not rules:
        raise PayrollTaxRuleReferenceError("IUTS validation rule reference is empty")
    _validate_rules(rules)
    return rules


def _parse_rule(row: dict[str, str | None]) -> PayrollTaxValidationRule:
    try:
        rule = PayrollTaxValidationRule(
            rule_id=_required(row, "rule_id"),
            version=_required(row, "version"),
            rule_type=PayrollTaxRuleType(_required(row, "rule_type")),
            sequence=_optional_int(row.get("sequence")),
            lower_bound=_optional_decimal(row.get("lower_bound")),
            upper_bound=_optional_decimal(row.get("upper_bound")),
            rate=_optional_decimal(row.get("rate")),
            dependent_count=_optional_int(row.get("dependent_count")),
            deadline_day=_optional_int(row.get("deadline_day")),
            small_withholding_threshold=_optional_decimal(
                row.get("small_withholding_threshold"),
            ),
            valid_from=date.fromisoformat(_required(row, "valid_from")),
            valid_to=_optional_date(row.get("valid_to")),
            source_url=_required(row, "source_url"),
            source_locator=_required(row, "source_locator"),
        )
    except (ValueError, InvalidOperation) as exc:
        raise PayrollTaxRuleReferenceError("invalid IUTS validation rule") from exc
    return rule


def _validate_rules(rules: tuple[PayrollTaxValidationRule, ...]) -> None:
    if len({rule.rule_id for rule in rules}) != len(rules):
        raise PayrollTaxRuleReferenceError("duplicate IUTS validation rule id")
    for rule in rules:
        if urlparse(rule.source_url).scheme != "https":
            raise PayrollTaxRuleReferenceError("IUTS rule source must use HTTPS")
        if rule.valid_to is not None and rule.valid_to < rule.valid_from:
            raise PayrollTaxRuleReferenceError("invalid IUTS rule validity period")
        if rule.rule_type is PayrollTaxRuleType.BRACKET:
            _validate_bracket(rule)
        elif rule.rule_type is PayrollTaxRuleType.FAMILY_REDUCTION:
            _validate_family_reduction(rule)
        else:
            _validate_deadline(rule)
    _validate_bracket_sets(rules)


def _validate_bracket(rule: PayrollTaxValidationRule) -> None:
    if (
        rule.sequence is None
        or rule.lower_bound is None
        or rule.rate is None
        or rule.rate < 0
        or rule.rate > 100
        or (rule.upper_bound is not None and rule.upper_bound <= rule.lower_bound)
    ):
        raise PayrollTaxRuleReferenceError("invalid IUTS bracket rule")


def _validate_family_reduction(rule: PayrollTaxValidationRule) -> None:
    if (
        rule.dependent_count is None
        or rule.dependent_count < 0
        or rule.rate is None
        or rule.rate < 0
        or rule.rate > 100
    ):
        raise PayrollTaxRuleReferenceError("invalid IUTS family reduction rule")


def _validate_deadline(rule: PayrollTaxValidationRule) -> None:
    if (
        rule.deadline_day is None
        or not 1 <= rule.deadline_day <= 28
        or rule.small_withholding_threshold is None
        or rule.small_withholding_threshold < 0
    ):
        raise PayrollTaxRuleReferenceError("invalid IUTS deadline rule")


def _validate_bracket_sets(rules: tuple[PayrollTaxValidationRule, ...]) -> None:
    periods = {(rule.valid_from, rule.valid_to) for rule in rules}
    for period in periods:
        brackets = sorted(
            (
                rule
                for rule in rules
                if rule.rule_type is PayrollTaxRuleType.BRACKET
                and (rule.valid_from, rule.valid_to) == period
            ),
            key=lambda rule: rule.sequence or 0,
        )
        if not brackets:
            continue
        if brackets[0].lower_bound != 0 or brackets[-1].upper_bound is not None:
            raise PayrollTaxRuleReferenceError("incomplete IUTS bracket set")
        for previous, current in zip(brackets, brackets[1:], strict=False):
            if previous.upper_bound != current.lower_bound:
                raise PayrollTaxRuleReferenceError("non-contiguous IUTS brackets")


def _required(row: dict[str, str | None], name: str) -> str:
    value = (row.get(name) or "").strip()
    if not value:
        raise PayrollTaxRuleReferenceError(f"missing IUTS rule field: {name}")
    return value


def _optional_decimal(value: str | None) -> Decimal | None:
    text = (value or "").strip()
    return Decimal(text) if text else None


def _optional_int(value: str | None) -> int | None:
    text = (value or "").strip()
    return int(text) if text else None


def _optional_date(value: str | None) -> date | None:
    text = (value or "").strip()
    return date.fromisoformat(text) if text else None
