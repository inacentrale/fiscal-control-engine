from pathlib import Path

import pandas as pd

from app.excel_agent.excel_tools import ExcelAgentTools
from app.excel_agent.tests.fixtures import write_minified_grand_livre
from app.ledger_analysis.account_balance_rules import AccountBalanceRule
from app.ledger_analysis.analysis_service import LedgerAnalysisService
from app.ledger_analysis.posting_key_rules import PostingKeyRule


def test_service_builds_minified_grand_livre_report(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    service = LedgerAnalysisService(excel_tools=ExcelAgentTools(allowed_root=tmp_path))

    report = service.analyze(workbook_path, sheet_name="Grand Livre")

    assert report.sheet_name == "Grand Livre"
    assert report.row_count == 4
    assert report.column_count == 5
    assert report.schema_report.is_valid is True
    assert report.schema_report.missing_required_columns == ()
    assert [column.name for column in report.columns] == [
        "Compte",
        "Date comptable",
        "Libelle",
        "Debit",
        "Credit",
    ]


def test_service_report_does_not_expose_cell_values(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    service = LedgerAnalysisService(excel_tools=ExcelAgentTools(allowed_root=tmp_path))

    report = service.analyze(workbook_path, sheet_name="Grand Livre")

    serialized_report = repr(report)
    assert "Achat fournitures" not in serialized_report
    assert "Compte a analyser" not in serialized_report
    assert "601000" not in serialized_report


def test_service_reports_grand_livre_with_missing_required_column(
    tmp_path: Path,
) -> None:
    workbook_path = tmp_path / "invalid_grand_livre.xlsx"
    dataframe = pd.DataFrame(
        {
            "Date comptable": ["2026-01-01"],
            "Libelle": ["Achat fournitures"],
            "Debit": [1200.0],
            "Credit": [None],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Grand Livre", index=False)
    service = LedgerAnalysisService(excel_tools=ExcelAgentTools(allowed_root=tmp_path))

    report = service.analyze(workbook_path, sheet_name="Grand Livre")

    assert report.schema_report.is_valid is False
    assert report.schema_report.missing_required_columns == ("account",)


def test_service_calculates_account_balance_from_posting_keys(
    tmp_path: Path,
) -> None:
    workbook_path = _write_posting_key_ledger(tmp_path, posting_keys=["40", "50", "40"])
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
        account_balance_rules=_account_balance_rules(),
    )

    report = service.calculate_metrics(
        workbook_path,
        sheet_name="Grand Livre",
        filters={"account": "345520"},
        metrics=("balance", "count"),
    )

    assert report.total_matches == 2
    assert report.metrics == {"balance": 70.0, "count": 2}
    assert report.sign_convention == "debit_positive_credit_negative"
    assert report.balance_interpretation == {
        "debit_total": 100.0,
        "credit_total": 30.0,
        "technical_balance": 70.0,
        "balance_side": "debit",
        "account": "345520",
        "normal_side": "debit",
        "nature": "inventory",
        "status": "normal",
        "natural_balance": 70.0,
        "matched_prefix": "3",
    }
    assert report.filters == {"account": "345520"}
    assert report.balance_reconciliation == {
        "entry_count": 2,
        "used_entry_count": 2,
        "excluded_entry_count": 0,
        "raw_amount_sum": 130.0,
        "debit_total": 100.0,
        "credit_total": 30.0,
        "balance": 70.0,
        "formula": "balance = debit_total - credit_total",
        "currency_count": 1,
        "by_currency": {
            "Sans devise": {
                "entry_count": 2,
                "used_entry_count": 2,
                "excluded_entry_count": 0,
                "raw_amount_sum": 130.0,
                "debit_total": 100.0,
                "credit_total": 30.0,
                "balance": 70.0,
            },
        },
        "by_posting_key": [
            {
                "posting_key": "40",
                "side": "debit",
                "entry_count": 1,
                "used_entry_count": 1,
                "excluded_entry_count": 0,
                "raw_amount_sum": 100.0,
                "debit_total": 100.0,
                "credit_total": 0.0,
                "balance": 100.0,
            },
            {
                "posting_key": "50",
                "side": "credit",
                "entry_count": 1,
                "used_entry_count": 1,
                "excluded_entry_count": 0,
                "raw_amount_sum": 30.0,
                "debit_total": 0.0,
                "credit_total": 30.0,
                "balance": -30.0,
            },
        ],
        "excluded_reasons": {
            "missing_or_unknown_posting_key": 0,
            "missing_or_invalid_amount": 0,
        },
    }


def test_service_uses_posting_key_side_for_negative_source_amounts(
    tmp_path: Path,
) -> None:
    workbook_path = _write_posting_key_ledger(
        tmp_path,
        posting_keys=["40", "50", "40"],
        amounts=[100.0, -30.0, 999.0],
    )
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.calculate_metrics(
        workbook_path,
        sheet_name="Grand Livre",
        filters={"account": "345520"},
        metrics=("balance",),
    )

    assert report.metrics["balance"] == 70.0
    assert report.balance_reconciliation is not None
    assert report.balance_reconciliation["used_entry_count"] == 2
    assert report.balance_reconciliation["credit_total"] == 30.0


def test_service_filters_balance_by_fiscal_year(tmp_path: Path) -> None:
    workbook_path = _write_posting_key_ledger(
        tmp_path,
        posting_keys=["40", "50", "40"],
    )
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.calculate_metrics(
        workbook_path,
        sheet_name="Grand Livre",
        filters={"account": "345520", "fiscal_year": "2024"},
        metrics=("balance",),
    )

    assert report.total_matches == 1
    assert report.metrics["balance"] == 100.0
    assert report.filters == {"account": "345520", "fiscal_year": "2024"}


def test_service_warns_when_account_filter_matches_only_prefix(
    tmp_path: Path,
) -> None:
    workbook_path = _write_posting_key_ledger(
        tmp_path,
        posting_keys=["40", "50", "40"],
    )
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.calculate_metrics(
        workbook_path,
        sheet_name="Grand Livre",
        filters={"account": "34552"},
        metrics=("balance",),
    )

    assert report.total_matches == 0
    assert report.filter_warnings == (
        {
            "warning_type": "account_prefix_matches_only",
            "account_filter": "34552",
            "matching_entry_count": 3,
            "matching_account_count": 2,
            "sample_accounts": ["345520", "34552001"],
        },
    )


def test_service_orders_period_aggregation_chronologically(
    tmp_path: Path,
) -> None:
    workbook_path = tmp_path / "period_ledger.xlsx"
    dataframe = pd.DataFrame(
        {
            "Compte": ["61365000", "61365000", "61365000"],
            "Texte": ["P10", "P1", "P2"],
            "Montant": [1000.0, 10.0, 100.0],
            "Cle de comptabilisation": ["40", "40", "40"],
            "Periode": [10, 1, 2],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Grand Livre", index=False)
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.aggregate(
        workbook_path,
        sheet_name="Grand Livre",
        group_by=("period",),
        filters={"account": "61365000"},
    )

    assert [group.key for group in report.aggregations[0].groups] == ["1", "2", "10"]


def test_service_aggregation_exposes_debit_credit_and_excluded_rows(
    tmp_path: Path,
) -> None:
    workbook_path = _write_posting_key_ledger(
        tmp_path,
        posting_keys=["99", "50", "40"],
    )
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.aggregate(
        workbook_path,
        sheet_name="Grand Livre",
        group_by=("account",),
        filters={"account": "345520"},
    )

    assert report.row_count == 2
    assert report.filters == {"account": "345520"}
    group = report.aggregations[0].groups[0]
    assert group.entry_count == 2
    assert group.used_entry_count == 1
    assert group.excluded_entry_count == 1
    assert group.raw_amount_sum == 130.0
    assert group.debit_total == 0.0
    assert group.credit_total == 30.0
    assert group.balance == -30.0
    assert group.amount_sum == group.balance


def test_service_excludes_invalid_amount_without_blocking_metrics(
    tmp_path: Path,
) -> None:
    workbook_path = _write_posting_key_ledger(
        tmp_path,
        posting_keys=["40", "50", "40"],
        amounts=[100.0, None, 999.0],
    )
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.calculate_metrics(
        workbook_path,
        sheet_name="Grand Livre",
        filters={"account": "345520"},
        metrics=("balance",),
    )

    assert report.metrics["balance"] == 100.0
    assert report.balance_reconciliation is not None
    assert report.balance_reconciliation["used_entry_count"] == 1
    assert report.balance_reconciliation["excluded_entry_count"] == 1
    assert report.balance_reconciliation["excluded_reasons"] == {
        "missing_or_unknown_posting_key": 0,
        "missing_or_invalid_amount": 1,
    }


def test_service_returns_signed_amounts_and_normalized_posting_keys(
    tmp_path: Path,
) -> None:
    workbook_path = _write_posting_key_ledger(tmp_path, posting_keys=["40", "50", "40"])
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.query_entries(
        workbook_path,
        sheet_name="Grand Livre",
        filters={"account": "345520"},
    )

    assert [entry["amount"] for entry in report.entries] == ["100", "-30"]
    assert [entry["posting_key"] for entry in report.entries] == ["40", "50"]
    assert report.sign_convention == "debit_positive_credit_negative"


def test_service_excludes_unknown_posting_key_and_reports_warning(
    tmp_path: Path,
) -> None:
    workbook_path = _write_posting_key_ledger(tmp_path, posting_keys=["99", "50", "40"])
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.calculate_metrics(
        workbook_path,
        sheet_name="Grand Livre",
        filters={"account": "345520"},
        metrics=("balance",),
    )
    quality = service.detect_data_quality_issues(workbook_path, "Grand Livre")

    assert report.metrics["balance"] == -30.0
    warning = next(
        issue
        for issue in quality.issues
        if issue.issue_type == "missing_or_unknown_posting_key"
    )
    assert warning.affected_count == 1
    assert warning.affected_accounts[0].account == "345520"
    assert warning.affected_accounts[0].affected_count == 1


def test_service_uses_account_class_for_a_subaccount(tmp_path: Path) -> None:
    workbook_path = _write_posting_key_ledger(tmp_path, posting_keys=["40", "50", "40"])
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
        account_balance_rules=_account_balance_rules(),
    )

    report = service.calculate_metrics(
        workbook_path,
        sheet_name="Grand Livre",
        filters={"account": "34552001"},
        metrics=("balance",),
    )

    assert report.balance_interpretation is not None
    assert report.balance_interpretation["normal_side"] == "debit"
    assert report.balance_interpretation["matched_prefix"] == "3"


def _write_posting_key_ledger(
    directory: Path,
    posting_keys: list[str],
    amounts: list[float | None] | None = None,
) -> Path:
    workbook_path = directory / "posting_key_ledger.xlsx"
    dataframe = pd.DataFrame(
        {
            "Compte": ["345520", "345520", "34552001"],
            "Texte": ["Débit", "Crédit", "Sous-compte"],
            "Montant": amounts or [100.0, 30.0, 999.0],
            "Clé de comptabilisation": posting_keys,
            "Exercice comptable": [2024, 2025, 2024],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Grand Livre", index=False)
    return workbook_path


def _posting_key_rules() -> tuple[PostingKeyRule, ...]:
    return (
        PostingKeyRule("40", "debit", "general_ledger", "standard", "", ""),
        PostingKeyRule("50", "credit", "general_ledger", "standard", "", ""),
    )


def _account_balance_rules() -> tuple[AccountBalanceRule, ...]:
    return (
        AccountBalanceRule("3", "debit", "inventory", "", ""),
        AccountBalanceRule("4", "variable", "third_parties", "", ""),
        AccountBalanceRule("40", "credit", "suppliers", "", ""),
        AccountBalanceRule("409", "debit", "supplier_receivables", "", ""),
        AccountBalanceRule("41", "debit", "customers", "", ""),
        AccountBalanceRule("419", "credit", "customer_payables", "", ""),
    )
