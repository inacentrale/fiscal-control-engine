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
from app.tax_declaration.payroll_tax_schema import PAYROLL_TAX_SCHEMA_VERSION

_FIELD_ALIASES = {
    "line_number": ("n", "no", "numero", "n ordre", "numero d ordre"),
    "employee_identifier": (
        "matricule",
        "matricule salarie",
        "identifiant salarie",
    ),
    "employee_name": (
        "noms et prenoms des salaries",
        "nom et prenoms du salarie",
        "nom du salarie",
        "salarie",
    ),
    "gross_salary": ("salaires bruts", "salaire brut", "remuneration brute"),
    "taxable_base": ("bases imposables", "base imposable", "revenu imposable"),
    "dependent_count": (
        "nombre de charge",
        "nombre de charges",
        "charges de famille",
    ),
    "iuts_amount": (
        "iuts du",
        "montant iuts",
        "iuts retenu",
        "iuts",
    ),
}
_AMOUNT_FIELDS = {"gross_salary", "taxable_base", "iuts_amount"}
_SIGNATURE_FIELDS = {"gross_salary", "taxable_base", "iuts_amount"}


class PayrollTaxTabularExtractionError(ValueError):
    pass


class PayrollTaxTabularExtractor:
    def is_candidate(
        self,
        source_path: Path,
        source_reference: SourceReference,
        *,
        sheet_name: str | None = None,
    ) -> bool:
        dataframe = _read_tabular_source(source_path, source_reference, sheet_name)
        mapping = _map_columns(tuple(dataframe.columns))
        return _SIGNATURE_FIELDS.issubset(mapping)

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
        if not _SIGNATURE_FIELDS.issubset(mapping):
            raise PayrollTaxTabularExtractionError(
                "IUTS tabular structure is unresolved",
            )
        records = tuple(
            _extract_record(row, row_index, mapping, source_reference)
            for row_index, (_, row) in enumerate(dataframe.iterrows(), start=2)
            if not row.isna().all()
        )
        if not records:
            raise PayrollTaxTabularExtractionError("IUTS declaration has no record")
        return CanonicalTaxDeclaration(
            schema_version=PAYROLL_TAX_SCHEMA_VERSION,
            declaration_type=TaxDeclarationType.PAYROLL_TAX,
            source_reference=source_reference,
            fields=(),
            records=records,
        )


def _read_tabular_source(
    path: Path,
    source_reference: SourceReference,
    sheet_name: str | None,
) -> pd.DataFrame:
    try:
        if source_reference.source_format is DeclarationSourceFormat.CSV:
            return pd.read_csv(path, sep=None, engine="python", dtype=object)
        if source_reference.source_format is DeclarationSourceFormat.EXCEL:
            return pd.read_excel(
                path,
                sheet_name=sheet_name or 0,
                engine="openpyxl",
                dtype=object,
            )
    except (OSError, UnicodeError, ValueError) as exc:
        raise PayrollTaxTabularExtractionError(
            "IUTS tabular source cannot be read",
        ) from exc
    raise PayrollTaxTabularExtractionError("unsupported IUTS tabular format")


def _map_columns(columns: tuple[Any, ...]) -> dict[str, str]:
    normalized = {str(column): _normalize_label(str(column)) for column in columns}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for field, aliases in _FIELD_ALIASES.items():
        matches = [
            source
            for source, label in normalized.items()
            if label in aliases and source not in used
        ]
        if len(matches) == 1:
            mapping[field] = matches[0]
            used.add(matches[0])
    return mapping


def _extract_record(
    row: pd.Series[Any],
    row_index: int,
    mapping: dict[str, str],
    reference: SourceReference,
) -> CanonicalRecord:
    return CanonicalRecord(
        record_type="payroll_tax_line",
        fields=tuple(
            _canonical_field(
                name,
                row[column],
                reference,
                f"row:{row_index};column:{column}",
            )
            for name, column in mapping.items()
        ),
    )


def _canonical_field(
    name: str,
    source_value: Any,
    reference: SourceReference,
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
        source_value=_serializable_value(source_value),
        normalized_value=normalized_value,
        confidence=1.0 if status is ResolutionStatus.RESOLVED else 0.0,
        status=status,
        provenance=FieldProvenance(reference, locator),
    )


def _normalize_value(name: str, value: Any) -> str | Decimal | int | None:
    if _missing(value):
        return None
    if name in _AMOUNT_FIELDS:
        return _decimal(value)
    if name == "dependent_count":
        decimal_value = _decimal(value)
        if decimal_value is None or decimal_value != decimal_value.to_integral_value():
            return None
        return int(decimal_value)
    text = str(value).strip()
    if name == "line_number" and text.endswith(".0"):
        text = text[:-2]
    return text or None


def _decimal(value: Any) -> Decimal | None:
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


def _serializable_value(value: Any) -> Any:
    if _missing(value):
        return None
    return value.item() if hasattr(value, "item") else value


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
