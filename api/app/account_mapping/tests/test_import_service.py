from pathlib import Path

import pytest

from app.account_mapping.domain import GeneralLedgerAccount, PlanAccount
from app.account_mapping.import_service import (
    AccountMappingImportService,
    MissingColumnError,
    UnsupportedSourceFileError,
)


def test_import_ledger_accounts_from_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "ledger_accounts.csv"
    csv_path.write_text(
        "Compte\n16000BSP\n 16000RAM \n16000BSP\n\n",
        encoding="utf-8",
    )
    service = AccountMappingImportService()

    accounts = service.read_ledger_accounts(csv_path)

    assert accounts == [
        GeneralLedgerAccount(number="16000BSP"),
        GeneralLedgerAccount(number="16000RAM"),
    ]


def test_import_plan_accounts_from_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "plan_accounts.csv"
    csv_path.write_text(
        ",Texte descr.cpt gén.\n"
        "62210000,HONORAIRES\n"
        "61320000, LOYERS \n"
        ",ligne sans compte\n",
        encoding="utf-8",
    )
    service = AccountMappingImportService()

    accounts = service.read_plan_accounts(csv_path)

    assert accounts == [
        PlanAccount(number="62210000", label="HONORAIRES"),
        PlanAccount(number="61320000", label="LOYERS"),
    ]


def test_import_plan_accounts_skips_rows_without_label(tmp_path: Path) -> None:
    csv_path = tmp_path / "plan_accounts.csv"
    csv_path.write_text(
        ",Texte descr.cpt gén.\n62210000,\n61320000,LOYERS\n",
        encoding="utf-8",
    )
    service = AccountMappingImportService()

    accounts = service.read_plan_accounts(csv_path)

    assert accounts == [PlanAccount(number="61320000", label="LOYERS")]


def test_import_ledger_accounts_requires_compte_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "ledger_accounts.csv"
    csv_path.write_text("Account\n62210000\n", encoding="utf-8")
    service = AccountMappingImportService()

    with pytest.raises(MissingColumnError, match="Compte"):
        service.read_ledger_accounts(csv_path)


def test_import_ledger_accounts_rejects_empty_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "ledger_accounts.csv"
    csv_path.write_text("", encoding="utf-8")
    service = AccountMappingImportService()

    with pytest.raises(MissingColumnError, match="Compte"):
        service.read_ledger_accounts(csv_path)


def test_import_plan_accounts_requires_label_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "plan_accounts.csv"
    csv_path.write_text(",Label\n62210000,HONORAIRES\n", encoding="utf-8")
    service = AccountMappingImportService()

    with pytest.raises(MissingColumnError, match="Texte descr.cpt gén."):
        service.read_plan_accounts(csv_path)


def test_import_rejects_unsupported_source_file(tmp_path: Path) -> None:
    source_path = tmp_path / "ledger_accounts.txt"
    source_path.write_text("Compte\n62210000\n", encoding="utf-8")
    service = AccountMappingImportService()

    with pytest.raises(UnsupportedSourceFileError, match="unsupported source file"):
        service.read_ledger_accounts(source_path)
