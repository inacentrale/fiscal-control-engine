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


def test_service_period_aggregation_scopes_to_reporting_currency(
    tmp_path: Path,
) -> None:
    workbook_path = tmp_path / "multi_currency_period_ledger.xlsx"
    dataframe = pd.DataFrame(
        {
            "Compte": ["61365000", "61365000", "61365000"],
            "Texte": ["XOF", "Sans devise", "EUR"],
            "Montant": [100.0, 50.0, 40.0],
            "Devise": ["XOF", None, "EUR"],
            "Cle de comptabilisation": ["40", "40", "40"],
            "Periode": [1, 1, 1],
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
    )

    groups = report.aggregations[0].groups
    assert len(groups) == 1
    assert groups[0].key == "1"
    assert groups[0].currency == "XOF"
    assert groups[0].entry_count == 2
    assert groups[0].balance == 150.0


def test_service_aggregates_period_business_nature(tmp_path: Path) -> None:
    workbook_path = tmp_path / "period_nature_ledger.xlsx"
    dataframe = pd.DataFrame(
        {
            "Compte": ["701000", "345520", "701000", "421000"],
            "Texte": ["Vente P1", "Stock P1", "Vente P2", "Salaire P1"],
            "Montant": [300.0, 100.0, 200.0, 50.0],
            "Cle de comptabilisation": ["50", "40", "50", "40"],
            "Periode": [1, 1, 2, 1],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Grand Livre", index=False)
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
        account_balance_rules=_account_balance_rules(),
    )

    report = service.aggregate_business_nature(
        workbook_path,
        sheet_name="Grand Livre",
        dimension="period",
    )

    assert report.dimension == "period"
    periods = {entry.key: entry for entry in report.groups}
    assert periods["1"].resources_balance == 300.0
    assert periods["1"].resources_entry_count == 1
    assert periods["1"].uses_balance == 100.0
    assert periods["1"].uses_entry_count == 1
    assert periods["1"].unclassified_balance == 50.0
    assert periods["1"].unclassified_entry_count == 1
    assert periods["2"].resources_balance == 200.0
    assert periods["2"].uses_balance == 0.0


def test_service_aggregates_business_nature_by_document_type(tmp_path: Path) -> None:
    workbook_path = tmp_path / "document_type_nature_ledger.xlsx"
    dataframe = pd.DataFrame(
        {
            "Compte": ["701000", "345520"],
            "Texte": ["Vente", "Stock"],
            "Montant": [300.0, 100.0],
            "Cle de comptabilisation": ["50", "40"],
            "Type de piece": ["FA", "FA"],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Grand Livre", index=False)
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
        account_balance_rules=_account_balance_rules(),
    )

    report = service.aggregate_business_nature(
        workbook_path,
        sheet_name="Grand Livre",
        dimension="document_type",
    )

    assert report.dimension == "document_type"
    assert len(report.groups) == 1
    group = report.groups[0]
    assert group.key == "FA"
    assert group.resources_balance == 300.0
    assert group.uses_balance == 100.0


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


def test_service_aggregates_by_ohada_account_class(tmp_path: Path) -> None:
    workbook_path = tmp_path / "account_class_ledger.xlsx"
    dataframe = pd.DataFrame(
        {
            "Compte": ["0632100", "706000", "345520", "34552001", "001200"],
            "Texte": ["Charge", "Produit", "Stock", "Sous-compte", "Immo"],
            "Montant": [100.0, 500.0, 40.0, 60.0, 700.0],
            "Clé de comptabilisation": ["40", "50", "40", "40", "40"],
            "Devise du document": ["XOF"] * 5,
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
        group_by=("account_class",),
    )

    groups = {group.key: group for group in report.aggregations[0].groups}
    assert report.aggregations[0].canonical_field == "account_class"
    assert groups["Classe 1"].debit_total == 700.0
    assert groups["Classe 3"].entry_count == 2
    assert groups["Classe 3"].debit_total == 100.0
    assert groups["Classe 6"].debit_total == 100.0
    assert groups["Classe 7"].credit_total == 500.0


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


def test_service_ranks_top_accounts_by_business_balance_when_rules_available(
    tmp_path: Path,
) -> None:
    workbook_path = _write_top_accounts_ledger(tmp_path)
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
        account_balance_rules=_account_balance_rules(),
    )

    report = service.calculate_metrics(
        workbook_path,
        sheet_name="Grand Livre",
        filters={},
        metrics=("count",),
        top_by="account",
        top_limit=5,
    )

    assert report.top is not None
    groups = {group.key: group for group in report.top.groups}
    assert [group.key for group in report.top.groups] == ["401000", "345520"]
    assert groups["401000"].balance == -500.0
    assert groups["401000"].balance_side == "credit"
    assert groups["401000"].normal_side == "credit"
    assert groups["401000"].nature == "suppliers"
    assert groups["401000"].business_balance == 500.0
    assert groups["345520"].balance == 100.0
    assert groups["345520"].balance_side == "debit"
    assert groups["345520"].normal_side == "debit"
    assert groups["345520"].business_balance == 100.0


def test_service_top_accounts_keeps_technical_order_without_balance_rules(
    tmp_path: Path,
) -> None:
    workbook_path = _write_top_accounts_ledger(tmp_path)
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.calculate_metrics(
        workbook_path,
        sheet_name="Grand Livre",
        filters={},
        metrics=("count",),
        top_by="account",
        top_limit=5,
    )

    assert report.top is not None
    assert [group.key for group in report.top.groups] == ["345520", "401000"]
    assert report.top.groups[0].normal_side is None
    assert report.top.groups[0].business_balance == 100.0


def test_service_aggregates_account_class_with_business_balance(tmp_path: Path) -> None:
    workbook_path = _write_account_class_ledger(tmp_path)
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
        account_balance_rules=_account_balance_rules(),
    )

    report = service.aggregate(
        workbook_path,
        sheet_name="Grand Livre",
        group_by=("account_class",),
        limit=10,
    )

    groups = {group.key: group for group in report.aggregations[0].groups}
    assert groups["Classe 3"].balance == 100.0
    assert groups["Classe 3"].balance_side == "debit"
    assert groups["Classe 3"].normal_side == "debit"
    assert groups["Classe 3"].business_balance == 100.0
    assert groups["Classe 7"].balance == -300.0
    assert groups["Classe 7"].balance_side == "credit"
    assert groups["Classe 7"].normal_side == "credit"
    assert groups["Classe 7"].nature == "revenue"
    assert groups["Classe 7"].business_balance == 300.0


def test_service_account_class_keeps_technical_balance_without_rules(
    tmp_path: Path,
) -> None:
    workbook_path = _write_account_class_ledger(tmp_path)
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.aggregate(
        workbook_path,
        sheet_name="Grand Livre",
        group_by=("account_class",),
        limit=10,
    )

    groups = {group.key: group for group in report.aggregations[0].groups}
    assert groups["Classe 7"].normal_side is None
    assert groups["Classe 7"].business_balance == -300.0


def test_service_account_class_view_scopes_to_reporting_currency(
    tmp_path: Path,
) -> None:
    workbook_path = _write_multi_currency_account_class_ledger(tmp_path)
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_key_rules(),
    )

    report = service.aggregate(
        workbook_path,
        sheet_name="Grand Livre",
        group_by=("account_class",),
        limit=10,
    )

    groups = report.aggregations[0].groups
    assert len(groups) == 1
    class_3 = groups[0]
    assert class_3.key == "Classe 3"
    assert class_3.currency == "XOF"
    assert class_3.entry_count == 2
    assert class_3.balance == 150.0


def _write_multi_currency_account_class_ledger(directory: Path) -> Path:
    workbook_path = directory / "multi_currency_account_class_ledger.xlsx"
    dataframe = pd.DataFrame(
        {
            "Compte": ["345520", "345521", "351000"],
            "Texte": ["Stock XOF", "Stock sans devise", "Stock EUR"],
            "Montant": [100.0, 50.0, 40.0],
            "Devise": ["XOF", None, "EUR"],
            "Clé de comptabilisation": ["40", "40", "40"],
            "Exercice comptable": [2024, 2024, 2024],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Grand Livre", index=False)
    return workbook_path


def _write_account_class_ledger(directory: Path) -> Path:
    workbook_path = directory / "account_class_ledger.xlsx"
    dataframe = pd.DataFrame(
        {
            "Compte": ["345520", "701000"],
            "Texte": ["Stock", "Vente"],
            "Montant": [100.0, 300.0],
            "Clé de comptabilisation": ["40", "50"],
            "Exercice comptable": [2024, 2024],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Grand Livre", index=False)
    return workbook_path


def _write_top_accounts_ledger(directory: Path) -> Path:
    workbook_path = directory / "top_accounts_ledger.xlsx"
    dataframe = pd.DataFrame(
        {
            "Compte": ["401000", "345520"],
            "Texte": ["Fournisseur", "Stock"],
            "Montant": [500.0, 100.0],
            "Clé de comptabilisation": ["50", "40"],
            "Exercice comptable": [2024, 2024],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Grand Livre", index=False)
    return workbook_path


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
        AccountBalanceRule("7", "credit", "revenue", "", ""),
    )
