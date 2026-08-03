from decimal import Decimal
from pathlib import Path

import pytest

from app.tax_declaration.domain import (
    CanonicalTaxDeclaration,
    DeclarationSourceFormat,
    SourceReference,
)
from app.tax_declaration.supporting_evidence import InvoiceEvidence, PaymentEvidence
from app.tax_declaration.supporting_evidence_validation import (
    SupportingEvidenceValidator,
)
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationStatus,
)
from app.tax_declaration.vat_tabular_extractor import VatTabularExtractor


def test_reconciles_declaration_invoices_and_payments(tmp_path: Path) -> None:
    report = SupportingEvidenceValidator().validate(
        _declaration(tmp_path, "20;TVA deductible;180\n"),
        (_invoice(),),
        (_payment(),),
        declaration_currency="XOF",
        tolerance=Decimal("0"),
    )

    assert report.overall_status is OverallValidationStatus.PASSED
    assert all(check.status is ValidationStatus.PASSED for check in report.checks)
    line_check = _check(report, "supporting_invoice_line_20")
    assert line_check.expected_value == Decimal("180")
    assert line_check.actual_value == Decimal("180")
    assert line_check.difference == Decimal("0")


def test_fails_when_invoice_arithmetic_is_inconsistent(tmp_path: Path) -> None:
    report = SupportingEvidenceValidator().validate(
        _declaration(tmp_path, "20;TVA deductible;180\n"),
        (_invoice(gross_amount=Decimal("1200")),),
        (_payment(amount=Decimal("1200")),),
        declaration_currency="XOF",
        tolerance=Decimal("0"),
    )

    assert report.overall_status is OverallValidationStatus.FAILED
    assert (
        _check(report, "supporting_invoice_arithmetic").status
        is ValidationStatus.FAILED
    )


def test_fails_when_invoices_do_not_justify_declaration(tmp_path: Path) -> None:
    report = SupportingEvidenceValidator().validate(
        _declaration(tmp_path, "20;TVA deductible;200\n"),
        (_invoice(),),
        (_payment(),),
        declaration_currency="XOF",
        tolerance=Decimal("0"),
    )

    check = _check(report, "supporting_invoice_line_20")
    assert check.status is ValidationStatus.FAILED
    assert check.expected_value == Decimal("180")
    assert check.actual_value == Decimal("200")
    assert check.difference == Decimal("20")


def test_missing_payments_make_report_incomplete(tmp_path: Path) -> None:
    report = SupportingEvidenceValidator().validate(
        _declaration(tmp_path, "20;TVA deductible;180\n"),
        (_invoice(),),
        (),
        declaration_currency="XOF",
        tolerance=Decimal("0"),
    )

    assert report.overall_status is OverallValidationStatus.INCOMPLETE
    assert (
        _check(report, "supporting_payment_reconciliation").status
        is ValidationStatus.NOT_EVALUATED
    )


@pytest.mark.parametrize("case", ["duplicate", "payment_currency", "invoice_currency"])
def test_rejects_duplicate_or_currency_conflicts(
    tmp_path: Path,
    case: str,
) -> None:
    invoices: tuple[InvoiceEvidence, ...]
    payments: tuple[PaymentEvidence, ...]
    if case == "duplicate":
        invoices = (_invoice(), _invoice())
        payments = (_payment(),)
        failed_check = "supporting_invoice_identifiers"
    elif case == "payment_currency":
        invoices = (_invoice(),)
        payments = (_payment(currency="EUR"),)
        failed_check = "supporting_payment_reconciliation"
    else:
        invoices = (_invoice(currency="EUR"),)
        payments = (_payment(currency="EUR"),)
        failed_check = "supporting_invoice_assignment"
    report = SupportingEvidenceValidator().validate(
        _declaration(tmp_path, "20;TVA deductible;180\n"),
        invoices,
        payments,
        declaration_currency="XOF",
        tolerance=Decimal("0"),
    )

    assert _check(report, failed_check).status is ValidationStatus.FAILED


def test_rejects_negative_tolerance(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="tolerance cannot be negative"):
        SupportingEvidenceValidator().validate(
            _declaration(tmp_path, "20;TVA deductible;180\n"),
            (_invoice(),),
            (_payment(),),
            declaration_currency="XOF",
            tolerance=Decimal("-1"),
        )


def _invoice(
    *,
    gross_amount: Decimal = Decimal("1180"),
    currency: str = "XOF",
) -> InvoiceEvidence:
    return InvoiceEvidence(
        invoice_id="F-001",
        partner_identifier=None,
        partner_identifier_type=None,
        net_amount=Decimal("1000"),
        vat_amount=Decimal("180"),
        gross_amount=gross_amount,
        currency=currency,
        declaration_line="20",
        source_reference=_source("factures.csv"),
        locator="row:2",
    )


def _payment(
    *,
    amount: Decimal = Decimal("1180"),
    currency: str = "XOF",
) -> PaymentEvidence:
    return PaymentEvidence(
        payment_id="P-001",
        invoice_id="F-001",
        amount=amount,
        currency=currency,
        source_reference=_source("paiements.csv"),
        locator="row:2",
    )


def _declaration(tmp_path: Path, row: str) -> CanonicalTaxDeclaration:
    path = tmp_path / "declaration.csv"
    path.write_text("Code;Nature;Montant\n" + row, encoding="utf-8")
    return VatTabularExtractor().extract(path, _source(path.name))


def _source(file_name: str) -> SourceReference:
    return SourceReference(
        file_name=file_name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="a" * 64,
    )


def _check(
    report: TaxDeclarationValidationReport,
    check_id: str,
) -> ValidationCheck:
    return next(check for check in report.checks if check.check_id == check_id)
