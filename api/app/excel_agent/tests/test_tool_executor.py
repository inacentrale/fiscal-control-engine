from pathlib import Path

import pytest

from app.excel_agent.excel_tools import ExcelAgentTools
from app.excel_agent.tests.fixtures import write_minified_grand_livre
from app.excel_agent.tool_executor import ExcelToolExecutor
from app.excel_agent.tool_registry import create_excel_tool_registry
from app.excel_agent.tool_validator import (
    InvalidToolArgumentsError,
    UnknownToolError,
)
from app.llm.domain import ToolCall


def test_validator_accepts_known_tool_with_valid_arguments(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    executor = _create_executor(tmp_path)

    result = executor.validate(
        ToolCall(
            name="profile_sheet",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Grand Livre",
            },
        ),
    )

    assert result.name == "profile_sheet"
    assert result.arguments["sheet_name"] == "Grand Livre"


def test_validator_rejects_unknown_tool(tmp_path: Path) -> None:
    executor = _create_executor(tmp_path)

    with pytest.raises(UnknownToolError, match="unknown tool"):
        executor.validate(ToolCall(name="delete_file", arguments={}))


def test_validator_rejects_missing_required_argument(tmp_path: Path) -> None:
    executor = _create_executor(tmp_path)

    with pytest.raises(InvalidToolArgumentsError, match="sheet_name"):
        executor.validate(
            ToolCall(
                name="profile_sheet",
                arguments={"file_path": "grand_livre_minifie.xlsx"},
            ),
        )


def test_validator_rejects_invalid_argument_type(tmp_path: Path) -> None:
    executor = _create_executor(tmp_path)

    with pytest.raises(InvalidToolArgumentsError, match="file_path"):
        executor.validate(
            ToolCall(
                name="list_sheets",
                arguments={"file_path": 123},
            ),
        )


def test_executor_rejects_file_outside_allowed_root(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    forbidden_root = tmp_path / "forbidden"
    allowed_root.mkdir()
    forbidden_root.mkdir()
    workbook_path = write_minified_grand_livre(forbidden_root)
    executor = _create_executor(allowed_root)

    result = executor.execute(
        ToolCall(name="list_sheets", arguments={"file_path": str(workbook_path)}),
    )

    assert result.ok is False
    assert result.error_code == "unsafe_excel_path"
    assert result.output == {}


def test_executor_rejects_missing_file(tmp_path: Path) -> None:
    executor = _create_executor(tmp_path)

    result = executor.execute(
        ToolCall(
            name="list_sheets",
            arguments={"file_path": str(tmp_path / "missing.xlsx")},
        ),
    )

    assert result.ok is False
    assert result.error_code == "excel_file_read"


def test_executor_rejects_invalid_excel_file(tmp_path: Path) -> None:
    invalid_workbook = tmp_path / "invalid.xlsx"
    invalid_workbook.write_text("not a real workbook", encoding="utf-8")
    executor = _create_executor(tmp_path)

    result = executor.execute(
        ToolCall(
            name="list_sheets",
            arguments={"file_path": str(invalid_workbook)},
        ),
    )

    assert result.ok is False
    assert result.error_code == "excel_file_read"


def test_executor_profiles_minified_grand_livre_without_cell_values(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    executor = _create_executor(tmp_path)

    result = executor.execute(
        ToolCall(
            name="profile_sheet",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Grand Livre",
            },
        ),
    )

    assert result.ok is True
    assert result.error_code is None
    assert result.output["sheet_name"] == "Grand Livre"
    assert result.output["row_count"] == 4
    assert result.output["column_count"] == 5
    assert result.output["columns"][0]["name"] == "Compte"
    serialized_output = repr(result.output)
    assert "Achat fournitures" not in serialized_output
    assert "Compte a analyser" not in serialized_output


def test_executor_analyzes_minified_grand_livre_without_cell_values(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    executor = _create_executor(tmp_path)

    result = executor.execute(
        ToolCall(
            name="analyze_ledger",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Grand Livre",
            },
        ),
    )

    assert result.ok is True
    assert result.output["sheet_name"] == "Grand Livre"
    assert result.output["row_count"] == 4
    assert result.output["schema"]["is_valid"] is True
    assert result.output["schema"]["missing_required_columns"] == []
    assert result.output["columns"][0]["name"] == "Compte"
    serialized_output = repr(result.output)
    assert "Achat fournitures" not in serialized_output
    assert "Compte a analyser" not in serialized_output
    assert "601000" not in serialized_output


def test_executor_classifies_anonymized_ledger_schema_without_cell_values() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="classify_ledger_schema",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
            },
        ),
    )

    assert result.ok is True
    assert result.output["sheet_name"] == "Sheet1"
    assert result.output["schema"]["is_usable"] is True
    assert result.output["schema"]["requires_confirmation"] is False
    mappings = {
        mapping["canonical_field"]: mapping
        for mapping in result.output["schema"]["mappings"]
    }
    assert mappings["account"]["source_column"] == "Compte"
    assert mappings["amount"]["source_column"] == "Montant devise document"
    assert mappings["tax_code"]["source_column"] == "Code TVA"
    assert mappings["document_type"]["source_column"] == "Type de pièce"
    serialized_output = repr(result.output)
    assert "SAP" not in serialized_output
    assert "Achat" not in serialized_output
    assert "601000" not in serialized_output


