from __future__ import annotations

from collections import Counter
from decimal import Decimal

from app.tax_declaration.domain import CanonicalTaxDeclaration
from app.tax_declaration.supporting_evidence import InvoiceEvidence, PaymentEvidence
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationLayer,
    ValidationSeverity,
    ValidationStatus,
)


class SupportingEvidenceValidator:
    def validate(
        self,
        declaration: CanonicalTaxDeclaration,
        invoices: tuple[InvoiceEvidence, ...],
        payments: tuple[PaymentEvidence, ...],
        *,
        declaration_currency: str,
        tolerance: Decimal,
    ) -> TaxDeclarationValidationReport:
        if not declaration_currency.strip():
            raise ValueError("declaration currency is required")
        if tolerance < 0:
            raise ValueError("tolerance cannot be negative")
        checks = (
            _invoice_identity_check(invoices),
            _invoice_arithmetic_check(invoices, tolerance),
            *_declaration_invoice_checks(
                declaration,
                invoices,
                declaration_currency,
                tolerance,
            ),
            _payment_reconciliation_check(invoices, payments, tolerance),
        )
        return TaxDeclarationValidationReport(
            overall_status=_overall_status(checks),
            checks=checks,
        )


def _invoice_identity_check(
    invoices: tuple[InvoiceEvidence, ...],
) -> ValidationCheck:
    if not invoices:
        return ValidationCheck(
            check_id="supporting_invoice_identifiers",
            layer=ValidationLayer.SUPPORTING_DOCUMENTS,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Aucune facture n'a ete fournie.",
        )
    identifiers = [invoice.invoice_id for invoice in invoices if invoice.invoice_id]
    duplicates = tuple(
        sorted(
            identifier
            for identifier, count in Counter(identifiers).items()
            if count > 1
        ),
    )
    missing_count = sum(invoice.invoice_id is None for invoice in invoices)
    failed = bool(duplicates or missing_count)
    return ValidationCheck(
        check_id="supporting_invoice_identifiers",
        layer=ValidationLayer.SUPPORTING_DOCUMENTS,
        status=ValidationStatus.FAILED if failed else ValidationStatus.PASSED,
        severity=ValidationSeverity.ERROR if failed else ValidationSeverity.INFO,
        message=(
            "Factures sans identifiant ou dupliquees."
            if failed
            else "Les identifiants de factures sont uniques."
        ),
        affected_lines=duplicates,
    )


def _invoice_arithmetic_check(
    invoices: tuple[InvoiceEvidence, ...],
    tolerance: Decimal,
) -> ValidationCheck:
    unresolved: list[str] = []
    mismatches: list[str] = []
    for invoice in invoices:
        identifier = invoice.invoice_id or invoice.locator
        net_amount = invoice.net_amount
        vat_amount = invoice.vat_amount
        gross_amount = invoice.gross_amount
        if net_amount is None or vat_amount is None or gross_amount is None:
            unresolved.append(identifier)
            continue
        expected = net_amount + vat_amount
        if abs(gross_amount - expected) > tolerance:
            mismatches.append(identifier)
    if mismatches:
        status = ValidationStatus.FAILED
        severity = ValidationSeverity.ERROR
        message = "Des totaux facture ne correspondent pas a HT + TVA."
    elif unresolved:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = "Des montants facture ne sont pas resolus."
    else:
        status = ValidationStatus.PASSED
        severity = ValidationSeverity.INFO
        message = "Les calculs HT + TVA = TTC sont coherents."
    return ValidationCheck(
        check_id="supporting_invoice_arithmetic",
        layer=ValidationLayer.SUPPORTING_DOCUMENTS,
        status=status,
        severity=severity,
        message=message,
        affected_lines=tuple((*mismatches, *unresolved)),
    )


def _declaration_invoice_checks(
    declaration: CanonicalTaxDeclaration,
    invoices: tuple[InvoiceEvidence, ...],
    currency: str,
    tolerance: Decimal,
) -> tuple[ValidationCheck, ...]:
    expected_currency = currency.upper()
    grouped: dict[str, Decimal] = {}
    unresolved: list[str] = []
    wrong_currency: list[str] = []
    for invoice in invoices:
        identifier = invoice.invoice_id or invoice.locator
        if (
            invoice.declaration_line is None
            or invoice.vat_amount is None
            or invoice.currency is None
        ):
            unresolved.append(identifier)
            continue
        if invoice.currency != expected_currency:
            wrong_currency.append(identifier)
            continue
        grouped[invoice.declaration_line] = (
            grouped.get(invoice.declaration_line, Decimal(0)) + invoice.vat_amount
        )
    assignment_check = _invoice_assignment_check(unresolved, wrong_currency)
    if not grouped:
        return (
            assignment_check,
            ValidationCheck(
                check_id="supporting_invoice_declaration",
                layer=ValidationLayer.SUPPORTING_DOCUMENTS,
                status=ValidationStatus.NOT_EVALUATED,
                severity=ValidationSeverity.WARNING,
                message="Aucune facture n'est affectee a une ligne de declaration.",
            ),
        )
    return tuple(
        (
            assignment_check,
            *(
                _declaration_line_check(declaration, line, amount, tolerance)
                for line, amount in sorted(grouped.items())
            ),
        )
    )


