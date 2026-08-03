from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from app.tax_declaration.document_text_extractor import (
    DeclarationDocumentTextExtractor,
)
from app.tax_declaration.domain import (
    CanonicalField,
    CanonicalRecord,
    CanonicalTaxDeclaration,
    FieldProvenance,
    SourceReference,
)
from app.tax_declaration.payroll_tax_tabular_extractor import (
    PayrollTaxTabularExtractionError,
    PayrollTaxTabularExtractor,
)

_DELIMITERS = re.compile(r"\s*[;|\t]\s*")


class PayrollTaxDocumentExtractor:
    def __init__(
        self,
        text_extractor: DeclarationDocumentTextExtractor | None = None,
    ) -> None:
        self._text_extractor = text_extractor or DeclarationDocumentTextExtractor()

    def extract_pdf(
        self,
        source_path: Path,
        source_reference: SourceReference,
    ) -> CanonicalTaxDeclaration:
        text, method = self._text_extractor.extract_pdf_text(source_path)
        try:
            return self.extract_text(
                text,
                source_reference,
                locator_prefix=method,
                confidence_cap=0.9 if method == "pdf_native_text" else 0.7,
            )
        except PayrollTaxTabularExtractionError:
            if method != "pdf_native_text":
                raise
            ocr_text = self._text_extractor.extract_scanned_pdf_text(source_path)
            return self.extract_text(
                ocr_text,
                source_reference,
                locator_prefix="pdf_ocr",
                confidence_cap=0.7,
            )

    def extract_image(
        self,
        source_path: Path,
        source_reference: SourceReference,
    ) -> CanonicalTaxDeclaration:
        text, method = self._text_extractor.extract_image_text(source_path)
        return self.extract_text(
            text,
            source_reference,
            locator_prefix=method,
            confidence_cap=0.7,
        )

    def extract_text(
        self,
        text: str,
        source_reference: SourceReference,
        *,
        locator_prefix: str,
        confidence_cap: float = 0.9,
    ) -> CanonicalTaxDeclaration:
        declaration = PayrollTaxTabularExtractor().extract_frame(
            _explicit_table(text),
            source_reference,
        )
        return _replace_metadata(declaration, locator_prefix, confidence_cap)


def _explicit_table(text: str) -> pd.DataFrame:
    rows = [
        _DELIMITERS.split(line.strip())
        for line in text.splitlines()
        if any(delimiter in line for delimiter in (";", "|", "\t"))
    ]
    for index, header in enumerate(rows):
        normalized_header = " ".join(header).casefold()
        if (
            len(header) < 2
            or any(not value for value in header)
            or "iuts" not in normalized_header
        ):
            continue
        body = [row for row in rows[index + 1 :] if len(row) == len(header)]
        if body:
            return pd.DataFrame(body, columns=header)
    raise PayrollTaxTabularExtractionError("IUTS document table is unresolved")


def _replace_metadata(
    declaration: CanonicalTaxDeclaration,
    locator_prefix: str,
    confidence_cap: float,
) -> CanonicalTaxDeclaration:
    return CanonicalTaxDeclaration(
        schema_version=declaration.schema_version,
        declaration_type=declaration.declaration_type,
        source_reference=declaration.source_reference,
        fields=declaration.fields,
        records=tuple(
            CanonicalRecord(
                record_type=record.record_type,
                fields=tuple(
                    CanonicalField(
                        name=field.name,
                        source_value=field.source_value,
                        normalized_value=field.normalized_value,
                        confidence=min(field.confidence, confidence_cap),
                        status=field.status,
                        provenance=FieldProvenance(
                            source_reference=field.provenance.source_reference,
                            locator=f"{locator_prefix};{field.provenance.locator}",
                        ),
                    )
                    for field in record.fields
                ),
            )
            for record in declaration.records
        ),
    )
