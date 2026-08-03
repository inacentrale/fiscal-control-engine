from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class TaxDeclarationType(StrEnum):
    VAT = "vat"
    WITHHOLDING_TAX = "withholding_tax"
    PAYROLL_TAX = "payroll_tax"
    CORPORATE_INCOME_TAX = "corporate_income_tax"
    UNRESOLVED = "unresolved"


class DeclarationSourceFormat(StrEnum):
    EXCEL = "excel"
    CSV = "csv"
    XML = "xml"
    PDF = "pdf"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class SourceReference:
    file_name: str
    source_format: DeclarationSourceFormat
    content_type: str | None
    content_sha256: str


@dataclass(frozen=True)
class FieldProvenance:
    source_reference: SourceReference
    locator: str


@dataclass(frozen=True)
class CanonicalField:
    name: str
    source_value: Any
    normalized_value: Any
    confidence: float
    status: ResolutionStatus
    provenance: FieldProvenance

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("canonical field name is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.status is ResolutionStatus.RESOLVED and self.normalized_value is None:
            raise ValueError("a resolved field requires a normalized value")


@dataclass(frozen=True)
class CanonicalTaxDeclaration:
    schema_version: str
    declaration_type: TaxDeclarationType
    source_reference: SourceReference
    fields: tuple[CanonicalField, ...]
    records: tuple["CanonicalRecord", ...] = ()

    def __post_init__(self) -> None:
        if not self.schema_version.strip():
            raise ValueError("schema version is required")


@dataclass(frozen=True)
class CanonicalRecord:
    record_type: str
    fields: tuple[CanonicalField, ...]

    def __post_init__(self) -> None:
        if not self.record_type.strip():
            raise ValueError("record type is required")


@dataclass(frozen=True)
class TaxpayerIdentifier:
    kind: str
    value: str
    confidence: float

    def __post_init__(self) -> None:
        if not self.kind.strip() or not self.value.strip():
            raise ValueError("identifier kind and value are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
