from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.tax_declaration.corporate_income_tax_rule_loader import (
    CorporateIncomeTaxRuleType,
    CorporateIncomeTaxValidationRule,
    CorporateMinimumTaxCalculationMode,
)
from app.tax_declaration.domain import (
    CanonicalRecord,
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
)

_REQUIRED_FIELDS = ("tax_regime", "taxable_profit", "computed_corporate_tax")


class CorporateIncomeTaxDeclarationValidator:
    def validate(
        self,
        declaration: CanonicalTaxDeclaration,
        rules: tuple[CorporateIncomeTaxValidationRule, ...],
        *,
        period_end: date | None,
        filing_date: date | None = None,
        tolerance: Decimal = Decimal("0"),
    ) -> TaxDeclarationValidationReport:
        if declaration.declaration_type is not TaxDeclarationType.CORPORATE_INCOME_TAX:
            raise ValueError("IS declaration is required")
        if tolerance < 0:
            raise ValueError("tolerance cannot be negative")
        checks: list[ValidationCheck] = [
            _structure_check(declaration),
            _completeness_check(declaration),
        ]
        if period_end is None:
            checks.append(
                ValidationCheck(
                    check_id="corporate_income_tax_rule_period",
                    layer=ValidationLayer.FISCAL,
                    status=ValidationStatus.NOT_EVALUATED,
                    severity=ValidationSeverity.WARNING,
                    message="La periode est requise pour selectionner les regles IS.",
                ),
            )
        else:
            active_rules = _active_rules(rules, period_end)
            for index, record in enumerate(declaration.records, start=1):
                checks.append(_rate_check(record, index, active_rules, tolerance))
                checks.append(
                    _minimum_tax_check(
                        record,
                        index,
                        active_rules,
                        tolerance,
                    ),
                )
            checks.append(_deadline_check(active_rules, period_end, filing_date))
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
        check_id="corporate_income_tax_structure",
        layer=ValidationLayer.STRUCTURE,
        status=status,
        severity=(
            ValidationSeverity.INFO
            if status is ValidationStatus.PASSED
            else ValidationSeverity.WARNING
        ),
        message=(
            "La structure des lignes IS est exploitable."
            if status is ValidationStatus.PASSED
            else "Aucune ligne IS n'est disponible."
        ),
    )


def _completeness_check(declaration: CanonicalTaxDeclaration) -> ValidationCheck:
    incomplete = tuple(
        _record_identifier(index)
        for index, record in enumerate(declaration.records, start=1)
        if any(_value(record, field) is None for field in _REQUIRED_FIELDS)
    )
    passed = bool(declaration.records) and not incomplete
    return ValidationCheck(
        check_id="corporate_income_tax_completeness",
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
            "Les donnees necessaires au controle IS sont presentes."
            if passed
            else "Des donnees necessaires au controle IS sont non resolues."
        ),
        affected_lines=incomplete,
    )


def _rate_check(
    record: CanonicalRecord,
    index: int,
    rules: tuple[CorporateIncomeTaxValidationRule, ...],
    tolerance: Decimal,
) -> ValidationCheck:
    identifier = _record_identifier(index)
    rate_rules = tuple(
        rule for rule in rules if rule.rule_type is CorporateIncomeTaxRuleType.RATE
    )
    taxable_profit = _decimal_value(record, "taxable_profit")
    actual = _decimal_value(record, "computed_corporate_tax")
    if len(rate_rules) != 1 or taxable_profit is None or taxable_profit < 0:
        return ValidationCheck(
            check_id=f"corporate_income_tax_rate_{identifier}",
            layer=ValidationLayer.FISCAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message=(
                "Le taux IS n'est pas evalue: benefice imposable non resolu, "
                "negatif ou taux applicable ambigu."
            ),
            affected_lines=(identifier,),
        )
    rule = rate_rules[0]
    if actual is None or rule.rate is None:
        return ValidationCheck(
            check_id=f"corporate_income_tax_rate_{identifier}",
            layer=ValidationLayer.FISCAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Le montant IS declare est non resolu.",
            source_url=rule.source_url,
            source_locator=rule.source_locator,
            affected_lines=(identifier,),
        )
    expected = taxable_profit * rule.rate / Decimal(100)
    difference = actual - expected
    passed = abs(difference) <= tolerance
    return ValidationCheck(
        check_id=f"corporate_income_tax_rate_{identifier}",
        layer=ValidationLayer.FISCAL,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "Le montant IS calcule correspond au taux applicable."
            if passed
            else "Le montant IS calcule ne correspond pas au taux applicable."
        ),
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_value=expected,
        actual_value=actual,
        difference=difference,
        affected_lines=(identifier,),
    )


