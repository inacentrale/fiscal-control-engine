from pathlib import Path

from PIL import Image

from app.tax_declaration.document_text_extractor import (
    DeclarationDocumentTextExtractor,
)
from app.tax_declaration.domain import DeclarationSourceFormat, SourceReference
from app.tax_declaration.payroll_tax_text_extractor import (
    PayrollTaxDocumentExtractor,
)

_IUTS_TABLE = (
    "N ordre | Nom du salarie | Salaire brut | Base imposable | "
    "Nombre de charges | IUTS\n"
    "01 | Salarie Test | 350000 | 280000 | 2 | 42237"
)


class FixedOcrEngine:
    def extract_text(self, image: Image.Image) -> str:
        assert image.width > 0
        return _IUTS_TABLE


def test_extracts_explicit_iuts_table_from_pdf_text() -> None:
    declaration = PayrollTaxDocumentExtractor().extract_text(
        _IUTS_TABLE,
        _reference("iuts.pdf", DeclarationSourceFormat.PDF),
        locator_prefix="pdf_native_text",
    )

    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["taxable_base"].normalized_value == 280000
    assert fields["iuts_amount"].normalized_value == 42237
    assert fields["iuts_amount"].confidence == 0.9
    assert fields["iuts_amount"].provenance.locator.startswith("pdf_native_text;")


def test_extracts_iuts_table_from_ocr_image(tmp_path: Path) -> None:
    source = tmp_path / "scan.png"
    Image.new("RGB", (200, 100), "white").save(source)
    extractor = PayrollTaxDocumentExtractor(
        DeclarationDocumentTextExtractor(ocr_engine=FixedOcrEngine()),
    )

    declaration = extractor.extract_image(
        source,
        _reference(source.name, DeclarationSourceFormat.IMAGE),
    )

    field = next(
        field
        for field in declaration.records[0].fields
        if field.name == "iuts_amount"
    )
    assert field.normalized_value == 42237
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
