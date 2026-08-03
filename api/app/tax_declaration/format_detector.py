from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from app.tax_declaration.domain import DeclarationSourceFormat, SourceReference

_PDF_SIGNATURE = b"%PDF-"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_TIFF_SIGNATURES = (b"II*\x00", b"MM\x00*")
_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_SIGNATURE = b"PK\x03\x04"
_READ_LIMIT_BYTES = 64 * 1024


class DeclarationSourceReadError(ValueError):
    pass


@dataclass(frozen=True)
class DeclarationFormatDetection:
    source_reference: SourceReference
    confidence: float
    evidence: str


class DeclarationFormatDetector:
    def detect(
        self,
        source_path: Path,
        *,
        content_type: str | None = None,
        file_name: str | None = None,
    ) -> DeclarationFormatDetection:
        path = source_path.resolve()
        if not path.is_file():
            raise DeclarationSourceReadError("declaration source does not exist")

        try:
            header = _read_header(path)
            content_sha256 = _sha256(path)
        except OSError as exc:
            raise DeclarationSourceReadError(
                "declaration source cannot be read",
            ) from exc

        source_format, confidence, evidence = _detect_content(path, header)
        return DeclarationFormatDetection(
            source_reference=SourceReference(
                file_name=Path(file_name).name if file_name else path.name,
                source_format=source_format,
                content_type=content_type,
                content_sha256=content_sha256,
            ),
            confidence=confidence,
            evidence=evidence,
        )


def _read_header(path: Path) -> bytes:
    with path.open("rb") as source:
        return source.read(_READ_LIMIT_BYTES)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(_READ_LIMIT_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _detect_content(
    path: Path,
    header: bytes,
) -> tuple[DeclarationSourceFormat, float, str]:
    if header.startswith(_PDF_SIGNATURE):
        return DeclarationSourceFormat.PDF, 1.0, "pdf_signature"
    if header.startswith((_PNG_SIGNATURE, _JPEG_SIGNATURE, *_TIFF_SIGNATURES)):
        return DeclarationSourceFormat.IMAGE, 1.0, "image_signature"
    if header.startswith(_OLE_SIGNATURE):
        return DeclarationSourceFormat.EXCEL, 0.95, "ole_signature"
    if header.startswith(_ZIP_SIGNATURE) and _is_xlsx(path):
        return DeclarationSourceFormat.EXCEL, 1.0, "xlsx_package"

    text = _decode_text(header)
    if text is None:
        return DeclarationSourceFormat.UNKNOWN, 0.0, "unrecognized_binary"
    if text.lstrip("\ufeff\t\r\n ").startswith("<"):
        return DeclarationSourceFormat.XML, 0.9, "xml_markup"
    if _looks_like_csv(text):
        return DeclarationSourceFormat.CSV, 0.85, "delimited_text"
    return DeclarationSourceFormat.UNKNOWN, 0.0, "unrecognized_text"


def _is_xlsx(path: Path) -> bool:
    try:
        with ZipFile(path) as archive:
            return "xl/workbook.xml" in archive.namelist()
    except (BadZipFile, OSError):
        return False


def _decode_text(content: bytes) -> str | None:
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def _looks_like_csv(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    try:
        dialect = csv.Sniffer().sniff("\n".join(lines[:20]), delimiters=",;\t|")
    except csv.Error:
        return False
    widths = [len(next(csv.reader([line], dialect=dialect))) for line in lines[:20]]
    return widths[0] > 1 and len(set(widths)) == 1