def _invoice_assignment_check(
    unresolved: list[str],
    wrong_currency: list[str],
) -> ValidationCheck:
    if wrong_currency:
        status = ValidationStatus.FAILED
        severity = ValidationSeverity.ERROR
        message = "Des factures utilisent une devise differente de la declaration."
    elif unresolved:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = "Ligne, TVA ou devise non resolue pour certaines factures."
    else:
        status = ValidationStatus.PASSED
        severity = ValidationSeverity.INFO
        message = "Toutes les factures sont affectees dans la devise attendue."
    return ValidationCheck(
        check_id="supporting_invoice_assignment",
        layer=ValidationLayer.SUPPORTING_DOCUMENTS,
        status=status,
        severity=severity,
        message=message,
        affected_lines=tuple((*wrong_currency, *unresolved)),
    )


def _declaration_line_check(
    declaration: CanonicalTaxDeclaration,
    line: str,
    evidence_amount: Decimal,
    tolerance: Decimal,
) -> ValidationCheck:
    declared = _line_amount(declaration, line)
    if declared is None:
        return ValidationCheck(
            check_id=f"supporting_invoice_line_{line}",
            layer=ValidationLayer.SUPPORTING_DOCUMENTS,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Montant de declaration absent pour les factures affectees.",
            affected_lines=(line,),
        )
    difference = declared - evidence_amount
    passed = abs(difference) <= tolerance
    return ValidationCheck(
        check_id=f"supporting_invoice_line_{line}",
        layer=ValidationLayer.SUPPORTING_DOCUMENTS,
        status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        severity=ValidationSeverity.INFO if passed else ValidationSeverity.ERROR,
        message=(
            "Les factures justifient la ligne de declaration."
            if passed
            else "Les factures ne justifient pas la ligne de declaration."
        ),
        expected_value=evidence_amount,
        actual_value=declared,
        difference=difference,
        affected_lines=(line,),
    )


def _payment_reconciliation_check(
    invoices: tuple[InvoiceEvidence, ...],
    payments: tuple[PaymentEvidence, ...],
    tolerance: Decimal,
) -> ValidationCheck:
    if not payments:
        return ValidationCheck(
            check_id="supporting_payment_reconciliation",
            layer=ValidationLayer.PAYMENT_RECONCILIATION,
            status=ValidationStatus.NOT_EVALUATED,
            severity=ValidationSeverity.WARNING,
            message="Aucun paiement n'a ete fourni.",
        )
    payments_by_invoice: dict[str, Decimal] = {}
    invalid_payments: list[str] = []
    invoice_by_id = {
        invoice.invoice_id: invoice
        for invoice in invoices
        if invoice.invoice_id is not None
    }
    payment_ids = [payment.payment_id for payment in payments if payment.payment_id]
    duplicate_payment_ids = {
        identifier
        for identifier, count in Counter(payment_ids).items()
        if count > 1
    }
    for payment in payments:
        invoice_id = payment.invoice_id
        invoice = invoice_by_id.get(invoice_id) if invoice_id is not None else None
        if (
            payment.payment_id is None
            or payment.payment_id in duplicate_payment_ids
            or invoice is None
            or payment.amount is None
            or payment.currency is None
            or invoice.currency is None
            or payment.currency != invoice.currency
        ):
            invalid_payments.append(payment.payment_id or payment.locator)
            continue
        assert invoice_id is not None
        payments_by_invoice[invoice_id] = (
            payments_by_invoice.get(invoice_id, Decimal(0)) + payment.amount
        )
    unresolved: list[str] = []
    mismatches: list[str] = []
    for invoice in invoices:
        if invoice.invoice_id is None or invoice.gross_amount is None:
            unresolved.append(invoice.invoice_id or invoice.locator)
            continue
        paid = payments_by_invoice.get(invoice.invoice_id)
        if paid is None:
            unresolved.append(invoice.invoice_id)
        elif abs(paid - invoice.gross_amount) > tolerance:
            mismatches.append(invoice.invoice_id)
    if invalid_payments or mismatches:
        status = ValidationStatus.FAILED
        severity = ValidationSeverity.ERROR
        message = "Des paiements sont invalides ou non rapproches."
    elif unresolved:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = "Des factures ne disposent pas d'un paiement complet rapproche."
    else:
        status = ValidationStatus.PASSED
        severity = ValidationSeverity.INFO
        message = "Les paiements sont rapproches aux factures."
    return ValidationCheck(
        check_id="supporting_payment_reconciliation",
        layer=ValidationLayer.PAYMENT_RECONCILIATION,
        status=status,
        severity=severity,
        message=message,
        affected_lines=tuple((*invalid_payments, *mismatches, *unresolved)),
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