def test_executor_analyzes_anonymized_ledger_with_canonical_schema() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="analyze_ledger",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
            },
        ),
    )

    assert result.ok is True
    assert result.output["sheet_name"] == "Sheet1"
    assert result.output["row_count"] == 2500
    assert result.output["schema"]["is_valid"] is True
    assert result.output["schema"]["canonical_schema"]["is_usable"] is True
    assert result.output["schema"]["canonical_schema"]["fields"]["account"] == "Compte"
    assert (
        result.output["schema"]["canonical_schema"]["fields"]["amount"]
        == "Montant devise document"
    )
    assert result.output["schema"]["canonical_schema"]["fields"]["text"] == "Texte"
    serialized_output = repr(result.output)
    assert "Achat" not in serialized_output
    assert "601000" not in serialized_output


def test_executor_aggregates_anonymized_ledger_without_cell_values() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="aggregate_ledger",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
                "group_by": ["account", "tax_code"],
                "limit": 5,
            },
        ),
    )

    assert result.ok is True
    assert result.output["sheet_name"] == "Sheet1"
    assert result.output["row_count"] == 2500
    assert result.output["amount_field"] == "Montant devise document"
    by_account = result.output["aggregations"]["account"]
    assert by_account["total_groups"] == 13
    account_group = by_account["groups"][0]
    assert account_group["key"] == "61365000"
    assert account_group["entry_count"] == 227
    assert account_group["amount_sum"] == 61173000.0
    assert account_group["balance"] == 61173000.0
    assert account_group["currency"] == "XOF"
    assert account_group["used_entry_count"] == 227
    assert account_group["excluded_entry_count"] == 0
    by_tax_code = result.output["aggregations"]["tax_code"]
    assert by_tax_code["total_groups"] == 2
    tax_group = by_tax_code["groups"][0]
    assert tax_group["key"] == "V1"
    assert tax_group["entry_count"] == 749
    assert tax_group["amount_sum"] == 87676740.0
    assert tax_group["balance"] == 87676740.0
    assert tax_group["currency"] == "XOF"
    serialized_output = repr(result.output)
    assert "Achat" not in serialized_output
    assert "601000" not in serialized_output


def test_executor_queries_ledger_entries_with_pagination_and_allowed_columns() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="query_ledger_entries",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
                "filters": {"account": "44380002"},
                "page": 1,
                "page_size": 3,
            },
        ),
    )

    assert result.ok is True
    assert result.output["sheet_name"] == "Sheet1"
    assert result.output["total_matches"] == 701
    assert result.output["page"] == 1
    assert result.output["page_size"] == 3
    assert len(result.output["entries"]) == 3
    first_entry = result.output["entries"][0]
    assert first_entry["account"] == "44380002"
    assert "amount" in first_entry
    assert "tax_code" in first_entry
    assert "text" not in first_entry
    serialized_output = repr(result.output)
    assert "Achat" not in serialized_output
    assert "601000" not in serialized_output


