from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from app.tax_declaration.domain import CanonicalTaxDeclaration
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationLayer,
    ValidationSeverity,
    ValidationStatus,
    VatValidationRule,
)


class VatHistoricalValidator:
    def validate(
        self,
        current: CanonicalTaxDeclaration,
        previous: CanonicalTaxDeclaration,
        rules: tuple[VatValidationRule, ...],
        *,
        current_period_end: date,
        previous_period_end: date,
    ) -> TaxDeclarationValidationReport:
        period_check = _period_continuity_check(
            current_period_end,
            previous_period_end,
        )
        history_checks = tuple(
            _evaluate_carry_forward(rule, current, previous)
            for rule in rules
            if rule.operator == "carry_forward_equals"
        )
        checks = (period_check, *history_checks)
        return TaxDeclarationValidationReport(
            overall_status=_overall_status(checks),
            checks=checks,
        )


def _period_continuity_check(
    current_period_end: date,
    previous_period_end: date,
) -> ValidationCheck:
    previous_last_day = monthrange(
        previous_period_end.year,
        previous_period_end.month,
    )[1]
    next_month = previous_period_end.month % 12 + 1
    next_year = previous_period_end.year + (
        1 if previous_period_end.month == 12 else 0
    )
    current_last_day = monthrange(next_year, next_month)[1]
    expected_current_end = date(next_year, next_month, current_last_day)
    passed = (
        previous_period_end.day == previous_last_day
        and current_period_end == expected_current_end
    )
    return ValidationCheck(
        check_id="vat_consecutive_periods",
        layer=ValidationLayer.HISTORICAL,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "Les declarations TVA couvrent deux mois consecutifs."
            if passed
            else "Les declarations TVA ne couvrent pas deux mois consecutifs."
        ),
        expected_date=expected_current_end,
        actual_date=current_period_end,
    )


def _evaluate_carry_forward(
    rule: VatValidationRule,
    current: CanonicalTaxDeclaration,
    previous: CanonicalTaxDeclaration,
) -> ValidationCheck:
    source_line = rule.operand_lines[0]
    expected = _line_amount(previous, source_line)
    actual = _line_amount(current, rule.target_line)
    if expected is None or actual is None:
        missing = tuple(
            line
            for line, value in ((source_line, expected), (rule.target_line, actual))
            if value is None
        )
        return ValidationCheck(
            check_id=rule.rule_id,
            layer=rule.layer,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Report de credit non evalue: montant requis absent.",
            source_url=rule.source_url,
            source_locator=rule.source_locator,
            affected_lines=missing,
        )
    difference = actual - expected
    passed = abs(difference) <= rule.tolerance
    return ValidationCheck(
        check_id=rule.rule_id,
        layer=rule.layer,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "Le credit anterieur est correctement repris."
            if passed
            else "Le credit repris differe du report anterieur."
        ),
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_value=expected,
        actual_value=actual,
        difference=difference,
        affected_lines=(source_line, rule.target_line),
    )


def _line_amount(
    declaration: CanonicalTaxDeclaration,
    line_code: str,
) -> Decimal | None:
    for record in declaration.records:
        fields = {field.name: field for field in record.fields}
        code = fields.get("line_code")
        amount = fields.get("tax_amount")
        if code is None or str(code.normalized_value) != line_code:
            continue
        if amount is not None and isinstance(amount.normalized_value, Decimal):
            return amount.normalized_value
    return None


def _overall_status(
    checks: tuple[ValidationCheck, ...],
) -> OverallValidationStatus:
    if any(check.status is ValidationStatus.FAILED for check in checks):
        return OverallValidationStatus.FAILED
    if any(check.status is ValidationStatus.NOT_EVALUATED for check in checks):
        return OverallValidationStatus.INCOMPLETE
    return OverallValidationStatus.PASSED

