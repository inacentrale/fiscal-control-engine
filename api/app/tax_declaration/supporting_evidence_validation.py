from __future__ import annotations

from collections import Counter
from decimal import Decimal

from app.tax_declaration.domain import (
    CanonicalRecord,
    CanonicalTaxDeclaration,
    TaxDeclarationType,
)
from app.tax_declaration.partner_reconciliation import (
    PartnerMatchStatus,
    PartnerReconciler,
    PartnerReference,
)
from app.tax_declaration.supporting_evidence import InvoiceEvidence, PaymentEvidence
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationLayer,
    ValidationSeverity,
    ValidationStatus,
)
from app.tax_declaration.vat_ledger_mapping import (
    validate_declaration_record_fields,
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
        record_selector_field: str = "line_code",
        declaration_amount_field: str = "tax_amount",
    ) -> TaxDeclarationValidationReport:
        if not declaration_currency.strip():
            raise ValueError("declaration currency is required")
        if tolerance < 0:
            raise ValueError("tolerance cannot be negative")
        validate_declaration_record_fields(
            declaration.declaration_type,
            record_selector_field,
            declaration_amount_field,
        )
        arithmetic_checks = (
            (_invoice_arithmetic_check(invoices, tolerance),)
            if declaration.declaration_type is TaxDeclarationType.VAT
            else ()
        )
        checks = (
            _invoice_identity_check(invoices),
            *_partner_reconciliation_checks(declaration, invoices),
            *arithmetic_checks,
            *_declaration_evidence_checks(
                declaration,
                invoices,
                declaration_currency,
                tolerance,
                record_selector_field,
                declaration_amount_field,
            ),
            _payment_reconciliation_check(invoices, payments, tolerance),
        )
        return TaxDeclarationValidationReport(
            overall_status=_overall_status(checks),
            checks=checks,
        )


def _partner_reconciliation_checks(
    declaration: CanonicalTaxDeclaration,
    invoices: tuple[InvoiceEvidence, ...],
) -> tuple[ValidationCheck, ...]:
    declaration_partners = tuple(
        _declaration_partner(record_index, record)
        for record_index, record in enumerate(declaration.records, start=1)
        if _record_has_partner(record)
    )
    evidence_partners = tuple(
        PartnerReference(
            reference_id=invoice.invoice_id or invoice.locator,
            identifier=invoice.partner_identifier,
            identifier_type=invoice.partner_identifier_type,
            name=invoice.partner_name,
        )
        for invoice in invoices
        if invoice.partner_identifier is not None or invoice.partner_name is not None
    )
    if not declaration_partners and not evidence_partners:
        return ()
    if not declaration_partners:
        return (
            ValidationCheck(
                check_id="supporting_partner_reconciliation",
                layer=ValidationLayer.SUPPORTING_DOCUMENTS,
                status=ValidationStatus.NOT_EVALUATED,
                severity=ValidationSeverity.WARNING,
                message="Aucun partenaire de declaration n'est disponible.",
                affected_lines=tuple(
                    partner.reference_id for partner in evidence_partners
                ),
            ),
        )
    matches = PartnerReconciler().reconcile(
        declaration_partners,
        evidence_partners,
    )
    conflicts = tuple(
        match.evidence_reference_id
        for match in matches
        if match.status in {PartnerMatchStatus.CONFLICT, PartnerMatchStatus.UNMATCHED}
    )
    uncertain = tuple(
        match.evidence_reference_id
        for match in matches
        if match.status in {PartnerMatchStatus.POTENTIAL, PartnerMatchStatus.UNRESOLVED}
    )
    if conflicts:
        status = ValidationStatus.FAILED
        severity = ValidationSeverity.ERROR
        message = "Des partenaires sont absents ou correspondent a plusieurs candidats."
    elif uncertain:
        status = ValidationStatus.NOT_EVALUATED
        severity = ValidationSeverity.WARNING
        message = "Des rapprochements partenaires restent potentiels."
    else:
        status = ValidationStatus.PASSED
        severity = ValidationSeverity.INFO
        message = "Les partenaires sont rapproches par identifiant type et valeur."
    return (
        ValidationCheck(
            check_id="supporting_partner_reconciliation",
            layer=ValidationLayer.SUPPORTING_DOCUMENTS,
            status=status,
            severity=severity,
            message=message,
            affected_lines=tuple((*conflicts, *uncertain)),
        ),
    )


def _record_has_partner(record: CanonicalRecord) -> bool:
    return any(
        field.name in {"partner_identifier", "partner_name"}
        and field.normalized_value is not None
        for field in record.fields
    )


def _declaration_partner(
    record_index: int,
    record: CanonicalRecord,
) -> PartnerReference:
    fields = {
        field.name: field.normalized_value
        for field in record.fields
    }
    line = fields.get("line_code") or fields.get("line_number") or record_index
    return PartnerReference(
        reference_id=str(line),
        identifier=_optional_text(fields.get("partner_identifier")),
        identifier_type=_optional_text(fields.get("partner_identifier_type")),
        name=_optional_text(fields.get("partner_name")),
    )


def _optional_text(value: object) -> str | None:
    return str(value) if value is not None else None


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


def _declaration_evidence_checks(
    declaration: CanonicalTaxDeclaration,
    invoices: tuple[InvoiceEvidence, ...],
    currency: str,
    tolerance: Decimal,
    selector_field: str,
    amount_field: str,
) -> tuple[ValidationCheck, ...]:
    expected_currency = currency.upper()
    grouped: dict[str, Decimal] = {}
    unresolved: list[str] = []
    wrong_currency: list[str] = []
    for invoice in invoices:
        identifier = invoice.invoice_id or invoice.locator
        evidence_amount = invoice.declaration_amount
        if (
            evidence_amount is None
            and declaration.declaration_type is TaxDeclarationType.VAT
        ):
            evidence_amount = invoice.vat_amount
        if (
            invoice.declaration_line is None
            or evidence_amount is None
            or invoice.currency is None
        ):
            unresolved.append(identifier)
            continue
        if invoice.currency != expected_currency:
            wrong_currency.append(identifier)
            continue
        grouped[invoice.declaration_line] = (
            grouped.get(invoice.declaration_line, Decimal(0))
            + evidence_amount
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
                _declaration_line_check(
                    declaration,
                    line,
                    amount,
                    tolerance,
                    selector_field,
                    amount_field,
                )
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
    selector_field: str,
    amount_field: str,
) -> ValidationCheck:
    declared = _record_amount(
        declaration,
        selector_field=selector_field,
        selector_value=line,
        amount_field=amount_field,
    )
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
        expected_payment = (
            invoice.payment_expected_amount
            if invoice.payment_expected_amount is not None
            else invoice.gross_amount
        )
        if invoice.invoice_id is None or expected_payment is None:
            unresolved.append(invoice.invoice_id or invoice.locator)
            continue
        paid = payments_by_invoice.get(invoice.invoice_id)
        if paid is None:
            unresolved.append(invoice.invoice_id)
        elif abs(paid - expected_payment) > tolerance:
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


def _overall_status(
    checks: tuple[ValidationCheck, ...],
) -> OverallValidationStatus:
    if any(check.status is ValidationStatus.FAILED for check in checks):
        return OverallValidationStatus.FAILED
    if any(check.status is ValidationStatus.NOT_EVALUATED for check in checks):
        return OverallValidationStatus.INCOMPLETE
    return OverallValidationStatus.PASSED