def test_executor_queries_real_anonymized_account_with_stable_payload() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="query_ledger_entries",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
                "filters": {"account": "44585100"},
                "page": 1,
                "page_size": 20,
            },
        ),
    )

    assert result.ok is True
    assert result.output["total_matches"] == 203
    assert result.output["page"] == 1
    assert result.output["page_size"] == 20
    assert result.output["filters"] == {"account": "44585100"}
    assert "account" in result.output["returned_columns"]
    assert len(result.output["entries"]) == 20
    assert result.output["message"] == "Écritures trouvées pour les filtres fournis."


def test_executor_queries_real_anonymized_account_and_period() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="query_ledger_entries",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
                "filters": {"account": "44585100", "period": "12"},
                "page": 1,
                "page_size": 20,
            },
        ),
    )

    assert result.ok is True
    assert result.output["total_matches"] == 15
    assert result.output["filters"] == {"account": "44585100", "period": "12"}


def test_executor_rejects_invalid_query_filter() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="query_ledger_entries",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
                "filters": {"unknown": "value"},
            },
        ),
    )

    assert result.ok is False
    assert result.error_code == "invalid_filter"


def test_executor_calculates_ledger_metrics_without_cell_values() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="calculate_ledger_metrics",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
                "filters": {"account": "44380002"},
                "metrics": ["sum", "count", "average", "min", "max"],
                "top_by": "account",
                "top_limit": 3,
            },
        ),
    )

    assert result.ok is True
    assert result.output["sheet_name"] == "Sheet1"
    assert result.output["total_matches"] == 701
    assert result.output["amount_field"] == "Montant devise document"
    assert result.output["metrics"] == {
        "sum": -124078785.0,
        "count": 701,
        "average": -177002.55,
        "min": -565000.0,
        "max": 346000.0,
    }
    assert result.output["top"]["canonical_field"] == "account"
    top_group = result.output["top"]["groups"][0]
    assert top_group["key"] == "44380002"
    assert top_group["entry_count"] == 701
    assert top_group["amount_sum"] == -124078785.0
    assert top_group["balance"] == -124078785.0
    assert top_group["currency"] == "XOF"
    serialized_output = repr(result.output)
    assert "Achat" not in serialized_output
    assert "601000" not in serialized_output


def test_executor_detects_data_quality_issues_without_cell_values() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="detect_data_quality_issues",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
            },
        ),
    )

    assert result.ok is True
    assert result.output["sheet_name"] == "Sheet1"
    assert result.output["row_count"] == 2500
    issue_types = {issue["issue_type"] for issue in result.output["issues"]}
    assert "empty_column" in issue_types
    assert "missing_counterparty" in issue_types
    missing_counterparty = next(
        issue
        for issue in result.output["issues"]
        if issue["issue_type"] == "missing_counterparty"
    )
    assert missing_counterparty["affected_count"] == 661
    assert missing_counterparty["severity"] == "warning"
    serialized_output = repr(result.output)
    assert "Achat" not in serialized_output
    assert "601000" not in serialized_output


def test_executor_detects_tax_candidates_from_reference_rules() -> None:
    docs_root = _docs_root()
    workbook_path = docs_root / "GL_anonymise_2500.xlsx"
    executor = _create_executor(docs_root)

    result = executor.execute(
        ToolCall(
            name="detect_tax_candidates",
            arguments={
                "file_path": str(workbook_path),
                "sheet_name": "Sheet1",
                "limit": 5,
            },
        ),
    )

    assert result.ok is True
    assert result.output["sheet_name"] == "Sheet1"
    assert result.output["row_count"] == 2500
    assert result.output["decision_status"] == "review_required"
    categories = {
        candidate["category"]: candidate
        for candidate in result.output["candidates"]
    }
    assert categories["resident_services"]["entry_count"] == 227
    assert categories["resident_services"]["amount_sum"] == 61173000.0
    assert categories["real_estate_charges"]["entry_count"] == 129
    assert categories["non_resident_services"]["entry_count"] == 87
    serialized_output = repr(result.output)
    assert "HONORAIRES" not in serialized_output
    assert "LOYER" not in serialized_output


def _create_executor(allowed_root: Path) -> ExcelToolExecutor:
    return ExcelToolExecutor(
        tools=ExcelAgentTools(allowed_root=allowed_root),
        registry=create_excel_tool_registry(),
    )


def _docs_root() -> Path:
    docker_docs_root = Path("/workspace/docs")
    if docker_docs_root.is_dir():
        return docker_docs_root
    return Path("../docs")
