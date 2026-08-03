from __future__ import annotations

from calendar import monthrange
from collections import Counter
from datetime import date
from decimal import Decimal

from app.tax_declaration.domain import (
    CanonicalField,
    CanonicalTaxDeclaration,
    TaxDeclarationType,
)
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationLayer,
    ValidationSeverity,
    ValidationStatus,
    VatValidationRule,
)


class VatDeclarationValidationError(ValueError):
    pass


class VatDeclarationValidator:
    def validate(
        self,
        declaration: CanonicalTaxDeclaration,
        rules: tuple[VatValidationRule, ...],
        *,
        period_end: date | None = None,
        filing_date: date | None = None,
    ) -> TaxDeclarationValidationReport:
        if declaration.declaration_type is not TaxDeclarationType.VAT:
            raise VatDeclarationValidationError("declaration is not VAT")

        line_fields, structural_checks = _collect_line_values(declaration)
        rule_checks = tuple(
            _evaluate_rule(rule, line_fields, period_end, filing_date)
            for rule in rules
        )
        checks = (*structural_checks, *rule_checks)
        return TaxDeclarationValidationReport(
            overall_status=_overall_status(checks),
            checks=checks,
        )


def _collect_line_values(
    declaration: CanonicalTaxDeclaration,
) -> tuple[dict[str, dict[str, CanonicalField]], tuple[ValidationCheck, ...]]:
    codes: list[str] = []
    line_fields: dict[str, dict[str, CanonicalField]] = {}
    missing_code_records: list[str] = []
    unresolved_amount_lines: list[str] = []

    for index, record in enumerate(declaration.records, start=1):
        fields = {field.name: field for field in record.fields}
        code = _text_value(fields.get("line_code"))
        if code is None:
            missing_code_records.append(f"record:{index}")
            continue
        codes.append(code)
        if code not in line_fields:
            line_fields[code] = fields
        amount = _decimal_value(fields.get("tax_amount"))
        if amount is None:
            unresolved_amount_lines.append(code)

    duplicates = tuple(
        sorted(code for code, count in Counter(codes).items() if count > 1),
    )
    structure_failed = bool(missing_code_records or duplicates)
    structure_lines = (*missing_code_records, *duplicates)
    structure_check = ValidationCheck(
        check_id="vat_unique_line_codes",
        layer=ValidationLayer.STRUCTURE,
        status=(
            ValidationStatus.FAILED if structure_failed else ValidationStatus.PASSED
        ),
        severity=(
            ValidationSeverity.ERROR if structure_failed else ValidationSeverity.INFO
        ),
        message=(
            "Codes de lignes TVA absents ou dupliques."
            if structure_failed
            else "Les codes de lignes TVA sont uniques."
        ),
        affected_lines=structure_lines,
    )
    completeness_failed = bool(unresolved_amount_lines)
    completeness_check = ValidationCheck(
        check_id="vat_resolved_line_amounts",
        layer=ValidationLayer.COMPLETENESS,
        status=(
            ValidationStatus.FAILED
            if completeness_failed
            else ValidationStatus.PASSED
        ),
        severity=(
            ValidationSeverity.ERROR
            if completeness_failed
            else ValidationSeverity.INFO
        ),
        message=(
            "Montants TVA absents ou non resolus."
            if completeness_failed
            else "Les montants presents sont resolus."
        ),
        affected_lines=tuple(sorted(unresolved_amount_lines)),
    )
    return line_fields, (structure_check, completeness_check)


def _evaluate_rule(
    rule: VatValidationRule,
    line_fields: dict[str, dict[str, CanonicalField]],
    period_end: date | None,
    filing_date: date | None,
) -> ValidationCheck:
    applicability_check = _applicability_check(rule, period_end)
    if applicability_check is not None:
        return applicability_check
    if rule.operator == "sum":
        return _evaluate_sum_rule(rule, line_fields)
    if rule.operator == "equals":
        return _evaluate_equals_rule(rule, line_fields)
    if rule.operator == "monthly_deadline":
        return _evaluate_monthly_deadline_rule(rule, period_end, filing_date)
    return ValidationCheck(
        check_id=rule.rule_id,
        layer=rule.layer,
        status=ValidationStatus.NOT_EVALUATED,
        severity=ValidationSeverity.WARNING,
        message="Controle historique non evalue: declaration precedente requise.",
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        affected_lines=(rule.target_line, *rule.operand_lines),
    )


