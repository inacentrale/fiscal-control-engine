import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path


class LedgerAmountSide(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


@dataclass(frozen=True)
class VatLedgerAccountMapping:
    mapping_id: str
    version: str
    account: str
    declaration_line: str
    amount_side: LedgerAmountSide
    currency: str
    tolerance: Decimal
    valid_from: date | None
    valid_to: date | None
    source_reference: str


class VatLedgerMappingError(ValueError):
    pass


_REQUIRED_COLUMNS = {
    "mapping_id",
    "version",
    "account",
    "declaration_line",
    "amount_side",
    "currency",
    "tolerance",
    "valid_from",
    "valid_to",
    "source_reference",
}


def load_vat_ledger_mappings(
    source_path: Path,
) -> tuple[VatLedgerAccountMapping, ...]:
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or not _REQUIRED_COLUMNS.issubset(
                reader.fieldnames,
            ):
                raise VatLedgerMappingError("invalid VAT ledger mapping columns")
            mappings = tuple(_parse_mapping(row) for row in reader)
    except OSError as exc:
        raise VatLedgerMappingError("VAT ledger mapping cannot be read") from exc
    if not mappings:
        raise VatLedgerMappingError("VAT ledger mapping is empty")
    if len({mapping.mapping_id for mapping in mappings}) != len(mappings):
        raise VatLedgerMappingError("duplicate VAT ledger mapping id")
    return mappings


def applicable_vat_ledger_mappings(
    mappings: tuple[VatLedgerAccountMapping, ...],
    period_end: date,
) -> tuple[VatLedgerAccountMapping, ...]:
    return tuple(
        mapping
        for mapping in mappings
        if (mapping.valid_from is None or period_end >= mapping.valid_from)
        and (mapping.valid_to is None or period_end <= mapping.valid_to)
    )


def _parse_mapping(
    row: Mapping[object, object],
) -> VatLedgerAccountMapping:
    values: dict[str, str] = {}
    for key, value in row.items():
        if not isinstance(key, str) or (
            value is not None and not isinstance(value, str)
        ):
            raise VatLedgerMappingError("invalid VAT ledger mapping row")
        values[key] = (value or "").strip()
    required_values = _REQUIRED_COLUMNS.difference({"valid_from", "valid_to"})
    if any(not values[column] for column in required_values):
        raise VatLedgerMappingError("VAT ledger mapping has an empty value")
    if not values["account"].isdigit():
        raise VatLedgerMappingError("VAT ledger account must be numeric")
    try:
        side = LedgerAmountSide(values["amount_side"])
        tolerance = Decimal(values["tolerance"])
        valid_from = (
            date.fromisoformat(values["valid_from"]) if values["valid_from"] else None
        )
        valid_to = (
            date.fromisoformat(values["valid_to"]) if values["valid_to"] else None
        )
    except (ValueError, InvalidOperation) as exc:
        raise VatLedgerMappingError("invalid VAT ledger mapping value") from exc
    if tolerance < 0:
        raise VatLedgerMappingError("VAT ledger tolerance cannot be negative")
    if valid_from and valid_to and valid_to < valid_from:
        raise VatLedgerMappingError("invalid VAT ledger mapping validity")
    return VatLedgerAccountMapping(
        mapping_id=values["mapping_id"],
        version=values["version"],
        account=values["account"],
        declaration_line=values["declaration_line"],
        amount_side=side,
        currency=values["currency"].upper(),
        tolerance=tolerance,
        valid_from=valid_from,
        valid_to=valid_to,
        source_reference=values["source_reference"],
    )
