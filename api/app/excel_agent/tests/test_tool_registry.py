from app.excel_agent.tool_registry import create_excel_tool_registry


def test_excel_tool_registry_exposes_initial_tools() -> None:
    registry = create_excel_tool_registry()

    assert registry.names == (
        "list_sheets",
        "get_columns",
        "profile_sheet",
        "classify_ledger_schema",
        "analyze_ledger",
        "aggregate_ledger",
        "query_ledger_entries",
        "calculate_ledger_metrics",
        "detect_data_quality_issues",
        "detect_tax_candidates",
    )


def test_excel_tool_definitions_have_contracts_and_safeguards() -> None:
    registry = create_excel_tool_registry()

    profile_sheet = registry.get("profile_sheet")

    assert profile_sheet is not None
    assert profile_sheet.name == "profile_sheet"
    assert profile_sheet.description
    assert profile_sheet.input_schema["required"] == ["file_path", "sheet_name"]
    assert profile_sheet.output_schema["type"] == "object"
    assert "never_return_cell_values" in profile_sheet.safeguards


def test_analyze_ledger_tool_definition_is_metadata_only() -> None:
    registry = create_excel_tool_registry()

    analyze_ledger = registry.get("analyze_ledger")

    assert analyze_ledger is not None
    assert analyze_ledger.input_schema["required"] == ["file_path", "sheet_name"]
    assert "ledger_schema_reporting" in analyze_ledger.safeguards
    assert "never_return_cell_values" in analyze_ledger.safeguards


def test_classify_ledger_schema_tool_definition_is_metadata_only() -> None:
    registry = create_excel_tool_registry()

    classify_schema = registry.get("classify_ledger_schema")

    assert classify_schema is not None
    assert classify_schema.input_schema["required"] == ["file_path", "sheet_name"]
    assert "ledger_schema_mapping" in classify_schema.safeguards
    assert "never_return_cell_values" in classify_schema.safeguards


def test_aggregate_ledger_tool_definition_is_metadata_only() -> None:
    registry = create_excel_tool_registry()

    aggregate_ledger = registry.get("aggregate_ledger")

    assert aggregate_ledger is not None
    assert aggregate_ledger.input_schema["required"] == ["file_path", "sheet_name"]
    assert "ledger_aggregation" in aggregate_ledger.safeguards
    assert "never_return_cell_values" in aggregate_ledger.safeguards


def test_query_ledger_entries_tool_definition_is_limited() -> None:
    registry = create_excel_tool_registry()

    query_ledger_entries = registry.get("query_ledger_entries")

    assert query_ledger_entries is not None
    assert query_ledger_entries.input_schema["required"] == ["file_path", "sheet_name"]
    assert "paginated_output" in query_ledger_entries.safeguards
    assert "allowed_columns_only" in query_ledger_entries.safeguards


def test_calculate_ledger_metrics_tool_definition_is_metadata_only() -> None:
    registry = create_excel_tool_registry()

    calculate_ledger_metrics = registry.get("calculate_ledger_metrics")

    assert calculate_ledger_metrics is not None
    assert calculate_ledger_metrics.input_schema["required"] == [
        "file_path",
        "sheet_name",
    ]
    assert "ledger_metrics" in calculate_ledger_metrics.safeguards
    assert "never_return_cell_values" in calculate_ledger_metrics.safeguards


def test_detect_data_quality_issues_tool_definition_is_metadata_only() -> None:
    registry = create_excel_tool_registry()

    quality_tool = registry.get("detect_data_quality_issues")

    assert quality_tool is not None
    assert quality_tool.input_schema["required"] == ["file_path", "sheet_name"]
    assert "ledger_data_quality" in quality_tool.safeguards
    assert "never_return_cell_values" in quality_tool.safeguards


def test_detect_tax_candidates_tool_definition_is_review_only() -> None:
    registry = create_excel_tool_registry()

    tax_tool = registry.get("detect_tax_candidates")

    assert tax_tool is not None
    assert tax_tool.input_schema["required"] == ["file_path", "sheet_name"]
    assert "review_only" in tax_tool.safeguards
    assert "no_tax_decision" in tax_tool.safeguards


def test_excel_tool_registry_rejects_unknown_tool() -> None:
    registry = create_excel_tool_registry()

    assert registry.get("unknown") is None
