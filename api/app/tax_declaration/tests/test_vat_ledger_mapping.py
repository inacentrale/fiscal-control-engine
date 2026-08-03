from datetime import date
from pathlib import Path

import pytest

from app.tax_declaration.vat_ledger_mapping import (
    LedgerAmountSide,
    VatLedgerMappingError,
    applicable_vat_ledger_mappings,
    load_vat_ledger_mappings,
)


def test_loads_applicable_versioned_account_mapping(tmp_path: Path) -> None:
    source = _write_mapping(
        tmp_path,
        "out,v1,443100,19,credit,XOF,1,2024-01-01,,config-2024\n",
    )

    mappings = load_vat_ledger_mappings(source)
    applicable = applicable_vat_ledger_mappings(
        mappings,
        date(2025, 1, 31),
    )

    assert applicable[0].amount_side is LedgerAmountSide.CREDIT
    assert applicable[0].currency == "XOF"


def test_rejects_non_numeric_account_mapping(tmp_path: Path) -> None:
    source = _write_mapping(
        tmp_path,
        "out,v1,TVA,19,credit,XOF,0,,,config\n",
    )

    with pytest.raises(VatLedgerMappingError, match="numeric"):
        load_vat_ledger_mappings(source)


def _write_mapping(tmp_path: Path, rows: str) -> Path:
    source = tmp_path / "mapping.csv"
    source.write_text(
        "mapping_id,version,account,declaration_line,amount_side,currency,"
        "tolerance,valid_from,valid_to,source_reference\n" + rows,
        encoding="utf-8",
    )
    return source
