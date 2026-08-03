from decimal import Decimal
from pathlib import Path

import pytest

from app.tax_declaration.document_text_extractor import (
    DeclarationDocumentTextExtractor,
)
from app.tax_declaration.domain import (
    DeclarationSourceFormat,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.supporting_evidence import (
    SupportingEvidenceExtractionError,
    SupportingEvidenceExtractor,
)


def test_extracts_invoice_with_dynamic_partner_identifier(tmp_path: Path) -> None:
    source = tmp_path / "factures.csv"
    source.write_text(
        "Numero facture;Type identifiant partenaire;Identifiant partenaire;"
        "Montant HT;Montant TVA;Montant TTC;Devise;Ligne declaration\n"
        "F-001;IFU;BF123;1 000,00;180,00;1 180,00;xof;20\n",
        encoding="utf-8",
    )

    invoices = SupportingEvidenceExtractor().extract_invoices(
        source,
        _reference(source, DeclarationSourceFormat.CSV),
    )

    assert len(invoices) == 1
    assert invoices[0].invoice_id == "F-001"
    assert invoices[0].partner_identifier_type == "IFU"
    assert invoices[0].partner_identifier == "BF123"
    assert invoices[0].net_amount == Decimal("1000.00")
    assert invoices[0].vat_amount == Decimal("180.00")
    assert invoices[0].gross_amount == Decimal("1180.00")
    assert invoices[0].currency == "XOF"
    assert invoices[0].declaration_line == "20"
    assert invoices[0].locator == "csv;row:2"


def test_partner_identifier_is_optional(tmp_path: Path) -> None:
    source = tmp_path / "factures.csv"
    source.write_text(
        "Facture;Montant HT;TVA;Total TTC;Devise;Ligne TVA\n"
        "F-002;1000;180;1180;XOF;20\n",
        encoding="utf-8",
    )

    invoice = SupportingEvidenceExtractor().extract_invoices(
        source,
        _reference(source, DeclarationSourceFormat.CSV),
    )[0]

    assert invoice.partner_identifier is None
    assert invoice.partner_identifier_type is None


def test_infers_equivalent_partner_identifier_type_from_source_header(
    tmp_path: Path,
) -> None:
    source = tmp_path / "factures-nif.csv"
    source.write_text(
        "Facture;NIF;Montant HT;TVA;Total TTC;Devise;Ligne TVA\n"
        "F-003;0012345;1000;180;1180;XOF;20\n",
        encoding="utf-8",
    )

    invoice = SupportingEvidenceExtractor().extract_invoices(
        source,
        _reference(source, DeclarationSourceFormat.CSV),
    )[0]

    assert invoice.partner_identifier == "0012345"
    assert invoice.partner_identifier_type == "NIF"


def test_extracts_withholding_amount_without_vat_columns(tmp_path: Path) -> None:
    source = tmp_path / "ras-evidence.csv"
    source.write_text(
        "Numero facture;Montant des retenues;Devise;Ligne RAS\n"
        "F-RAS-1;20000;XOF;01\n",
        encoding="utf-8",
    )

    evidence = SupportingEvidenceExtractor().extract_invoices(
        source,
        _reference(source, DeclarationSourceFormat.CSV),
        declaration_type=TaxDeclarationType.WITHHOLDING_TAX,
    )

    assert evidence[0].declaration_amount == Decimal("20000")
    assert evidence[0].vat_amount is None


def test_extracts_payment_and_keeps_invoice_link(tmp_path: Path) -> None:
    source = tmp_path / "paiements.csv"
    source.write_text(
        "Numero paiement;Numero facture;Montant paiement;Devise\n"
        "P-001;F-001;1.180,00;XOF\n",
        encoding="utf-8",
    )

    payment = SupportingEvidenceExtractor().extract_payments(
        source,
        _reference(source, DeclarationSourceFormat.CSV),
    )[0]

    assert payment.payment_id == "P-001"
    assert payment.invoice_id == "F-001"
    assert payment.amount == Decimal("1180.00")
    assert payment.currency == "XOF"


def test_rejects_unresolved_invoice_structure(tmp_path: Path) -> None:
    source = tmp_path / "factures.csv"
    source.write_text("Facture;Montant\nF-001;1180\n", encoding="utf-8")

    with pytest.raises(
        SupportingEvidenceExtractionError,
        match="invoice evidence structure is unresolved",
    ):
        SupportingEvidenceExtractor().extract_invoices(
            source,
            _reference(source, DeclarationSourceFormat.CSV),
        )


def test_extracts_invoices_from_namespaced_xml(tmp_path: Path) -> None:
    source = tmp_path / "factures.xml"
    source.write_text(
        "<Invoices xmlns='urn:test'><Invoice>"
        "<invoice_id>F-XML-1</invoice_id>"
        "<net_amount>1000</net_amount><vat_amount>180</vat_amount>"
        "<gross_amount>1180</gross_amount><currency>XOF</currency>"
        "<declaration_line>20</declaration_line>"
        "</Invoice></Invoices>",
        encoding="utf-8",
    )

    invoice = SupportingEvidenceExtractor().extract_invoices(
        source,
        _reference(source, DeclarationSourceFormat.XML),
    )[0]

    assert invoice.invoice_id == "F-XML-1"
    assert invoice.vat_amount == Decimal("180")
    assert invoice.locator == "xml;row:2"


def test_extracts_payments_from_xml(tmp_path: Path) -> None:
    source = tmp_path / "paiements.xml"
    source.write_text(
        "<Payments><Payment><payment_id>P-XML-1</payment_id>"
        "<invoice_id>F-XML-1</invoice_id><amount>1180</amount>"
        "<currency>XOF</currency></Payment></Payments>",
        encoding="utf-8",
    )

    payment = SupportingEvidenceExtractor().extract_payments(
        source,
        _reference(source, DeclarationSourceFormat.XML),
    )[0]

    assert payment.payment_id == "P-XML-1"
    assert payment.invoice_id == "F-XML-1"
    assert payment.amount == Decimal("1180")


def test_rejects_xml_entities(tmp_path: Path) -> None:
    source = tmp_path / "factures.xml"
    source.write_text(
        "<!DOCTYPE x [<!ENTITY secret SYSTEM 'file:///etc/passwd'>]>"
        "<x><invoice_id>&secret;</invoice_id></x>",
        encoding="utf-8",
    )

    with pytest.raises(SupportingEvidenceExtractionError, match="unsafe evidence XML"):
        SupportingEvidenceExtractor().extract_invoices(
            source,
            _reference(source, DeclarationSourceFormat.XML),
        )


@pytest.mark.parametrize(
    ("source_format", "method"),
    [
        (DeclarationSourceFormat.PDF, "pdf_native_text"),
        (DeclarationSourceFormat.IMAGE, "image_ocr"),
    ],
)
def test_extracts_only_explicit_document_tables(
    tmp_path: Path,
    source_format: DeclarationSourceFormat,
    method: str,
) -> None:
    source = tmp_path / "piece.bin"
    source.write_bytes(b"placeholder")
    text = (
        "Numero facture;Montant HT;Montant TVA;Montant TTC;"
        "Devise;Ligne declaration\n"
        "F-DOC-1;1000;180;1180;XOF;20\n"
    )
    extractor = SupportingEvidenceExtractor(_StubTextExtractor(text, method))

    invoice = extractor.extract_invoices(
        source,
        _reference(source, source_format),
    )[0]

    assert invoice.invoice_id == "F-DOC-1"
    assert invoice.locator == f"{method};row:2"


def test_rejects_unstructured_document_text(tmp_path: Path) -> None:
    source = tmp_path / "piece.pdf"
    source.write_bytes(b"placeholder")
    extractor = SupportingEvidenceExtractor(
        _StubTextExtractor("Facture F-1 pour un total de 1180 XOF", "pdf_native_text"),
    )

    with pytest.raises(
        SupportingEvidenceExtractionError,
        match="document evidence structure is unresolved",
    ):
        extractor.extract_invoices(
            source,
            _reference(source, DeclarationSourceFormat.PDF),
        )


def _reference(path: Path, source_format: DeclarationSourceFormat) -> SourceReference:
    return SourceReference(
        file_name=path.name,
        source_format=source_format,
        content_type="text/csv",
        content_sha256="a" * 64,
    )


class _StubTextExtractor(DeclarationDocumentTextExtractor):
    def __init__(self, text: str, method: str) -> None:
        self._text = text
        self._method = method

    def extract_pdf_text(self, source_path: Path) -> tuple[str, str]:
        return self._text, self._method

    def extract_image_text(self, source_path: Path) -> tuple[str, str]:
        return self._text, self._method