def _evaluate_sum_rule(
    rule: VatValidationRule,
    line_fields: dict[str, dict[str, CanonicalField]],
) -> ValidationCheck:
    required_lines = (*rule.operand_lines, rule.target_line)
    line_values = {
        line: _decimal_value(fields.get(rule.target_field))
        for line, fields in line_fields.items()
    }
    missing_lines = tuple(
        line for line in required_lines if line_values.get(line) is None
    )
    if missing_lines:
        return ValidationCheck(
            check_id=rule.rule_id,
            layer=rule.layer,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Controle non evalue: lignes requises absentes.",
            source_url=rule.source_url,
            source_locator=rule.source_locator,
            affected_lines=missing_lines,
        )

    operand_values: list[Decimal] = []
    for line in rule.operand_lines:
        value = line_values[line]
        if value is None:
            raise AssertionError("operand value checked above")
        operand_values.append(value)
    expected = sum(operand_values, Decimal(0))
    actual = line_values[rule.target_line]
    if actual is None:
        raise AssertionError("target value checked above")
    difference = actual - expected
    passed = abs(difference) <= rule.tolerance
    return ValidationCheck(
        check_id=rule.rule_id,
        layer=rule.layer,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "Le total correspond aux lignes sources."
            if passed
            else "Le total ne correspond pas aux lignes sources."
        ),
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_value=expected,
        actual_value=actual,
        difference=difference,
        affected_lines=required_lines,
    )


def _evaluate_equals_rule(
    rule: VatValidationRule,
    line_fields: dict[str, dict[str, CanonicalField]],
) -> ValidationCheck:
    field = line_fields.get(rule.target_line, {}).get(rule.target_field)
    actual = _decimal_value(field)
    if actual is None or rule.expected_value is None:
        return ValidationCheck(
            check_id=rule.rule_id,
            layer=rule.layer,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Controle non evalue: valeur fiscale requise absente.",
            source_url=rule.source_url,
            source_locator=rule.source_locator,
            affected_lines=(rule.target_line,),
        )
    difference = actual - rule.expected_value
    passed = abs(difference) <= rule.tolerance
    return ValidationCheck(
        check_id=rule.rule_id,
        layer=rule.layer,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "La valeur fiscale correspond au referentiel."
            if passed
            else "La valeur fiscale differe du referentiel."
        ),
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_value=rule.expected_value,
        actual_value=actual,
        difference=difference,
        affected_lines=(rule.target_line,) if rule.target_line else (),
    )


def _applicability_check(
    rule: VatValidationRule,
    period_end: date | None,
) -> ValidationCheck | None:
    if rule.valid_from is None and rule.valid_to is None:
        return None
    if period_end is None:
        message = "Controle fiscal non evalue: periode fiscale absente."
    elif (
        rule.valid_from is not None
        and period_end < rule.valid_from
        or rule.valid_to is not None
        and period_end > rule.valid_to
    ):
        message = "Controle fiscal non applicable a cette periode."
    else:
        return None
    return ValidationCheck(
        check_id=rule.rule_id,
        layer=rule.layer,
        status=ValidationStatus.NOT_EVALUATED,
        severity=ValidationSeverity.WARNING,
        message=message,
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        affected_lines=(rule.target_line,),
    )


def _evaluate_monthly_deadline_rule(
    rule: VatValidationRule,
    period_end: date | None,
    filing_date: date | None,
) -> ValidationCheck:
    if period_end is None or filing_date is None:
        return ValidationCheck(
            check_id=rule.rule_id,
            layer=rule.layer,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Echeance non evaluee: dates requises absentes.",
            source_url=rule.source_url,
            source_locator=rule.source_locator,
        )
    last_day = monthrange(period_end.year, period_end.month)[1]
    if period_end.day != last_day:
        return ValidationCheck(
            check_id=rule.rule_id,
            layer=rule.layer,
            status=ValidationStatus.FAILED,
            severity=ValidationSeverity.ERROR,
            message="La periode TVA mensuelle ne finit pas au dernier jour du mois.",
            source_url=rule.source_url,
            source_locator=rule.source_locator,
            actual_date=period_end,
        )
    next_month = period_end.month % 12 + 1
    next_year = period_end.year + (1 if period_end.month == 12 else 0)
    deadline = date(next_year, next_month, 15)
    passed = filing_date <= deadline
    return ValidationCheck(
        check_id=rule.rule_id,
        layer=rule.layer,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "La declaration respecte l'echeance mensuelle."
            if passed
            else "La declaration est posterieure a l'echeance mensuelle."
        ),
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_date=deadline,
        actual_date=filing_date,
    )


def _text_value(field: CanonicalField | None) -> str | None:
    if field is None or field.normalized_value is None:
        return None
    value = str(field.normalized_value).strip()
    return value.zfill(2) if value.isdigit() and len(value) < 2 else value


def _decimal_value(field: CanonicalField | None) -> Decimal | None:
    if field is None or not isinstance(field.normalized_value, Decimal):
        return None
    return field.normalized_value


def _overall_status(
    checks: tuple[ValidationCheck, ...],
) -> OverallValidationStatus:
    if any(check.status is ValidationStatus.FAILED for check in checks):
        return OverallValidationStatus.FAILED
    if any(check.status is ValidationStatus.NOT_EVALUATED for check in checks):
        return OverallValidationStatus.INCOMPLETE
    return OverallValidationStatus.PASSED
