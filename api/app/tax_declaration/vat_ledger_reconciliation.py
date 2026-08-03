from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from app.ledger_analysis.analysis_service import LedgerMetricsReport
from app.tax_declaration.domain import CanonicalTaxDeclaration, TaxDeclarationType
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationLayer,
    ValidationSeverity,
    ValidationStatus,
)
from app.tax_declaration.vat_ledger_mapping import (
    LedgerAmountSide,
    VatLedgerAccountMapping,
    applicable_vat_ledger_mappings,
)


class LedgerMetricsCalculator(Protocol):
    def calculate_metrics(
        self,
        file_path: Path,
        sheet_name: str,
        filters: dict[str, object],
        metrics: tuple[str, ...],
        top_by: str | None = None,
        top_limit: int = 10,
    ) -> LedgerMetricsReport: ...


@dataclass(frozen=True)
class VatLedgerEvidence:
    declaration_line: str
    currency: str
    amount: Decimal
    entry_count: int
    used_entry_count: int
    excluded_entry_count: int
    accounts: tuple[str, ...]
    mapping_ids: tuple[str, ...]
    source_references: tuple[str, ...]
    tolerance: Decimal
    declaration_type: TaxDeclarationType = TaxDeclarationType.VAT
    record_selector_field: str = "line_code"
    declaration_amount_field: str = "tax_amount"


class VatLedgerEvidenceBuilder:
    def build(
        self,
        calculator: LedgerMetricsCalculator,
        ledger_path: Path,
        sheet_name: str,
        mappings: tuple[VatLedgerAccountMapping, ...],
        *,
        period_end: date,
    ) -> tuple[VatLedgerEvidence, ...]:
        applicable = applicable_vat_ledger_mappings(mappings, period_end)
        grouped: dict[
            tuple[TaxDeclarationType, str, str, str, str],
            list[tuple[VatLedgerAccountMapping, dict[str, object]]],
        ] = {}
        for mapping in applicable:
            report = calculator.calculate_metrics(
                ledger_path,
                sheet_name,
                filters={
                    "account": mapping.account,
                    "period": str(period_end.month),
                    "fiscal_year": str(period_end.year),
                },
                metrics=("balance",),
            )
            reconciliation = report.balance_reconciliation
            if reconciliation is None:
                continue
            by_currency = reconciliation.get("by_currency")
            if not isinstance(by_currency, dict):
                continue
            currency_totals = by_currency.get(mapping.currency)
            if not isinstance(currency_totals, dict):
                currency_totals = _empty_totals()
            grouped.setdefault(
                (
                    mapping.declaration_type,
                    mapping.record_selector_field,
                    mapping.declaration_amount_field,
                    mapping.declaration_line,
                    mapping.currency,
                ),
                [],
            ).append((mapping, currency_totals))
        return tuple(
            _to_evidence(key, rows) for key, rows in sorted(grouped.items())
        )


class VatLedgerReconciler:
    def reconcile(
        self,
        declaration: CanonicalTaxDeclaration,
        evidence: tuple[VatLedgerEvidence, ...],
        *,
        declaration_currency: str,
    ) -> TaxDeclarationValidationReport:
        checks = tuple(
            _reconcile_evidence(declaration, item, declaration_currency)
            for item in evidence
        )
        if not checks:
            checks = (
                ValidationCheck(
                    check_id="tax_ledger_mapping_missing",
                    layer=ValidationLayer.RECONCILIATION,
                    status=ValidationStatus.NOT_EVALUATED,
                    severity=ValidationSeverity.WARNING,
                    message="Rapprochement non evalue: aucune cartographie applicable.",
                ),
            )
        return TaxDeclarationValidationReport(
            overall_status=_overall_status(checks),
            checks=checks,
        )


