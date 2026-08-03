from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.tax_declaration.domain import (
    CanonicalRecord,
    CanonicalTaxDeclaration,
    TaxDeclarationType,
)
from app.tax_declaration.payroll_tax_rule_loader import (
    PayrollTaxRuleType,
    PayrollTaxValidationRule,
)
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationLayer,
    ValidationSeverity,
    ValidationStatus,
)

_REQUIRED_FIELDS = ("taxable_base", "dependent_count", "iuts_amount")


class PayrollTaxDeclarationValidator:
    def validate(
        self,
        declaration: CanonicalTaxDeclaration,
        rules: tuple[PayrollTaxValidationRule, ...],
        *,
        period_end: date | None,
        filing_date: date | None = None,
        tolerance: Decimal = Decimal("0"),
    ) -> TaxDeclarationValidationReport:
        if declaration.declaration_type is not TaxDeclarationType.PAYROLL_TAX:
            raise ValueError("IUTS declaration is required")
        if tolerance < 0:
            raise ValueError("tolerance cannot be negative")
        checks: list[ValidationCheck] = [
            _structure_check(declaration),
            _completeness_check(declaration),
        ]
        if period_end is None:
            checks.append(
                ValidationCheck(
                    check_id="payroll_tax_rule_period",
                    layer=ValidationLayer.FISCAL,
                    status=ValidationStatus.NOT_EVALUATED,
                    severity=ValidationSeverity.WARNING,
                    message="La periode est requise pour selectionner les regles IUTS.",
                ),
            )
        else:
            active_rules = _active_rules(rules, period_end)
            for index, record in enumerate(declaration.records, start=1):
                checks.append(
                    _amount_check(record, index, active_rules, tolerance),
                )
            checks.append(
                _deadline_check(
                    declaration,
                    active_rules,
                    period_end,
                    filing_date,
                ),
            )
        result = tuple(checks)
        return TaxDeclarationValidationReport(
            overall_status=_overall_status(result),
            checks=result,
        )


def _structure_check(declaration: CanonicalTaxDeclaration) -> ValidationCheck:
    status = (
        ValidationStatus.PASSED
        if declaration.records
        else ValidationStatus.NOT_EVALUATED
    )
    return ValidationCheck(
        check_id="payroll_tax_structure",
        layer=ValidationLayer.STRUCTURE,
        status=status,
        severity=(
            ValidationSeverity.INFO
            if status is ValidationStatus.PASSED
            else ValidationSeverity.WARNING
        ),
        message=(
            "La structure des lignes IUTS est exploitable."
            if status is ValidationStatus.PASSED
            else "Aucune ligne IUTS n'est disponible."
        ),
    )


def _completeness_check(declaration: CanonicalTaxDeclaration) -> ValidationCheck:
    incomplete = tuple(
        _record_identifier(record, index)
        for index, record in enumerate(declaration.records, start=1)
        if any(_value(record, field) is None for field in _REQUIRED_FIELDS)
    )
    passed = bool(declaration.records) and not incomplete
    return ValidationCheck(
        check_id="payroll_tax_completeness",
        layer=ValidationLayer.COMPLETENESS,
        status=(
            ValidationStatus.PASSED
            if passed
            else ValidationStatus.NOT_EVALUATED
        ),
        severity=(
            ValidationSeverity.INFO if passed else ValidationSeverity.WARNING
        ),
        message=(
            "Les donnees necessaires au controle IUTS sont presentes."
            if passed
            else "Des donnees necessaires au controle IUTS sont non resolues."
        ),
        affected_lines=incomplete,
    )


def _amount_check(
    record: CanonicalRecord,
    index: int,
    rules: tuple[PayrollTaxValidationRule, ...],
    tolerance: Decimal,
) -> ValidationCheck:
    identifier = _record_identifier(record, index)
    base = _decimal_value(record, "taxable_base")
    actual = _decimal_value(record, "iuts_amount")
    dependent_count = _int_value(record, "dependent_count")
    brackets = tuple(
        sorted(
            (rule for rule in rules if rule.rule_type is PayrollTaxRuleType.BRACKET),
            key=lambda rule: rule.sequence or 0,
        ),
    )
    family_rules = tuple(
        rule
        for rule in rules
        if rule.rule_type is PayrollTaxRuleType.FAMILY_REDUCTION
        and rule.dependent_count == dependent_count
    )
    expected = None
    if base is not None and base >= 0 and brackets and len(family_rules) == 1:
        gross_tax = _progressive_tax(base, brackets)
        family_rate = family_rules[0].rate
        if family_rate is not None:
            expected = gross_tax * (Decimal(100) - family_rate) / Decimal(100)
    source_rules = brackets + family_rules
    if expected is None or actual is None:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        difference = None
        message = "La base, les charges ou le montant IUTS sont non resolus."
    else:
        difference = actual - expected
        passed = abs(difference) <= tolerance
        status = ValidationStatus.PASSED if passed else ValidationStatus.FAILED
        severity = ValidationSeverity.INFO if passed else ValidationSeverity.ERROR
        message = (
            "Le montant IUTS correspond au bareme et aux charges."
            if passed
            else "Le montant IUTS ne correspond pas au bareme et aux charges."
        )
    return ValidationCheck(
        check_id=f"payroll_tax_amount_{identifier}",
        layer=ValidationLayer.FISCAL,
        status=status,
        severity=severity,
        message=message,
        source_url=source_rules[0].source_url if source_rules else None,
        source_locator=_source_locators(source_rules),
        expected_value=expected,
        actual_value=actual,
        difference=difference,
        affected_lines=(identifier,),
    )