def _minimum_tax_check(
    record: CanonicalRecord,
    index: int,
    rules: tuple[CorporateIncomeTaxValidationRule, ...],
    tolerance: Decimal,
) -> ValidationCheck:
    identifier = _record_identifier(index)
    regime = _text_value(record, "tax_regime")
    floor_rules = tuple(
        rule
        for rule in rules
        if rule.rule_type is CorporateIncomeTaxRuleType.MINIMUM_TAX_FLOOR
        and rule.regime == regime
    )
    actual = _decimal_value(record, "minimum_tax_declared")
    turnover = _decimal_value(record, "annual_turnover_excluding_tax")
    treatment = _text_value(record, "minimum_tax_treatment")
    treatment_rules = tuple(
        rule
        for rule in rules
        if rule.rule_type is CorporateIncomeTaxRuleType.MINIMUM_TAX_TREATMENT
        and rule.treatment == treatment
    )
    if treatment is None or len(treatment_rules) != 1:
        source_rules = floor_rules + treatment_rules
        return ValidationCheck(
            check_id=f"corporate_income_tax_minimum_{identifier}",
            layer=ValidationLayer.FISCAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message=(
                "Le calcul IMFPIC exige une situation fiscale explicite "
                "et une regle unique applicable."
            ),
            source_url=source_rules[0].source_url if source_rules else None,
            source_locator=_source_locators(source_rules),
            affected_lines=(identifier,),
        )
    rule = floor_rules[0] if len(floor_rules) == 1 else None
    treatment_rule = treatment_rules[0]
    mode = treatment_rule.calculation_mode
    requires_turnover = mode in {
        CorporateMinimumTaxCalculationMode.STANDARD,
        CorporateMinimumTaxCalculationMode.SCALE_STANDARD,
    }
    if (
        regime is None
        or rule is None
        or actual is None
        or (requires_turnover and (turnover is None or turnover < 0))
    ):
        return ValidationCheck(
            check_id=f"corporate_income_tax_minimum_{identifier}",
            layer=ValidationLayer.FISCAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message=(
                "Le calcul IMFPIC n'est pas evalue: regime, chiffre "
                "d'affaires HT ou montant declare non resolu."
            ),
            affected_lines=(identifier,),
        )
    if (
        rule.floor_amount is None
        or rule.rate is None
        or rule.base_rounding_unit is None
    ):
        raise ValueError("IS minimum tax calculation parameters are required")
    rounded_turnover = (
        (turnover // rule.base_rounding_unit) * rule.base_rounding_unit
        if turnover is not None
        else Decimal(0)
    )
    proportional_minimum = rounded_turnover * rule.rate / Decimal(100)
    standard_minimum = max(proportional_minimum, rule.floor_amount)
    expected = _minimum_tax_expected(
        standard_minimum,
        rule.floor_amount,
        treatment_rule,
    )
    difference = actual - expected
    passed = abs(difference) <= tolerance
    return ValidationCheck(
        check_id=f"corporate_income_tax_minimum_{identifier}",
        layer=ValidationLayer.FISCAL,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "Le montant IMFPIC correspond au chiffre d'affaires HT et au plancher."
            if passed
            else "Le montant IMFPIC declare ne correspond pas au montant attendu."
        ),
        source_url=rule.source_url,
        source_locator=_source_locators((rule, treatment_rule)),
        expected_value=expected,
        actual_value=actual,
        difference=difference,
        affected_lines=(identifier,),
    )


