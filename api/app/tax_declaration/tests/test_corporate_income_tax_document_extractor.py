from decimal import Decimal
from pathlib import Path

from PIL import Image

from app.tax_declaration.corporate_income_tax_text_extractor import (
    CorporateIncomeTaxDocumentExtractor,
)
from app.tax_declaration.document_text_extractor import (
    DeclarationDocumentTextExtractor,
)
from app.tax_declaration.domain import DeclarationSourceFormat, SourceReference

_IS_TABLE = (
    "IFU | Raison sociale | Regime | Benefice imposable | "
    "IS calcule | IMFPIC | IS a payer\n"
    "0123456789 | Societe Test | Reel Normal | 10000000 | "
    "2750000 | 1000000 | 2750000"
)


class FixedOcrEngine:
    def extract_text(self, image: Image.Image) -> str:
        assert image.width > 0
        return _IS_TABLE


def test_extracts_explicit_is_table_from_pdf_text() -> None:
    declaration = CorporateIncomeTaxDocumentExtractor().extract_text(
        _IS_TABLE,
        _reference("is.pdf", DeclarationSourceFormat.PDF),
        locator_prefix="pdf_native_text",
    )

    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["taxable_profit"].normalized_value == Decimal("10000000")
    assert fields["computed_corporate_tax"].normalized_value == Decimal("2750000")
    assert fields["computed_corporate_tax"].confidence == 0.9
    assert fields["computed_corporate_tax"].provenance.locator.startswith(
        "pdf_native_text;",
    )


def test_extracts_is_table_from_ocr_image(tmp_path: Path) -> None:
    source = tmp_path / "scan.png"
    Image.new("RGB", (200, 100), "white").save(source)
    extractor = CorporateIncomeTaxDocumentExtractor(
        DeclarationDocumentTextExtractor(ocr_engine=FixedOcrEngine()),
    )

    declaration = extractor.extract_image(
        source,
        _reference(source.name, DeclarationSourceFormat.IMAGE),
    )

    field = next(
        field
        for field in declaration.records[0].fields
        if field.name == "computed_corporate_tax"
    )
    assert field.normalized_value == Decimal("2750000")
    assert field.confidence == 0.7
    assert field.provenance.locator.startswith("image_ocr;")


def _reference(
    file_name: str,
    source_format: DeclarationSourceFormat,
) -> SourceReference:
    return SourceReference(
        file_name=file_name,
        source_format=source_format,
        content_type=None,
        content_sha256="a" * 64,
    )
