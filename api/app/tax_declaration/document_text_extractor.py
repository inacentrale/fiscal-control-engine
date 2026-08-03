from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pypdfium2 as pdfium
import pytesseract
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

_PDF_RENDER_SCALE = 200 / 72
_OCR_TIMEOUT_SECONDS = 30
_MAX_PDF_PAGES = 50


class DocumentTextExtractionError(ValueError):
    pass


class OcrEngine(Protocol):
    def extract_text(self, image: Image.Image) -> str: ...


class TesseractOcrEngine:
    def extract_text(self, image: Image.Image) -> str:
        try:
            return str(
                pytesseract.image_to_string(
                    image,
                    lang="fra",
                    config="--psm 6",
                    timeout=_OCR_TIMEOUT_SECONDS,
                ),
            )
        except (OSError, RuntimeError) as exc:
            raise DocumentTextExtractionError("OCR extraction failed") from exc


class DeclarationDocumentTextExtractor:
    def __init__(self, ocr_engine: OcrEngine | None = None) -> None:
        self._ocr_engine = ocr_engine or TesseractOcrEngine()

    def extract_pdf_text(self, source_path: Path) -> tuple[str, str]:
        native_text = _extract_native_pdf_text(source_path)
        if native_text.strip():
            return native_text, "pdf_native_text"
        return self.extract_scanned_pdf_text(source_path), "pdf_ocr"

    def extract_image_text(self, source_path: Path) -> tuple[str, str]:
        try:
            with Image.open(source_path) as image:
                image.load()
                text = self._ocr_engine.extract_text(image.convert("RGB"))
        except (OSError, UnidentifiedImageError) as exc:
            raise DocumentTextExtractionError("invalid declaration image") from exc
        if not text.strip():
            raise DocumentTextExtractionError("OCR returned no text")
        return text, "image_ocr"

    def extract_scanned_pdf_text(self, source_path: Path) -> str:
        try:
            document = pdfium.PdfDocument(str(source_path))
        except Exception as exc:
            raise DocumentTextExtractionError("invalid declaration PDF") from exc
        try:
            if len(document) > _MAX_PDF_PAGES:
                raise DocumentTextExtractionError("declaration PDF has too many pages")
            pages: list[str] = []
            for index in range(len(document)):
                page = document[index]
                bitmap = page.render(scale=_PDF_RENDER_SCALE)
                try:
                    image = bitmap.to_pil().convert("RGB")
                    pages.append(self._ocr_engine.extract_text(image))
                finally:
                    bitmap.close()
                    page.close()
            text = "\n".join(pages)
        finally:
            document.close()
        if not text.strip():
            raise DocumentTextExtractionError("OCR returned no text")
        return text


def _extract_native_pdf_text(source_path: Path) -> str:
    try:
        reader = PdfReader(source_path, strict=True)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise DocumentTextExtractionError("encrypted declaration PDF")
        if len(reader.pages) > _MAX_PDF_PAGES:
            raise DocumentTextExtractionError("declaration PDF has too many pages")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except (OSError, PdfReadError) as exc:
        raise DocumentTextExtractionError("invalid declaration PDF") from exc
