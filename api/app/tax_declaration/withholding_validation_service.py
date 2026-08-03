from __future__ import annotations

from datetime import date
from decimal import Decimal

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
from app.tax_declaration.withholding_deadline_loader import (
    WithholdingDeadlineRule,
    WithholdingDeadlineSchedule,
)
from app.tax_declaration.withholding_rule_loader import (
    WithholdingRegime,
    WithholdingValidationRule,
)

_SELECTION_FIELDS = (
    "withholding_regime",
    "rate_category",
    "tax_rate",
    "withheld_amount",
)


class WithholdingDeclarationValidator:
    def validate(
        self,
        declaration: CanonicalTaxDeclaration,
        rules: tuple[WithholdingValidationRule, ...],
        *,
        period_end: date | None,
        filing_date: date | None = None,
        deadline_rules: tuple[WithholdingDeadlineRule, ...] = (),
        tolerance: Decimal = Decimal("0"),
    ) -> TaxDeclarationValidationReport:
        if declaration.declaration_type is not TaxDeclarationType.WITHHOLDING_TAX:
            raise ValueError("withholding declaration is required")
        if tolerance < 0:
            raise ValueError("tolerance cannot be negative")
        checks: list[ValidationCheck] = [_structure_check(declaration)]
        checks.append(_completeness_check(declaration))
        if period_end is None:
            checks.append(
                ValidationCheck(
                    check_id="withholding_rule_period",
                    layer=ValidationLayer.FISCAL,
                    status=ValidationStatus.NOT_EVALUATED,
                    severity=ValidationSeverity.WARNING,
                    message="La periode est requise pour selectionner les regles RAS.",
                ),
            )
        else:
            for index, record in enumerate(declaration.records, start=1):
                checks.extend(
                    _record_checks(
                        record,
                        index,
                        rules,
                        period_end,
                        tolerance,
                    ),
                )
            if deadline_rules:
                checks.extend(
                    _deadline_checks(
                        declaration,
                        deadline_rules,
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
    line_codes = [
        value
        for record in declaration.records
        if (value := _text_value(record, "line_code")) is not None
    ]
    duplicates = tuple(
        sorted({code for code in line_codes if line_codes.count(code) > 1}),
    )
    if not declaration.records:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = "Aucune ligne RAS n'est disponible."
    elif duplicates:
        status = ValidationStatus.FAILED
        severity = ValidationSeverity.ERROR
        message = "Des codes de ligne RAS sont dupliques."
    else:
        status = ValidationStatus.PASSED
        severity = ValidationSeverity.INFO
        message = "La structure des lignes RAS est exploitable."
    return ValidationCheck(
        check_id="withholding_structure",
        layer=ValidationLayer.STRUCTURE,
        status=status,
        severity=severity,
        message=message,
        affected_lines=duplicates,
    )


def _completeness_check(
    declaration: CanonicalTaxDeclaration,
) -> ValidationCheck:
    incomplete: list[str] = []
    for index, record in enumerate(declaration.records, start=1):
        fields = {field.name: field.normalized_value for field in record.fields}
        if any(fields.get(name) is None for name in _SELECTION_FIELDS):
            incomplete.append(_record_identifier(record, index))
    if incomplete or not declaration.records:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = "Des donnees necessaires au controle RAS sont non resolues."
    else:
        status = ValidationStatus.PASSED
        severity = ValidationSeverity.INFO
        message = "Les donnees necessaires au controle RAS sont presentes."
    return ValidationCheck(
        check_id="withholding_completeness",
        layer=ValidationLayer.COMPLETENESS,
        status=status,
        severity=severity,
        message=message,
        affected_lines=tuple(incomplete),
    )


def _record_checks(
    record: CanonicalRecord,
    index: int,
    rules: tuple[WithholdingValidationRule, ...],
    period_end: date,
    tolerance: Decimal,
) -> tuple[ValidationCheck, ...]:
    identifier = _record_identifier(record, index)
    regime_text = _text_value(record, "withholding_regime")
    category = _text_value(record, "rate_category")
    if regime_text is None or category is None:
        return (_unresolved_rule_check(identifier),)
    try:
        regime = WithholdingRegime(regime_text)
    except ValueError:
        return (_unresolved_rule_check(identifier),)
    candidates = tuple(
        rule
        for rule in rules
        if rule.regime is regime
        and rule.rate_category == category
        and rule.valid_from <= period_end
        and (rule.valid_to is None or period_end <= rule.valid_to)
    )
    if len(candidates) != 1:
        return (_unresolved_rule_check(identifier),)
    rule = candidates[0]
    return (
        _rate_check(record, identifier, rule),
        _amount_check(record, identifier, rule, tolerance),
    )


def _unresolved_rule_check(identifier: str) -> ValidationCheck:
    return ValidationCheck(
        check_id=f"withholding_rule_{identifier}",
        layer=ValidationLayer.FISCAL,
        status=ValidationStatus.NOT_EVALUATED,
        severity=ValidationSeverity.WARNING,
        message="Aucune regle RAS unique ne correspond aux donnees explicites.",
        affected_lines=(identifier,),
    )


def _deadline_checks(
    declaration: CanonicalTaxDeclaration,
    rules: tuple[WithholdingDeadlineRule, ...],
    period_end: date,
    filing_date: date | None,
) -> tuple[ValidationCheck, ...]:
    regimes = _declaration_regimes(declaration)
    if not regimes:
        return (
            ValidationCheck(
                check_id="withholding_deadline_regime",
                layer=ValidationLayer.FISCAL,
                status=ValidationStatus.NOT_EVALUATED,
                severity=ValidationSeverity.WARNING,
                message="Le regime RAS est requis pour calculer l'echeance.",
            ),
        )
    return tuple(
        _deadline_check(regime, rules, period_end, filing_date)
        for regime in regimes
    )


def _deadline_check(
    regime: WithholdingRegime,
    rules: tuple[WithholdingDeadlineRule, ...],
    period_end: date,
    filing_date: date | None,
) -> ValidationCheck:
    candidates = tuple(
        rule
        for rule in rules
        if rule.regime is regime
        and rule.valid_from <= period_end
        and (rule.valid_to is None or period_end <= rule.valid_to)
    )
    if len(candidates) != 1:
        return ValidationCheck(
            check_id=f"withholding_deadline_{regime.value}",
            layer=ValidationLayer.FISCAL,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Aucune regle d'echeance RAS unique n'est applicable.",
        )
    rule = candidates[0]
    expected_date = _expected_deadline(period_end, rule)
    if filing_date is None:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = "La date de depot RAS n'est pas renseignee."
    else:
        passed = filing_date <= expected_date
        status = ValidationStatus.PASSED if passed else ValidationStatus.FAILED
        severity = ValidationSeverity.INFO if passed else ValidationSeverity.ERROR
        message = "La declaration RAS respecte l'echeance." if passed else (
            "La declaration RAS est deposee apres l'echeance."
        )
    return ValidationCheck(
        check_id=f"withholding_deadline_{regime.value}",
        layer=ValidationLayer.FISCAL,
        status=status,
        severity=severity,
        message=message,
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_date=expected_date,
        actual_date=filing_date,
    )


def _expected_deadline(
    period_end: date,
    rule: WithholdingDeadlineRule,
) -> date:
    if rule.schedule is not WithholdingDeadlineSchedule.NEXT_MONTH_DAY:
        raise ValueError("unsupported withholding deadline schedule")
    if period_end.month == 12:
        return date(period_end.year + 1, 1, rule.deadline_day)
    return date(period_end.year, period_end.month + 1, rule.deadline_day)


def _declaration_regimes(
    declaration: CanonicalTaxDeclaration,
) -> tuple[WithholdingRegime, ...]:
    regimes: set[WithholdingRegime] = set()
    for record in declaration.records:
        value = _text_value(record, "withholding_regime")
        if value is None:
            continue
        try:
            regimes.add(WithholdingRegime(value))
        except ValueError:
            continue
    return tuple(sorted(regimes, key=lambda regime: regime.value))


def _rate_check(
    record: CanonicalRecord,
    identifier: str,
    rule: WithholdingValidationRule,
) -> ValidationCheck:
    actual = _decimal_value(record, "tax_rate")
    if actual is None:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        difference = None
        message = "Le taux RAS declare n'est pas resolu."
    else:
        difference = actual - rule.rate
        passed = difference == 0
        status = ValidationStatus.PASSED if passed else ValidationStatus.FAILED
        severity = ValidationSeverity.INFO if passed else ValidationSeverity.ERROR
        message = "Le taux RAS correspond au referentiel." if passed else (
            "Le taux RAS ne correspond pas au referentiel."
        )
    return ValidationCheck(
        check_id=f"withholding_rate_{identifier}",
        layer=ValidationLayer.FISCAL,
        status=status,
        severity=severity,
        message=message,
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_value=rule.rate,
        actual_value=actual,
        difference=difference,
        affected_lines=(identifier,),
    )


def _amount_check(
    record: CanonicalRecord,
    identifier: str,
    rule: WithholdingValidationRule,
    tolerance: Decimal,
) -> ValidationCheck:
    base = _decimal_value(record, rule.base_field.value)
    actual = _decimal_value(record, "withheld_amount")
    expected = base * rule.rate / Decimal(100) if base is not None else None
    if expected is None or actual is None:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        difference = None
        message = "La base ou la retenue RAS n'est pas resolue."
    else:
        difference = actual - expected
        passed = abs(difference) <= tolerance
        status = ValidationStatus.PASSED if passed else ValidationStatus.FAILED
        severity = ValidationSeverity.INFO if passed else ValidationSeverity.ERROR
        message = "Le montant RAS correspond a la base et au taux." if passed else (
            "Le montant RAS ne correspond pas a la base et au taux."
        )
    return ValidationCheck(
        check_id=f"withholding_amount_{identifier}",
        layer=ValidationLayer.ARITHMETIC,
        status=status,
        severity=severity,
        message=message,
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        expected_value=expected,
        actual_value=actual,
        difference=difference,
        affected_lines=(identifier,),
    )


def _record_identifier(record: CanonicalRecord, index: int) -> str:
    return _text_value(record, "line_code") or str(index)


def _text_value(record: CanonicalRecord, name: str) -> str | None:
    value = next(
        (
            field.normalized_value
            for field in record.fields
            if field.name == name
        ),
        None,
    )
    return value if isinstance(value, str) else None


def _decimal_value(record: CanonicalRecord, name: str) -> Decimal | None:
    value = next(
        (
            field.normalized_value
            for field in record.fields
            if field.name == name
        ),
        None,
    )
    return value if isinstance(value, Decimal) else None


def _overall_status(
    checks: tuple[ValidationCheck, ...],
) -> OverallValidationStatus:
    if any(check.status is ValidationStatus.FAILED for check in checks):
        return OverallValidationStatus.FAILED
    if any(check.status is ValidationStatus.NOT_EVALUATED for check in checks):
        return OverallValidationStatus.INCOMPLETE
    return OverallValidationStatus.PASSED
