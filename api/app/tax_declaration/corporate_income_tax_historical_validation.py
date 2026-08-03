from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.tax_declaration.corporate_income_tax_rule_loader import (
    CorporateIncomeTaxRuleType,
    CorporateIncomeTaxValidationRule,
)
from app.tax_declaration.domain import CanonicalRecord, CanonicalTaxDeclaration
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationLayer,
    ValidationSeverity,
    ValidationStatus,
)


class CorporateIncomeTaxHistoricalValidationError(ValueError):
    pass


class CorporateIncomeTaxHistoricalValidator:
    def validate(
        self,
        current: CanonicalTaxDeclaration,
        previous: CanonicalTaxDeclaration,
        rules: tuple[CorporateIncomeTaxValidationRule, ...],
        *,
        current_period_end: date,
        previous_period_end: date,
        tolerance: Decimal = Decimal("0"),
    ) -> TaxDeclarationValidationReport:
        if tolerance < 0:
            raise ValueError("tolerance cannot be negative")
        period_check = _period_continuity_check(
            current_period_end,
            previous_period_end,
        )
        installment_check = _installment_check(
            current,
            previous,
            rules,
            current_period_end,
            tolerance,
        )
        checks = (period_check, installment_check)
        return TaxDeclarationValidationReport(
            overall_status=_overall_status(checks),
            checks=checks,
        )


def _period_continuity_check(
    current_period_end: date,
    previous_period_end: date,
) -> ValidationCheck:
    if (
        previous_period_end.month != 12
        or previous_period_end.day != 31
        or current_period_end.month != 12
        or current_period_end.day != 31
    ):
        return ValidationCheck(
            check_id="corporate_income_tax_consecutive_exercises",
            layer=ValidationLayer.HISTORICAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message=(
                "La continuite des exercices IS n'est evaluee que pour des "
                "exercices clos au 31 decembre."
            ),
        )
    expected_current_end = date(previous_period_end.year + 1, 12, 31)
    passed = current_period_end == expected_current_end
    return ValidationCheck(
        check_id="corporate_income_tax_consecutive_exercises",
        layer=ValidationLayer.HISTORICAL,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "Les declarations IS couvrent deux exercices consecutifs."
            if passed
            else "Les declarations IS ne couvrent pas deux exercices consecutifs."
        ),
        expected_date=expected_current_end,
        actual_date=current_period_end,
    )


def _installment_check(
    current: CanonicalTaxDeclaration,
    previous: CanonicalTaxDeclaration,
    rules: tuple[CorporateIncomeTaxValidationRule, ...],
    current_period_end: date,
    tolerance: Decimal,
) -> ValidationCheck:
    installment_rules = tuple(
        rule
        for rule in rules
        if rule.rule_type is CorporateIncomeTaxRuleType.INSTALLMENT
        and rule.valid_from <= current_period_end
        and (rule.valid_to is None or current_period_end <= rule.valid_to)
    )
    prior_due = _decimal_value(previous, "corporate_tax_due")
    actual = _decimal_value(current, "provisional_installments_paid")
    if len(installment_rules) != 1 or prior_due is None or actual is None:
        return ValidationCheck(
            check_id="corporate_income_tax_installments",
            layer=ValidationLayer.HISTORICAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message=(
                "Le controle des acomptes provisionnels n'est pas evalue: "
                "IS du de l'exercice precedent, acomptes verses ou regle "
                "applicable non resolus."
            ),
        )
    rule = installment_rules[0]
    if rule.rate is None:
        raise CorporateIncomeTaxHistoricalValidationError(
            "IS installment rule rate is required",
        )
    expected = prior_due * rule.rate / Decimal(100)
    difference = actual - expected
    passed = abs(difference) <= tolerance
    return ValidationCheck(
        check_id="corporate_income_tax_installments",
        layer=ValidationLayer.HISTORICAL,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "Les acomptes provisionnels correspondent a l'IS de l'exercice "
            "precedent."
            if passed
            else "Les acomptes provisionnels ne correspondent pas a l'IS de "
            "l'exercice precedent."
        ),
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_value=expected,
        actual_value=actual,
        difference=difference,
    )


def _decimal_value(
    declaration: CanonicalTaxDeclaration,
    field_name: str,
) -> Decimal | None:
    record = _first_record(declaration)
    if record is None:
        return None
    value = next(
        (field.normalized_value for field in record.fields if field.name == field_name),
        None,
    )
    return value if isinstance(value, Decimal) else None


def _first_record(declaration: CanonicalTaxDeclaration) -> CanonicalRecord | None:
    return declaration.records[0] if declaration.records else None


def _overall_status(
    checks: tuple[ValidationCheck, ...],
) -> OverallValidationStatus:
    if any(check.status is ValidationStatus.FAILED for check in checks):
        return OverallValidationStatus.FAILED
    if any(check.status is ValidationStatus.NOT_EVALUATED for check in checks):
        return OverallValidationStatus.INCOMPLETE
    return OverallValidationStatus.PASSED
