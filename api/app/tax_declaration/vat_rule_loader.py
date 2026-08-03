import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.tax_declaration.validation_domain import ValidationLayer, VatValidationRule

_REQUIRED_COLUMNS = {
    "rule_id",
    "version",
    "layer",
    "target_line",
    "target_field",
    "operator",
    "operand_lines",
    "expected_value",
    "tolerance",
    "valid_from",
    "valid_to",
    "source_url",
    "source_locator",
}


class VatRuleReferenceError(ValueError):
    pass


def load_vat_validation_rules(source_path: Path) -> tuple[VatValidationRule, ...]:
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or not _REQUIRED_COLUMNS.issubset(
                reader.fieldnames,
            ):
                raise VatRuleReferenceError("invalid VAT rule reference columns")
            rules = tuple(_parse_rule(row) for row in reader)
    except OSError as exc:
        raise VatRuleReferenceError("VAT rule reference cannot be read") from exc
    if not rules:
        raise VatRuleReferenceError("VAT rule reference is empty")
    if len({rule.rule_id for rule in rules}) != len(rules):
        raise VatRuleReferenceError("duplicate VAT rule id")
    return rules


def _parse_rule(row: dict[str, str | None]) -> VatValidationRule:
    values = {key: (value or "").strip() for key, value in row.items()}
    always_required = _REQUIRED_COLUMNS.difference(
        {
            "target_line",
            "target_field",
            "operand_lines",
            "expected_value",
            "valid_from",
            "valid_to",
        },
    )
    if any(not values[column] for column in always_required):
        raise VatRuleReferenceError("VAT rule contains an empty required value")
    if values["operator"] not in {
        "sum",
        "equals",
        "monthly_deadline",
        "carry_forward_equals",
    }:
        raise VatRuleReferenceError("unsupported VAT rule operator")
    try:
        layer = ValidationLayer(values["layer"])
        tolerance = Decimal(values["tolerance"])
        expected_value = (
            Decimal(values["expected_value"])
            if values["expected_value"]
            else None
        )
        valid_from = (
            date.fromisoformat(values["valid_from"]) if values["valid_from"] else None
        )
        valid_to = (
            date.fromisoformat(values["valid_to"]) if values["valid_to"] else None
        )
    except (ValueError, InvalidOperation) as exc:
        raise VatRuleReferenceError("invalid VAT rule value") from exc
    if tolerance < 0:
        raise VatRuleReferenceError("VAT rule tolerance cannot be negative")
    operand_lines = (
        tuple(operand.strip() for operand in values["operand_lines"].split("|"))
        if values["operand_lines"]
        else ()
    )
    if values["operator"] == "sum" and (
        not operand_lines or any(not operand for operand in operand_lines)
    ):
        raise VatRuleReferenceError("VAT rule operands are invalid")
    if values["operator"] in {"sum", "equals"} and (
        not values["target_line"] or not values["target_field"]
    ):
        raise VatRuleReferenceError("VAT line rule requires a target")
    if values["operator"] == "equals" and expected_value is None:
        raise VatRuleReferenceError("VAT equals rule requires an expected value")
    if values["operator"] == "carry_forward_equals" and len(operand_lines) != 1:
        raise VatRuleReferenceError("VAT carry-forward rule requires one source line")
    if valid_from and valid_to and valid_to < valid_from:
        raise VatRuleReferenceError("VAT rule validity window is invalid")
    return VatValidationRule(
        rule_id=values["rule_id"],
        version=values["version"],
        layer=layer,
        target_line=values["target_line"],
        target_field=values["target_field"],
        operator=values["operator"],
        operand_lines=operand_lines,
        expected_value=expected_value,
        tolerance=tolerance,
        valid_from=valid_from,
        valid_to=valid_to,
        source_url=values["source_url"],
        source_locator=values["source_locator"],
    )
