from pathlib import Path

from PIL import Image

from app.tax_declaration.document_text_extractor import (
    DeclarationDocumentTextExtractor,
)
from app.tax_declaration.domain import DeclarationSourceFormat, SourceReference
from app.tax_declaration.vat_text_extractor import VatDocumentExtractor


class FixedOcrEngine:
    def extract_text(self, image: Image.Image) -> str:
        assert image.width > 0
        return "19 | Montant total TVA brute | 1000000 | 18% | 180000"


def test_extracts_vat_line_from_ocr_image(tmp_path: Path) -> None:
    source = tmp_path / "scan.png"
    Image.new("RGB", (200, 100), "white").save(source)
    reference = _reference(source, DeclarationSourceFormat.IMAGE)
    extractor = VatDocumentExtractor(
        DeclarationDocumentTextExtractor(ocr_engine=FixedOcrEngine()),
    )

    result = extractor.extract_image(source, reference)

    fields = {field.name: field for field in result.records[0].fields}
    assert fields["line_code"].normalized_value == "19"
    assert fields["tax_amount"].normalized_value == 180000
    assert fields["tax_amount"].provenance.locator.startswith("image_ocr;")
    assert fields["tax_amount"].confidence == 0.7


def test_uses_ocr_when_pdf_has_no_native_text(tmp_path: Path) -> None:
    source = tmp_path / "scan.pdf"
    Image.new("RGB", (200, 100), "white").save(source, "PDF")
    reference = _reference(source, DeclarationSourceFormat.PDF)
    extractor = VatDocumentExtractor(
        DeclarationDocumentTextExtractor(ocr_engine=FixedOcrEngine()),
    )

    result = extractor.extract_pdf(source, reference)

    fields = {field.name: field for field in result.records[0].fields}
    assert fields["tax_amount"].normalized_value == 180000
    assert fields["tax_amount"].provenance.locator.startswith("pdf_ocr;")
    assert fields["tax_amount"].confidence == 0.7


def test_parses_native_pdf_text_lines_without_ocr() -> None:
    reference = SourceReference(
        file_name="vat.pdf",
        source_format=DeclarationSourceFormat.PDF,
        content_type="application/pdf",
        content_sha256="a" * 64,
    )

    result = VatDocumentExtractor().extract_text(
        "19 Montant total de la TVA brute 180 000",
        reference,
        locator_prefix="pdf_native_text",
    )

    fields = {field.name: field for field in result.records[0].fields}
    assert fields["line_code"].normalized_value == "19"
    assert fields["tax_amount"].normalized_value == 180000
    assert fields["tax_amount"].confidence == 0.9


def test_parses_credit_carry_forward_summary() -> None:
    reference = SourceReference(
        file_name="vat.pdf",
        source_format=DeclarationSourceFormat.PDF,
        content_type="application/pdf",
        content_sha256="a" * 64,
    )

    result = VatDocumentExtractor().extract_text(
        "Montant du crédit de TVA à reporter 250 000",
        reference,
        locator_prefix="pdf_native_text",
    )

    fields = {field.name: field for field in result.records[0].fields}
    assert fields["line_code"].normalized_value == "vat_credit_carry_forward"
    assert fields["tax_amount"].normalized_value == 250000


def _reference(path: Path, source_format: DeclarationSourceFormat) -> SourceReference:
    return SourceReference(
        file_name=path.name,
        source_format=source_format,
        content_type=None,
        content_sha256="a" * 64,
    )