def _to_evidence(
    key: tuple[TaxDeclarationType, str, str, str, str],
    rows: list[tuple[VatLedgerAccountMapping, dict[str, object]]],
) -> VatLedgerEvidence:
    declaration_type, selector_field, amount_field, declaration_line, currency = key
    amount = Decimal(0)
    entry_count = 0
    used_entry_count = 0
    excluded_entry_count = 0
    for mapping, totals in rows:
        side_key = (
            "debit_total"
            if mapping.amount_side is LedgerAmountSide.DEBIT
            else "credit_total"
        )
        amount += Decimal(str(totals.get(side_key, 0)))
        entry_count += _integer_total(totals, "entry_count")
        used_entry_count += _integer_total(totals, "used_entry_count")
        excluded_entry_count += _integer_total(totals, "excluded_entry_count")
    return VatLedgerEvidence(
        declaration_line=declaration_line,
        currency=currency,
        amount=amount,
        entry_count=entry_count,
        used_entry_count=used_entry_count,
        excluded_entry_count=excluded_entry_count,
        accounts=tuple(mapping.account for mapping, _ in rows),
        mapping_ids=tuple(mapping.mapping_id for mapping, _ in rows),
        source_references=tuple(mapping.source_reference for mapping, _ in rows),
        tolerance=max(mapping.tolerance for mapping, _ in rows),
        declaration_type=declaration_type,
        record_selector_field=selector_field,
        declaration_amount_field=amount_field,
    )


def _reconcile_evidence(
    declaration: CanonicalTaxDeclaration,
    evidence: VatLedgerEvidence,
    declaration_currency: str,
) -> ValidationCheck:
    check_id = (
        f"tax_ledger_{evidence.declaration_type.value}_"
        f"{evidence.record_selector_field}_{evidence.declaration_line}"
    )
    if declaration.declaration_type is not evidence.declaration_type:
        return ValidationCheck(
            check_id=check_id,
            layer=ValidationLayer.RECONCILIATION,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Rapprochement non evalue: type de declaration incompatible.",
            affected_lines=(evidence.declaration_line,),
        )
    if evidence.currency != declaration_currency.upper():
        return ValidationCheck(
            check_id=check_id,
            layer=ValidationLayer.RECONCILIATION,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Rapprochement non evalue: devises incompatibles.",
            affected_lines=(evidence.declaration_line,),
        )
    declared = _record_amount(
        declaration,
        selector_field=evidence.record_selector_field,
        selector_value=evidence.declaration_line,
        amount_field=evidence.declaration_amount_field,
    )
    if declared is None:
        return ValidationCheck(
            check_id=check_id,
            layer=ValidationLayer.RECONCILIATION,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Rapprochement non evalue: montant declare absent.",
            affected_lines=(evidence.declaration_line,),
        )
    difference = declared - evidence.amount
    passed = (
        abs(difference) <= evidence.tolerance
        and evidence.excluded_entry_count == 0
    )
    return ValidationCheck(
        check_id=check_id,
        layer=ValidationLayer.RECONCILIATION,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "Le montant declare est rapproche du Grand Livre."
            if passed
            else "Le montant declare differe du Grand Livre ou des lignes sont exclues."
        ),
        expected_value=evidence.amount,
        actual_value=declared,
        difference=difference,
        affected_lines=(evidence.declaration_line,),
    )


def _record_amount(
    declaration: CanonicalTaxDeclaration,
    *,
    selector_field: str,
    selector_value: str,
    amount_field: str,
) -> Decimal | None:
    for record in declaration.records:
        fields = {field.name: field for field in record.fields}
        selector = fields.get(selector_field)
        amount = fields.get(amount_field)
        if selector is None or str(selector.normalized_value) != selector_value:
            continue
        if amount is not None and isinstance(amount.normalized_value, Decimal):
            return amount.normalized_value
    return None


def _empty_totals() -> dict[str, object]:
    return {
        "entry_count": 0,
        "used_entry_count": 0,
        "excluded_entry_count": 0,
        "debit_total": 0,
        "credit_total": 0,
    }


def _integer_total(totals: dict[str, object], key: str) -> int:
    value = totals.get(key, 0)
    return int(value) if isinstance(value, int | float) else 0


def _overall_status(
    checks: tuple[ValidationCheck, ...],
) -> OverallValidationStatus:
    if any(check.status is ValidationStatus.FAILED for check in checks):
        return OverallValidationStatus.FAILED
    if any(check.status is ValidationStatus.NOT_EVALUATED for check in checks):
        return OverallValidationStatus.INCOMPLETE
    return OverallValidationStatus.PASSED
