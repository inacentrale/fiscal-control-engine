from __future__ import annotations

import math
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from app.tax_declaration.domain import (
    CanonicalField,
    CanonicalRecord,
    CanonicalTaxDeclaration,
    DeclarationSourceFormat,
    FieldProvenance,
    ResolutionStatus,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.vat_schema import VAT_SCHEMA_VERSION

_FIELD_ALIASES = {
    "line_code": ("n", "no", "numero", "code", "ligne"),
    "operation_nature": (
        "nature",
        "nature des operations",
        "libelle",
        "description",
    ),
    "tax_base": ("base", "base taxable", "base imposable"),
    "tax_rate": ("taux", "taux tva", "pourcentage"),
    "tax_amount": ("montant", "montant tva", "taxe", "tva"),
}
_MINIMUM_FIELDS = frozenset({"operation_nature", "tax_amount"})


class VatTabularExtractionError(ValueError):
    pass


class VatTabularExtractor:
    def extract(
        self,
        source_path: Path,
        source_reference: SourceReference,
        *,
        sheet_name: str | None = None,
    ) -> CanonicalTaxDeclaration:
        dataframe = _read_tabular_source(source_path, source_reference, sheet_name)
        return self.extract_frame(dataframe, source_reference)

    def extract_frame(
        self,
        dataframe: pd.DataFrame,
        source_reference: SourceReference,
    ) -> CanonicalTaxDeclaration:
        mapping = _map_columns(tuple(dataframe.columns))
        if not _MINIMUM_FIELDS.issubset(mapping):
            missing = sorted(_MINIMUM_FIELDS.difference(mapping))
            raise VatTabularExtractionError(
                f"VAT tabular structure is unresolved: {', '.join(missing)}",
            )

        records = tuple(
            _extract_record(row, row_index, mapping, source_reference)
            for row_index, (_, row) in enumerate(dataframe.iterrows(), start=2)
            if not row.isna().all()
        )
        return CanonicalTaxDeclaration(
            schema_version=VAT_SCHEMA_VERSION,
            declaration_type=TaxDeclarationType.VAT,
            source_reference=source_reference,
            fields=(),
            records=records,
        )


def _read_tabular_source(
    path: Path,
    source_reference: SourceReference,
    sheet_name: str | None,
) -> pd.DataFrame:
    source_format = source_reference.source_format
    try:
        if source_format is DeclarationSourceFormat.CSV:
            return pd.read_csv(path, sep=None, engine="python")
        if source_format is DeclarationSourceFormat.EXCEL:
            return pd.read_excel(path, sheet_name=sheet_name or 0, engine="openpyxl")
    except (OSError, UnicodeError, ValueError) as exc:
        raise VatTabularExtractionError("VAT tabular source cannot be read") from exc
    raise VatTabularExtractionError(
        f"unsupported VAT tabular format: {source_format.value}",
    )


def _map_columns(columns: tuple[Any, ...]) -> dict[str, str]:
    normalized_sources = {
        str(column): _normalize_label(str(column)) for column in columns
    }
    mapping: dict[str, str] = {}
    used_sources: set[str] = set()
    for canonical_field, aliases in _FIELD_ALIASES.items():
        matches = [
            source
            for source, normalized in normalized_sources.items()
            if normalized in aliases and source not in used_sources
        ]
        if len(matches) == 1:
            mapping[canonical_field] = matches[0]
            used_sources.add(matches[0])
    return mapping


def _extract_record(
    row: pd.Series[Any],
    row_index: int,
    mapping: dict[str, str],
    source_reference: SourceReference,
) -> CanonicalRecord:
    fields = tuple(
        _canonical_field(
            canonical_name,
            row[source_column],
            source_reference,
            locator=f"row:{row_index};column:{source_column}",
        )
        for canonical_name, source_column in mapping.items()
    )
    return CanonicalRecord(record_type="vat_line", fields=fields)


def _canonical_field(
    name: str,
    source_value: Any,
    source_reference: SourceReference,
    locator: str,
) -> CanonicalField:
    normalized_value = _normalize_value(name, source_value)
    status = (
        ResolutionStatus.RESOLVED
        if normalized_value is not None
        else ResolutionStatus.UNRESOLVED
    )
    return CanonicalField(
        name=name,
        source_value=_serializable_source_value(source_value),
        normalized_value=normalized_value,
        confidence=1.0 if status is ResolutionStatus.RESOLVED else 0.0,
        status=status,
        provenance=FieldProvenance(
            source_reference=source_reference,
            locator=locator,
        ),
    )


def _normalize_value(name: str, value: Any) -> str | Decimal | None:
    if _is_missing(value):
        return None
    if name in {"tax_base", "tax_rate", "tax_amount"}:
        return _to_decimal(value)
    text = str(value).strip()
    if name == "line_code" and text.endswith(".0"):
        text = text[:-2]
    return text or None


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return Decimal(str(value))
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    text = text.removesuffix("%")
    if not text:
        return None
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


def _serializable_source_value(value: Any) -> Any:
    if _is_missing(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _is_missing(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except ValueError:
        return False


def _normalize_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()
