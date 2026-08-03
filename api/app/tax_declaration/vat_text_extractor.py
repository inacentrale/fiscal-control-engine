from __future__ import annotations

import re
import unicodedata
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
from app.tax_declaration.vat_tabular_extractor import (
    VatTabularExtractionError,
    VatTabularExtractor,
)

_DELIMITERS = re.compile(r"\s*[;|\t]\s*")
_CODE_PREFIX = re.compile(r"^\s*(?P<code>\d{1,2})\s+(?P<body>.+?)\s*$")
_TRAILING_AMOUNT = re.compile(
    r"(?P<amount>[-+]?\d(?:[\d .\u00a0]*\d)?(?:,\d+)?)\s*$",
)
_SUMMARY_LINE_CODES = {
    "montant de la tva nette a payer": "net_vat_payable",
    "montant du credit de tva a reporter": "vat_credit_carry_forward",
    "montant de la tva payable par avis de credit ou par l etat": (
        "vat_payable_by_credit_or_state"
    ),
}


class VatDocumentExtractor:
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
        except VatTabularExtractionError:
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
        rows = [row for line in text.splitlines() if (row := _parse_line(line))]
        if not rows:
            raise VatTabularExtractionError("VAT document structure is unresolved")
        declaration = VatTabularExtractor().extract_frame(
            pd.DataFrame(rows),
            source_reference,
        )
        return _replace_metadata(declaration, locator_prefix, confidence_cap)


def _parse_line(line: str) -> dict[str, str] | None:
    delimited = _DELIMITERS.split(line.strip())
    if len(delimited) >= 3 and delimited[0].isdigit():
        row = {
            "Code": delimited[0],
            "Nature": delimited[1],
            "Montant": delimited[-1],
        }
        if len(delimited) >= 4:
            row["Base"] = delimited[2]
        if len(delimited) >= 5:
            row["Taux"] = delimited[3]
        return row

    code_match = _CODE_PREFIX.match(line)
    if code_match is None:
        return _parse_summary_line(line)
    body = code_match.group("body")
    amount_match = _TRAILING_AMOUNT.search(body)
    if amount_match is None:
        return None
    nature = body[: amount_match.start()].strip(" :-")
    if not nature:
        return None
    return {
        "Code": code_match.group("code"),
        "Nature": nature,
        "Montant": amount_match.group("amount"),
    }


def _parse_summary_line(line: str) -> dict[str, str] | None:
    normalized_line = _normalize_text(line)
    for label, line_code in _SUMMARY_LINE_CODES.items():
        if not normalized_line.startswith(label):
            continue
        amount_match = _TRAILING_AMOUNT.search(line)
        if amount_match is None:
            return None
        return {
            "Code": line_code,
            "Nature": label,
            "Montant": amount_match.group("amount"),
        }
    return None


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def _replace_metadata(
    declaration: CanonicalTaxDeclaration,
    locator_prefix: str,
    confidence_cap: float,
) -> CanonicalTaxDeclaration:
    records = tuple(
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
    )
    return CanonicalTaxDeclaration(
        schema_version=declaration.schema_version,
        declaration_type=declaration.declaration_type,
        source_reference=declaration.source_reference,
        fields=declaration.fields,
        records=records,
    )
