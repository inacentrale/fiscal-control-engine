from pathlib import Path

from PIL import Image

from app.tax_declaration.document_text_extractor import (
    DeclarationDocumentTextExtractor,
)
from app.tax_declaration.domain import DeclarationSourceFormat, SourceReference
from app.tax_declaration.withholding_text_extractor import (
    WithholdingDocumentExtractor,
)

_RAS_TABLE = (
    "Code | Regime retenue | Categorie taux | Base | Taux | "
    "Montant des retenues\n"
    "01 | resident | registered_standard | 1000000 | 5 | 50000"
)


class FixedOcrEngine:
    def extract_text(self, image: Image.Image) -> str:
        assert image.width > 0
        return _RAS_TABLE


def test_extracts_explicit_withholding_table_from_text() -> None:
    reference = _reference("ras.pdf", DeclarationSourceFormat.PDF)

    declaration = WithholdingDocumentExtractor().extract_text(
        _RAS_TABLE,
        reference,
        locator_prefix="pdf_native_text",
    )

    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["tax_base"].normalized_value == 1000000
    assert fields["withheld_amount"].normalized_value == 50000
    assert fields["withheld_amount"].confidence == 0.9
    assert fields["withheld_amount"].provenance.locator.startswith(
        "pdf_native_text;",
    )


def test_extracts_withholding_table_from_ocr_image(tmp_path: Path) -> None:
    source = tmp_path / "scan.png"
    Image.new("RGB", (200, 100), "white").save(source)
    extractor = WithholdingDocumentExtractor(
        DeclarationDocumentTextExtractor(ocr_engine=FixedOcrEngine()),
    )

    declaration = extractor.extract_image(
        source,
        _reference(source.name, DeclarationSourceFormat.IMAGE),
    )

    field = next(
        field
        for field in declaration.records[0].fields
        if field.name == "withheld_amount"
    )
    assert field.normalized_value == 50000
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
