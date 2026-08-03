from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.tax_declaration.domain import DeclarationSourceFormat
from app.tax_declaration.format_detector import (
    DeclarationFormatDetector,
    DeclarationSourceReadError,
)


@pytest.mark.parametrize(
    ("file_name", "content", "expected_format"),
    [
        ("unknown.bin", b"%PDF-1.7\n", DeclarationSourceFormat.PDF),
        ("scan.bin", b"\x89PNG\r\n\x1a\nrest", DeclarationSourceFormat.IMAGE),
        ("data.bin", b"<?xml version='1.0'?><return />", DeclarationSourceFormat.XML),
        ("data.bin", b"ifu;amount\n123;1000\n", DeclarationSourceFormat.CSV),
    ],
)
def test_detects_format_from_content_not_extension(
    tmp_path: Path,
    file_name: str,
    content: bytes,
    expected_format: DeclarationSourceFormat,
) -> None:
    source = tmp_path / file_name
    source.write_bytes(content)

    result = DeclarationFormatDetector().detect(source)

    assert result.source_reference.source_format is expected_format
    assert result.confidence > 0.0
    assert len(result.source_reference.content_sha256) == 64


def test_detects_xlsx_package_without_xlsx_extension(tmp_path: Path) -> None:
    source = tmp_path / "declaration.upload"
    with ZipFile(source, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", "<workbook />")

    result = DeclarationFormatDetector().detect(source)

    assert result.source_reference.source_format is DeclarationSourceFormat.EXCEL
    assert result.evidence == "xlsx_package"


def test_leaves_unrecognized_input_unresolved(tmp_path: Path) -> None:
    source = tmp_path / "declaration.dat"
    source.write_bytes(b"not a structured declaration")

    result = DeclarationFormatDetector().detect(source)

    assert result.source_reference.source_format is DeclarationSourceFormat.UNKNOWN
    assert result.confidence == 0.0


def test_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(DeclarationSourceReadError, match="does not exist"):
        DeclarationFormatDetector().detect(tmp_path / "missing.pdf")
