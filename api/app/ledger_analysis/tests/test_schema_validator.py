from pathlib import Path

import pandas as pd

from app.excel_agent.excel_tools import ExcelAgentTools
from app.excel_agent.tests.fixtures import write_minified_grand_livre
from app.ledger_analysis.schema_validator import LedgerSchemaValidator


def test_validator_accepts_minified_grand_livre_schema(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    excel_tools = ExcelAgentTools(allowed_root=tmp_path)
    columns = excel_tools.get_columns(workbook_path, sheet_name="Grand Livre").columns
    validator = LedgerSchemaValidator()

    report = validator.validate(columns)

    assert report.is_valid is True
    assert report.present_columns == (
        "Compte",
        "Date comptable",
        "Libelle",
        "Debit",
        "Credit",
    )
    assert report.missing_required_columns == ()
    assert report.optional_columns == ()


def test_validator_reports_missing_required_account_column() -> None:
    validator = LedgerSchemaValidator()

    report = validator.validate(("Date comptable", "Libelle", "Debit", "Credit"))

    assert report.is_valid is False
    assert report.missing_required_columns == ("Compte",)


def test_validator_reports_optional_columns_without_failing() -> None:
    validator = LedgerSchemaValidator(optional_columns=("Piece", "Journal"))

    report = validator.validate(
        ("Compte", "Date comptable", "Libelle", "Debit", "Credit", "Journal"),
    )

    assert report.is_valid is True
    assert report.optional_columns == ("Journal",)


def test_validator_normalizes_accents_and_case() -> None:
    validator = LedgerSchemaValidator()

    report = validator.validate(
        ("compte", "DATE COMPTABLE", "Libellé", "Débit", "Crédit"),
    )

    assert report.is_valid is True


def test_fixture_writer_creates_expected_ledger_columns(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)

    dataframe = pd.read_excel(workbook_path, sheet_name="Grand Livre", nrows=0)

    assert tuple(dataframe.columns) == (
        "Compte",
        "Date comptable",
        "Libelle",
        "Debit",
        "Credit",
    )
