from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pandas as pd

from app.tax_declaration.document_text_extractor import (
    DeclarationDocumentTextExtractor,
)
from app.tax_declaration.domain import (
    DeclarationSourceFormat,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.identifier_detection import (
    infer_identifier_kind,
    normalize_explicit_identifier_kind,
)

_FORBIDDEN_XML_MARKERS = (b"<!DOCTYPE", b"<!ENTITY")

_INVOICE_ALIASES = {
    "invoice_id": ("numero facture", "n facture", "invoice id", "facture"),
    "partner_identifier": (
        "identifiant partenaire",
        "partner identifier",
        "ifu",
        "numero ifu",
        "nif",
        "tin",
        "identifiant fiscal",
        "numero fiscal",
        "tax id",
        "taxpayer identifier",
    ),
    "partner_identifier_type": (
        "type identifiant partenaire",
        "partner identifier type",
        "type identifiant",
    ),
    "partner_name": (
        "nom partenaire",
        "raison sociale",
        "beneficiaire",
        "prestataire",
        "partner name",
    ),
    "net_amount": ("montant hors taxe", "montant ht", "base", "net amount"),
    "vat_amount": ("montant tva", "tva", "vat amount"),
    "gross_amount": ("montant ttc", "total ttc", "gross amount"),
    "currency": ("devise", "currency"),
    "declaration_line": (
        "ligne declaration",
        "declaration line",
        "ligne tva",
        "ligne ras",
        "numero ligne",
        "selecteur declaration",
        "declaration selector",
    ),
    "declaration_amount": (
        "montant fiscal",
        "declaration amount",
        "montant declare justifie",
        "montant des retenues",
        "montant de la retenue",
        "montant iuts",
        "iuts du",
        "is a payer",
        "impot sur les societes a payer",
    ),
    "payment_expected_amount": (
        "montant paiement attendu",
        "expected payment amount",
        "montant a rapprocher au paiement",
        "salaire brut",
        "montant verse",
    ),
}
_PAYMENT_ALIASES = {
    "payment_id": ("numero paiement", "payment id", "paiement"),
    "invoice_id": _INVOICE_ALIASES["invoice_id"],
    "amount": ("montant paiement", "montant", "payment amount", "amount"),
    "currency": _INVOICE_ALIASES["currency"],
}


@dataclass(frozen=True)
class InvoiceEvidence:
    invoice_id: str | None
    partner_identifier: str | None
    partner_identifier_type: str | None
    net_amount: Decimal | None
    vat_amount: Decimal | None
    gross_amount: Decimal | None
    currency: str | None
    declaration_line: str | None
    source_reference: SourceReference
    locator: str
    declaration_amount: Decimal | None = None
    payment_expected_amount: Decimal | None = None
    partner_name: str | None = None


@dataclass(frozen=True)
class PaymentEvidence:
    payment_id: str | None
    invoice_id: str | None
    amount: Decimal | None
    currency: str | None
    source_reference: SourceReference
    locator: str


class SupportingEvidenceExtractionError(ValueError):
    pass


class SupportingEvidenceExtractor:
    def __init__(
        self,
        text_extractor: DeclarationDocumentTextExtractor | None = None,
    ) -> None:
        self._text_extractor = text_extractor or DeclarationDocumentTextExtractor()

    def extract_invoices(
        self,
        source_path: Path,
        source_reference: SourceReference,
        *,
        sheet_name: str | None = None,
        declaration_type: TaxDeclarationType = TaxDeclarationType.VAT,
    ) -> tuple[InvoiceEvidence, ...]:
        frame, locator_prefix = _read_frame(
            source_path,
            source_reference,
            sheet_name,
            self._text_extractor,
        )
        mapping = _map_columns(tuple(frame.columns), _INVOICE_ALIASES)
        required = {"invoice_id", "currency", "declaration_line"}
        if declaration_type is TaxDeclarationType.VAT:
            required.update({"net_amount", "vat_amount", "gross_amount"})
        else:
            required.add("declaration_amount")
        _require_mapping(mapping, required, "invoice")
        return tuple(
            _invoice(row, index, mapping, source_reference, locator_prefix)
            for index, (_, row) in enumerate(frame.iterrows(), start=2)
            if not row.isna().all()
        )

    def extract_payments(
        self,
        source_path: Path,
        source_reference: SourceReference,
        *,
        sheet_name: str | None = None,
    ) -> tuple[PaymentEvidence, ...]:
        frame, locator_prefix = _read_frame(
            source_path,
            source_reference,
            sheet_name,
            self._text_extractor,
        )
        mapping = _map_columns(tuple(frame.columns), _PAYMENT_ALIASES)
        _require_mapping(
            mapping,
            {"payment_id", "invoice_id", "amount", "currency"},
            "payment",
        )
        return tuple(
            _payment(row, index, mapping, source_reference, locator_prefix)
            for index, (_, row) in enumerate(frame.iterrows(), start=2)
            if not row.isna().all()
        )


def _read_frame(
    path: Path,
    reference: SourceReference,
    sheet_name: str | None,
    text_extractor: DeclarationDocumentTextExtractor,
) -> tuple[pd.DataFrame, str]:
    try:
        if reference.source_format is DeclarationSourceFormat.CSV:
            return pd.read_csv(path, sep=None, engine="python", dtype=object), "csv"
        if reference.source_format is DeclarationSourceFormat.EXCEL:
            return (
                pd.read_excel(
                    path,
                    sheet_name=sheet_name or 0,
                    engine="openpyxl",
                    dtype=object,
                ),
                f"excel:{sheet_name or 0}",
            )
        if reference.source_format is DeclarationSourceFormat.XML:
            return _read_xml_frame(path), "xml"
        if reference.source_format is DeclarationSourceFormat.PDF:
            text, method = text_extractor.extract_pdf_text(path)
            return _read_text_frame(text), method
        if reference.source_format is DeclarationSourceFormat.IMAGE:
            text, method = text_extractor.extract_image_text(path)
            return _read_text_frame(text), method
    except SupportingEvidenceExtractionError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise SupportingEvidenceExtractionError("evidence cannot be read") from exc
    raise SupportingEvidenceExtractionError("unsupported evidence format")


def _read_xml_frame(path: Path) -> pd.DataFrame:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise SupportingEvidenceExtractionError("evidence cannot be read") from exc
    upper_content = content.upper()
    if any(marker in upper_content for marker in _FORBIDDEN_XML_MARKERS):
        raise SupportingEvidenceExtractionError("unsafe evidence XML")
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise SupportingEvidenceExtractionError("invalid evidence XML") from exc
    rows: list[dict[str, str | None]] = []
    for element in root.iter():
        children = list(element)
        if not children or any(list(child) for child in children):
            continue
        row = {_local_name(child.tag): _element_text(child) for child in children}
        if len(row) >= 2:
            rows.append(row)
    if not rows:
        raise SupportingEvidenceExtractionError("evidence XML structure is unresolved")
    return pd.DataFrame(rows)


def _read_text_frame(text: str) -> pd.DataFrame:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        delimiter = next(
            (candidate for candidate in (";", "|", "\t") if candidate in line),
            None,
        )
        if delimiter is None:
            continue
        header = [_normalize_label(value) for value in line.split(delimiter)]
        known_aliases = {
            alias
            for aliases in (*_INVOICE_ALIASES.values(), *_PAYMENT_ALIASES.values())
            for alias in aliases
        }
        if sum(value in known_aliases for value in header) < 2:
            continue
        candidate_text = "\n".join(lines[index:])
        try:
            frame = pd.read_csv(StringIO(candidate_text), sep=delimiter)
        except (UnicodeError, ValueError) as exc:
            raise SupportingEvidenceExtractionError(
                "document evidence table cannot be read",
            ) from exc
        if not frame.empty:
            return frame
    raise SupportingEvidenceExtractionError("document evidence structure is unresolved")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _element_text(element: ElementTree.Element) -> str | None:
    value = element.text.strip() if element.text else ""
    return value or None


def _map_columns(
    columns: tuple[Any, ...],
    aliases: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    normalized = {str(column): _normalize_label(str(column)) for column in columns}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for field, field_aliases in aliases.items():
        matches = [
            source
            for source, label in normalized.items()
            if label in field_aliases and source not in used
        ]
        if len(matches) == 1:
            mapping[field] = matches[0]
            used.add(matches[0])
    return mapping


def _require_mapping(
    mapping: dict[str, str],
    required: set[str],
    evidence_type: str,
) -> None:
    missing = sorted(required.difference(mapping))
    if missing:
        raise SupportingEvidenceExtractionError(
            f"{evidence_type} evidence structure is unresolved: {', '.join(missing)}",
        )


def _invoice(
    row: pd.Series[Any],
    index: int,
    mapping: dict[str, str],
    reference: SourceReference,
    locator_prefix: str,
) -> InvoiceEvidence:
    explicit_kind = _text(row, mapping.get("partner_identifier_type"))
    identifier_column = mapping.get("partner_identifier")
    return InvoiceEvidence(
        invoice_id=_text(row, mapping.get("invoice_id")),
        partner_identifier=_text(row, mapping.get("partner_identifier")),
        partner_identifier_type=(
            normalize_explicit_identifier_kind(explicit_kind)
            if explicit_kind is not None
            else infer_identifier_kind(identifier_column or "")
        ),
        net_amount=_amount(row, mapping.get("net_amount")),
        vat_amount=_amount(row, mapping.get("vat_amount")),
        gross_amount=_amount(row, mapping.get("gross_amount")),
        currency=_upper_text(row, mapping.get("currency")),
        declaration_line=_text(row, mapping.get("declaration_line")),
        source_reference=reference,
        locator=f"{locator_prefix};row:{index}",
        declaration_amount=_declaration_amount(row, mapping),
        payment_expected_amount=_amount(
            row,
            mapping.get("payment_expected_amount"),
        ),
        partner_name=_text(row, mapping.get("partner_name")),
    )


def _payment(
    row: pd.Series[Any],
    index: int,
    mapping: dict[str, str],
    reference: SourceReference,
    locator_prefix: str,
) -> PaymentEvidence:
    return PaymentEvidence(
        payment_id=_text(row, mapping.get("payment_id")),
        invoice_id=_text(row, mapping.get("invoice_id")),
        amount=_amount(row, mapping.get("amount")),
        currency=_upper_text(row, mapping.get("currency")),
        source_reference=reference,
        locator=f"{locator_prefix};row:{index}",
    )


def _declaration_amount(
    row: pd.Series[Any],
    mapping: dict[str, str],
) -> Decimal | None:
    amount = _amount(row, mapping.get("declaration_amount"))
    return amount if amount is not None else _amount(row, mapping.get("vat_amount"))


def _text(row: pd.Series[Any], column: str | None) -> str | None:
    if column is None or _missing(row[column]):
        return None
    value = str(row[column]).strip()
    return value.removesuffix(".0") if value.endswith(".0") else value or None


def _upper_text(row: pd.Series[Any], column: str | None) -> str | None:
    value = _text(row, column)
    return value.upper() if value else None


def _amount(row: pd.Series[Any], column: str | None) -> Decimal | None:
    if column is None or _missing(row[column]):
        return None
    value = row[column]
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return Decimal(str(value))
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if "," in text and "." in text:
        decimal_separator = "," if text.rfind(",") > text.rfind(".") else "."
        thousands_separator = "." if decimal_separator == "," else ","
        text = text.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _missing(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except ValueError:
        return False


def _normalize_label(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()
