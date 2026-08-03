import csv
from pathlib import Path
from typing import Any

from app.account_mapping.domain import GeneralLedgerAccount, PlanAccount

LEDGER_ACCOUNT_COLUMN = "Compte"
PLAN_ACCOUNT_NUMBER_COLUMN = ""
PLAN_ACCOUNT_LABEL_COLUMN = "Texte descr.cpt gén."
EXCEL_SUFFIXES = {".xls", ".xlsx"}


class MissingColumnError(ValueError):
    pass


class UnsupportedSourceFileError(ValueError):
    pass


class AccountMappingImportService:
    def read_ledger_accounts(self, source_path: Path) -> list[GeneralLedgerAccount]:
        rows = _read_rows(source_path)
        _require_columns(rows, [LEDGER_ACCOUNT_COLUMN])
        account_numbers = [
            row.get(LEDGER_ACCOUNT_COLUMN, "").strip()
            for row in rows
            if row.get(LEDGER_ACCOUNT_COLUMN, "").strip()
        ]
        return [
            GeneralLedgerAccount(number=account_number)
            for account_number in _deduplicate(account_numbers)
        ]

    def read_plan_accounts(self, source_path: Path) -> list[PlanAccount]:
        rows = _read_rows(source_path)
        _require_columns(rows, [PLAN_ACCOUNT_NUMBER_COLUMN, PLAN_ACCOUNT_LABEL_COLUMN])

        accounts: list[PlanAccount] = []
        for row in rows:
            account_number = row.get(PLAN_ACCOUNT_NUMBER_COLUMN, "").strip()
            label = row.get(PLAN_ACCOUNT_LABEL_COLUMN, "").strip()
            if account_number and label:
                accounts.append(PlanAccount(number=account_number, label=label))
        return accounts


def _read_rows(source_path: Path) -> list[dict[str, str]]:
    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        return _read_csv_rows(source_path)
    if suffix in EXCEL_SUFFIXES:
        return _read_excel_rows(source_path)
    raise UnsupportedSourceFileError(f"unsupported source file: {source_path}")


def _read_csv_rows(source_path: Path) -> list[dict[str, str]]:
    with source_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return [
            {key or "": value or "" for key, value in row.items()}
            for row in reader
            if row
        ]


def _read_excel_rows(source_path: Path) -> list[dict[str, str]]:
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise UnsupportedSourceFileError(
            "Excel import requires pandas and an Excel reader dependency",
        ) from exc

    dataframe = pd.read_excel(source_path, dtype=str)
    dataframe = dataframe.fillna("")
    records: list[dict[str, Any]] = dataframe.to_dict(orient="records")
    return [
        {str(key) if key is not None else "": str(value) for key, value in row.items()}
        for row in records
    ]


def _require_columns(rows: list[dict[str, str]], required_columns: list[str]) -> None:
    columns = set(rows[0].keys()) if rows else set()
    missing_columns = [column for column in required_columns if column not in columns]
    if missing_columns:
        raise MissingColumnError(
            f"missing required columns: {', '.join(missing_columns)}",
        )


def _deduplicate(values: list[str]) -> list[str]:
    deduplicated: dict[str, None] = {}
    for value in values:
        deduplicated.setdefault(value, None)
    return list(deduplicated)
