from __future__ import annotations

import math
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from app.tax_declaration.corporate_income_tax_schema import (
    CORPORATE_INCOME_TAX_SCHEMA_VERSION,
)
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
from app.tax_declaration.identifier_detection import (
    infer_identifier_kind,
    normalize_explicit_identifier_kind,
)

_FIELD_ALIASES = {
    "company_identifier": (
        "ifu",
        "numero ifu",
        "n ifu",
        "nif",
        "numero nif",
        "tin",
        "identifiant fiscal",
        "numero fiscal",
        "tax id",
        "taxpayer identifier",
    ),
    "company_identifier_type": (
        "type identifiant societe",
        "company identifier type",
        "type identifiant fiscal",
    ),
    "company_name": (
        "raison sociale",
        "designation de la societe",
        "denomination",
    ),
    "tax_regime": ("regime", "regime d imposition", "regime fiscal"),
    "taxable_profit": (
        "benefice imposable",
        "resultat imposable",
        "benefice net imposable",
    ),
    "annual_turnover_excluding_tax": (
        "chiffre d affaires annuel hors taxes",
        "chiffre d affaires hors taxes",
        "chiffre d affaires ht",
        "ca annuel ht",
        "ca ht",
    ),
    "computed_corporate_tax": (
        "is calcule",
        "impot calcule",
        "montant is",
        "is du",
    ),
    "minimum_tax_declared": (
        "imfpic",
        "minimum forfaitaire",
        "impot minimum",
    ),
    "minimum_tax_treatment": (
        "traitement imfpic",
        "situation imfpic",
        "categorie imfpic",
    ),
    "corporate_tax_due": (
        "is a payer",
        "is net a payer",
        "solde is",
    ),
    "provisional_installments_paid": (
        "acomptes provisionnels verses",
        "acomptes verses",
        "total acomptes provisionnels",
        "acomptes payes",
    ),
}
_AMOUNT_FIELDS = {
    "taxable_profit",
    "annual_turnover_excluding_tax",
    "computed_corporate_tax",
    "minimum_tax_declared",
    "corporate_tax_due",
    "provisional_installments_paid",
}
_SIGNATURE_FIELDS = {"tax_regime", "taxable_profit", "computed_corporate_tax"}
_REGIME_LABELS = {
    "real_normal": ("reel normal", "regime du reel normal", "normal"),
    "real_simplified": (
        "reel simplifie",
        "regime du reel simplifie",
        "simplifie",
    ),
}
_MINIMUM_TAX_TREATMENT_LABELS = {
    "standard": ("standard", "droit commun", "regle generale"),
    "exclusive_floor_only": (
        "activite exclusive station service",
        "activite exclusive recharge telephonique",
        "plancher uniquement",
    ),
    "approved_management_center": (
        "adherent centre de gestion agree",
        "centre de gestion agree",
        "cga",
    ),
    "approved_management_center_exclusive_floor_only": (
        "cga et activite exclusive",
        "centre de gestion agree et plancher uniquement",
    ),
    "new_company_first_year": (
        "societe nouvelle premier exercice",
        "premier exercice",
        "nouvelle societe",
    ),
}


class CorporateIncomeTaxTabularExtractionError(ValueError):
    pass


class CorporateIncomeTaxTabularExtractor:
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
            raise CorporateIncomeTaxTabularExtractionError(
                "IS tabular structure is unresolved",
            )
        records = tuple(
            _extract_record(row, row_index, mapping, source_reference)
            for row_index, (_, row) in enumerate(dataframe.iterrows(), start=2)
            if not row.isna().all()
        )
        if not records:
            raise CorporateIncomeTaxTabularExtractionError(
                "IS declaration has no record",
            )
        return CanonicalTaxDeclaration(
            schema_version=CORPORATE_INCOME_TAX_SCHEMA_VERSION,
            declaration_type=TaxDeclarationType.CORPORATE_INCOME_TAX,
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
        raise CorporateIncomeTaxTabularExtractionError(
            "IS tabular source cannot be read",
        ) from exc
    raise CorporateIncomeTaxTabularExtractionError("unsupported IS tabular format")


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
    fields = [
        _canonical_field(
            name,
            row[column],
            reference,
            f"row:{row_index};column:{column}",
        )
        for name, column in mapping.items()
    ]
    identifier_column = mapping.get("company_identifier")
    if identifier_column is not None and "company_identifier_type" not in mapping:
        identifier_kind = infer_identifier_kind(identifier_column)
        if identifier_kind is not None:
            fields.append(
                CanonicalField(
                    name="company_identifier_type",
                    source_value=identifier_column,
                    normalized_value=identifier_kind,
                    confidence=1.0,
                    status=ResolutionStatus.RESOLVED,
                    provenance=FieldProvenance(
                        reference,
                        f"column:{identifier_column}",
                    ),
                ),
            )
    return CanonicalRecord(
        record_type="corporate_income_tax_line",
        fields=tuple(fields),
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


def _normalize_value(name: str, value: Any) -> str | Decimal | None:
    if _missing(value):
        return None
    if name in _AMOUNT_FIELDS:
        return _decimal(value)
    if name == "tax_regime":
        return _normalize_regime(str(value))
    if name == "minimum_tax_treatment":
        return _normalize_minimum_tax_treatment(str(value))
    text = str(value).strip()
    if name == "company_identifier_type":
        return normalize_explicit_identifier_kind(text)
    return text or None


def _normalize_regime(value: str) -> str | None:
    label = _normalize_label(value)
    for regime, aliases in _REGIME_LABELS.items():
        if label in aliases:
            return regime
    return None


def _normalize_minimum_tax_treatment(value: str) -> str | None:
    label = _normalize_label(value)
    for treatment, aliases in _MINIMUM_TAX_TREATMENT_LABELS.items():
        if label in aliases:
            return treatment
    return None


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
