from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse


class CorporateIncomeTaxRuleType(StrEnum):
    RATE = "rate"
    MINIMUM_TAX_FLOOR = "minimum_tax_floor"
    DEADLINE = "deadline"
    INSTALLMENT = "installment"
    MINIMUM_TAX_TREATMENT = "minimum_tax_treatment"


class CorporateMinimumTaxCalculationMode(StrEnum):
    STANDARD = "standard"
    FLOOR_ONLY = "floor_only"
    SCALE_STANDARD = "scale_standard"
    SCALE_FLOOR = "scale_floor"
    EXEMPT = "exempt"


@dataclass(frozen=True)
class CorporateIncomeTaxValidationRule:
    rule_id: str
    version: str
    rule_type: CorporateIncomeTaxRuleType
    rate: Decimal | None
    regime: str | None
    floor_amount: Decimal | None
    base_field: str | None
    base_rounding_unit: Decimal | None
    treatment: str | None
    calculation_mode: CorporateMinimumTaxCalculationMode | None
    factor: Decimal | None
    deadline_month: int | None
    deadline_day: int | None
    valid_from: date
    valid_to: date | None
    source_url: str
    source_locator: str


class CorporateIncomeTaxRuleReferenceError(ValueError):
    pass


_REQUIRED_COLUMNS = {
    "rule_id",
    "version",
    "rule_type",
    "rate",
    "regime",
    "floor_amount",
    "base_field",
    "base_rounding_unit",
    "treatment",
    "calculation_mode",
    "factor",
    "deadline_month",
    "deadline_day",
    "valid_from",
    "valid_to",
    "source_url",
    "source_locator",
}


def load_corporate_income_tax_validation_rules(
    source_path: Path,
) -> tuple[CorporateIncomeTaxValidationRule, ...]:
    try:
        with source_path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or not _REQUIRED_COLUMNS.issubset(
                reader.fieldnames,
            ):
                raise CorporateIncomeTaxRuleReferenceError(
                    "invalid IS validation rule columns",
                )
            rules = tuple(_parse_rule(row) for row in reader)
    except OSError as exc:
        raise CorporateIncomeTaxRuleReferenceError(
            "IS validation rule reference cannot be read",
        ) from exc
    if not rules:
        raise CorporateIncomeTaxRuleReferenceError(
            "IS validation rule reference is empty",
        )
    _validate_rules(rules)
    return rules


def _parse_rule(row: dict[str, str | None]) -> CorporateIncomeTaxValidationRule:
    try:
        rule = CorporateIncomeTaxValidationRule(
            rule_id=_required(row, "rule_id"),
            version=_required(row, "version"),
            rule_type=CorporateIncomeTaxRuleType(_required(row, "rule_type")),
            rate=_optional_decimal(row.get("rate")),
            regime=_optional_text(row.get("regime")),
            floor_amount=_optional_decimal(row.get("floor_amount")),
            base_field=_optional_text(row.get("base_field")),
            base_rounding_unit=_optional_decimal(row.get("base_rounding_unit")),
            treatment=_optional_text(row.get("treatment")),
            calculation_mode=_optional_calculation_mode(
                row.get("calculation_mode"),
            ),
            factor=_optional_decimal(row.get("factor")),
            deadline_month=_optional_int(row.get("deadline_month")),
            deadline_day=_optional_int(row.get("deadline_day")),
            valid_from=date.fromisoformat(_required(row, "valid_from")),
            valid_to=_optional_date(row.get("valid_to")),
            source_url=_required(row, "source_url"),
            source_locator=_required(row, "source_locator"),
        )
    except (ValueError, InvalidOperation) as exc:
        raise CorporateIncomeTaxRuleReferenceError(
            "invalid IS validation rule",
        ) from exc
    return rule


def _validate_rules(rules: tuple[CorporateIncomeTaxValidationRule, ...]) -> None:
    if len({rule.rule_id for rule in rules}) != len(rules):
        raise CorporateIncomeTaxRuleReferenceError("duplicate IS validation rule id")
    for rule in rules:
        if urlparse(rule.source_url).scheme != "https":
            raise CorporateIncomeTaxRuleReferenceError("IS rule source must use HTTPS")
        if rule.valid_to is not None and rule.valid_to < rule.valid_from:
            raise CorporateIncomeTaxRuleReferenceError(
                "invalid IS rule validity period",
            )
        if rule.rule_type is CorporateIncomeTaxRuleType.RATE:
            _validate_rate(rule)
        elif rule.rule_type is CorporateIncomeTaxRuleType.MINIMUM_TAX_FLOOR:
            _validate_minimum_tax_floor(rule)
        elif rule.rule_type is CorporateIncomeTaxRuleType.DEADLINE:
            _validate_deadline(rule)
        elif rule.rule_type is CorporateIncomeTaxRuleType.INSTALLMENT:
            _validate_installment(rule)
        else:
            _validate_minimum_tax_treatment(rule)


def _validate_rate(rule: CorporateIncomeTaxValidationRule) -> None:
    if rule.rate is None or rule.rate < 0 or rule.rate > 100:
        raise CorporateIncomeTaxRuleReferenceError("invalid IS rate rule")


def _validate_installment(rule: CorporateIncomeTaxValidationRule) -> None:
    if rule.rate is None or rule.rate < 0 or rule.rate > 100:
        raise CorporateIncomeTaxRuleReferenceError("invalid IS installment rule")


def _validate_minimum_tax_floor(rule: CorporateIncomeTaxValidationRule) -> None:
    if (
        rule.regime is None
        or rule.floor_amount is None
        or rule.floor_amount < 0
        or rule.rate is None
        or rule.rate < 0
        or rule.rate > 100
        or rule.base_field != "annual_turnover_excluding_tax"
        or rule.base_rounding_unit is None
        or rule.base_rounding_unit <= 0
    ):
        raise CorporateIncomeTaxRuleReferenceError(
            "invalid IS minimum tax floor rule",
        )


def _validate_deadline(rule: CorporateIncomeTaxValidationRule) -> None:
    if (
        rule.deadline_month is None
        or not 1 <= rule.deadline_month <= 12
        or rule.deadline_day is None
        or not 1 <= rule.deadline_day <= 31
    ):
        raise CorporateIncomeTaxRuleReferenceError("invalid IS deadline rule")


def _validate_minimum_tax_treatment(
    rule: CorporateIncomeTaxValidationRule,
) -> None:
    if (
        rule.treatment is None
        or rule.calculation_mode is None
        or rule.factor is None
        or rule.factor < 0
        or rule.factor > 1
    ):
        raise CorporateIncomeTaxRuleReferenceError(
            "invalid IS minimum tax treatment rule",
        )


def _required(row: dict[str, str | None], name: str) -> str:
    value = (row.get(name) or "").strip()
    if not value:
        raise CorporateIncomeTaxRuleReferenceError(f"missing IS rule field: {name}")
    return value


def _optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _optional_decimal(value: str | None) -> Decimal | None:
    text = (value or "").strip()
    return Decimal(text) if text else None


def _optional_int(value: str | None) -> int | None:
    text = (value or "").strip()
    return int(text) if text else None


def _optional_calculation_mode(
    value: str | None,
) -> CorporateMinimumTaxCalculationMode | None:
    text = (value or "").strip()
    return CorporateMinimumTaxCalculationMode(text) if text else None


def _optional_date(value: str | None) -> date | None:
    text = (value or "").strip()
    return date.fromisoformat(text) if text else None