def _minimum_tax_expected(
    standard_minimum: Decimal,
    floor_amount: Decimal,
    treatment_rule: CorporateIncomeTaxValidationRule,
) -> Decimal:
    mode = treatment_rule.calculation_mode
    factor = treatment_rule.factor
    if mode is None or factor is None:
        raise ValueError("IS minimum tax treatment parameters are required")
    if mode is CorporateMinimumTaxCalculationMode.STANDARD:
        return standard_minimum
    if mode is CorporateMinimumTaxCalculationMode.FLOOR_ONLY:
        return floor_amount
    if mode is CorporateMinimumTaxCalculationMode.SCALE_STANDARD:
        return standard_minimum * factor
    if mode is CorporateMinimumTaxCalculationMode.SCALE_FLOOR:
        return floor_amount * factor
    if mode is CorporateMinimumTaxCalculationMode.EXEMPT:
        return Decimal(0)
    raise ValueError("unsupported IS minimum tax calculation mode")


def _deadline_check(
    rules: tuple[CorporateIncomeTaxValidationRule, ...],
    period_end: date,
    filing_date: date | None,
) -> ValidationCheck:
    deadline_rules = tuple(
        rule for rule in rules if rule.rule_type is CorporateIncomeTaxRuleType.DEADLINE
    )
    if len(deadline_rules) != 1:
        return ValidationCheck(
            check_id="corporate_income_tax_deadline",
            layer=ValidationLayer.FISCAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Aucune regle d'echeance IS unique n'est applicable.",
        )
    rule = deadline_rules[0]
    if rule.deadline_month is None or rule.deadline_day is None:
        raise ValueError("IS deadline month and day are required")
    if period_end.month != 12 or period_end.day != 31:
        return ValidationCheck(
            check_id="corporate_income_tax_deadline",
            layer=ValidationLayer.FISCAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message=(
                "L'echeance IS n'est calculee que pour un exercice clos "
                "au 31 decembre."
            ),
            source_url=rule.source_url,
            source_locator=rule.source_locator,
        )
    expected_date = date(period_end.year + 1, rule.deadline_month, rule.deadline_day)
    if filing_date is None:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = "La date de depot IS n'est pas resolue."
    elif filing_date <= expected_date:
        status = ValidationStatus.PASSED
        severity = ValidationSeverity.INFO
        message = "La declaration IS respecte l'echeance annuelle."
    else:
        status = ValidationStatus.FAILED
        severity = ValidationSeverity.ERROR
        message = "La declaration IS est deposee apres l'echeance annuelle."
    return ValidationCheck(
        check_id="corporate_income_tax_deadline",
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
    rules: tuple[CorporateIncomeTaxValidationRule, ...],
    period_end: date,
) -> tuple[CorporateIncomeTaxValidationRule, ...]:
    return tuple(
        rule
        for rule in rules
        if rule.valid_from <= period_end
        and (rule.valid_to is None or period_end <= rule.valid_to)
    )


def _record_identifier(index: int) -> str:
    return str(index)


def _value(record: CanonicalRecord, name: str) -> object | None:
    return next(
        (field.normalized_value for field in record.fields if field.name == name),
        None,
    )


def _decimal_value(record: CanonicalRecord, name: str) -> Decimal | None:
    value = _value(record, name)
    return value if isinstance(value, Decimal) else None


def _text_value(record: CanonicalRecord, name: str) -> str | None:
    value = _value(record, name)
    return value if isinstance(value, str) else None


def _source_locators(
    rules: tuple[CorporateIncomeTaxValidationRule, ...],
) -> str | None:
    locators = tuple(dict.fromkeys(rule.source_locator for rule in rules))
    return "; ".join(locators) if locators else None


def _overall_status(
    checks: tuple[ValidationCheck, ...],
) -> OverallValidationStatus:
    if any(check.status is ValidationStatus.FAILED for check in checks):
        return OverallValidationStatus.FAILED
    if any(check.status is ValidationStatus.NOT_EVALUATED for check in checks):
        return OverallValidationStatus.INCOMPLETE
    return OverallValidationStatus.PASSED