def _progressive_tax(
    base: Decimal,
    brackets: tuple[PayrollTaxValidationRule, ...],
) -> Decimal:
    total = Decimal(0)
    for rule in brackets:
        if rule.lower_bound is None or rule.rate is None:
            continue
        upper = rule.upper_bound if rule.upper_bound is not None else base
        taxable = min(base, upper) - rule.lower_bound
        if taxable > 0:
            total += taxable * rule.rate / Decimal(100)
    return total


def _deadline_check(
    declaration: CanonicalTaxDeclaration,
    rules: tuple[PayrollTaxValidationRule, ...],
    period_end: date,
    filing_date: date | None,
) -> ValidationCheck:
    deadline_rules = tuple(
        rule for rule in rules if rule.rule_type is PayrollTaxRuleType.DEADLINE
    )
    if len(deadline_rules) != 1:
        return ValidationCheck(
            check_id="payroll_tax_deadline",
            layer=ValidationLayer.FISCAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Aucune regle d'echeance IUTS unique n'est applicable.",
        )
    rule = deadline_rules[0]
    if rule.deadline_day is None:
        raise ValueError("IUTS deadline day is required")
    expected_date = _next_month_date(period_end, rule.deadline_day)
    amounts = tuple(
        value
        for record in declaration.records
        if (value := _decimal_value(record, "iuts_amount")) is not None
    )
    total = (
        sum(amounts, Decimal(0))
        if len(amounts) == len(declaration.records)
        else None
    )
    threshold = rule.small_withholding_threshold
    if filing_date is None or total is None:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = "La date de depot ou le total IUTS n'est pas resolu."
    elif filing_date <= expected_date:
        status = ValidationStatus.PASSED
        severity = ValidationSeverity.INFO
        message = "La declaration IUTS respecte l'echeance mensuelle."
    elif threshold is not None and total <= threshold:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = (
            "Le calendrier semestriel optionnel des petites retenues "
            "doit etre confirme."
        )
    else:
        status = ValidationStatus.FAILED
        severity = ValidationSeverity.ERROR
        message = "La declaration IUTS est deposee apres l'echeance."
    return ValidationCheck(
        check_id="payroll_tax_deadline",
        layer=ValidationLayer.FISCAL,
        status=status,
        severity=severity,
        message=message,
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_date=expected_date,
        actual_date=filing_date,
    )


def _active_rules(
    rules: tuple[PayrollTaxValidationRule, ...],
    period_end: date,
) -> tuple[PayrollTaxValidationRule, ...]:
    return tuple(
        rule
        for rule in rules
        if rule.valid_from <= period_end
        and (rule.valid_to is None or period_end <= rule.valid_to)
    )


def _next_month_date(period_end: date, day: int) -> date:
    if period_end.month == 12:
        return date(period_end.year + 1, 1, day)
    return date(period_end.year, period_end.month + 1, day)


def _source_locators(rules: tuple[PayrollTaxValidationRule, ...]) -> str | None:
    locators = tuple(dict.fromkeys(rule.source_locator for rule in rules))
    return "; ".join(locators) if locators else None


def _record_identifier(record: CanonicalRecord, index: int) -> str:
    value = _value(record, "line_number")
    return value if isinstance(value, str) else str(index)


def _value(record: CanonicalRecord, name: str) -> object | None:
    return next(
        (field.normalized_value for field in record.fields if field.name == name),
        None,
    )


def _decimal_value(record: CanonicalRecord, name: str) -> Decimal | None:
    value = _value(record, name)
    return value if isinstance(value, Decimal) else None


def _int_value(record: CanonicalRecord, name: str) -> int | None:
    value = _value(record, name)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _overall_status(
    checks: tuple[ValidationCheck, ...],
) -> OverallValidationStatus:
    if any(check.status is ValidationStatus.FAILED for check in checks):
        return OverallValidationStatus.FAILED
    if any(check.status is ValidationStatus.NOT_EVALUATED for check in checks):
        return OverallValidationStatus.INCOMPLETE
    return OverallValidationStatus.PASSED
