from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from app.ledger_analysis.analysis_service import LedgerMetricsReport
from app.tax_declaration.domain import CanonicalTaxDeclaration
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
            tuple[str, str],
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
                (mapping.declaration_line, mapping.currency),
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
                    check_id="vat_ledger_mapping_missing",
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
    key: tuple[str, str],
    rows: list[tuple[VatLedgerAccountMapping, dict[str, object]]],
) -> VatLedgerEvidence:
    declaration_line, currency = key
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
    )


def _reconcile_evidence(
    declaration: CanonicalTaxDeclaration,
    evidence: VatLedgerEvidence,
    declaration_currency: str,
) -> ValidationCheck:
    if evidence.currency != declaration_currency.upper():
        return ValidationCheck(
            check_id=f"vat_ledger_line_{evidence.declaration_line}",
            layer=ValidationLayer.RECONCILIATION,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Rapprochement non evalue: devises incompatibles.",
            affected_lines=(evidence.declaration_line,),
        )
    declared = _line_amount(declaration, evidence.declaration_line)
    if declared is None:
        return ValidationCheck(
            check_id=f"vat_ledger_line_{evidence.declaration_line}",
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
        check_id=f"vat_ledger_line_{evidence.declaration_line}",
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
