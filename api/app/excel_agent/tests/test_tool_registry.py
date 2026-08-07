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
        "aggregate_business_nature",
        "query_ledger_entries",
        "calculate_ledger_metrics",
        "detect_data_quality_issues",
        "detect_tax_candidates",
        "normalize_gl",
        "assess_gl_readiness",
        "reconstruct_accounting_entry",
        "find_ras_counterpart",
        "detect_ras_candidates",
        "classify_transaction_semantics",
        "resolve_applicable_ras_rule",
        "calculate_theoretical_ras",
        "run_ras_audit_batch",
        "query_tax_rag",
        "generate_ras_audit_report",
        "assess_ras_accounting",
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


def test_normalize_gl_tool_definition_is_summary_only() -> None:
    registry = create_excel_tool_registry()

    normalize_gl = registry.get("normalize_gl")

    assert normalize_gl is not None
    assert normalize_gl.input_schema["required"] == ["file_path", "sheet_name"]
    assert "summary_only" in normalize_gl.safeguards
    assert "never_return_cell_values" in normalize_gl.safeguards


def test_assess_gl_readiness_tool_definition_cannot_emit_firm_finding() -> None:
    registry = create_excel_tool_registry()

    readiness = registry.get("assess_gl_readiness")

    assert readiness is not None
    assert readiness.input_schema["required"] == ["file_path", "sheet_name"]
    assert "no_firm_finding" in readiness.safeguards
    assert "never_return_cell_values" in readiness.safeguards


def test_reconstruct_accounting_entry_never_groups_on_amount() -> None:
    registry = create_excel_tool_registry()

    reconstruction = registry.get("reconstruct_accounting_entry")

    assert reconstruction is not None
    assert "numero de piece/document" in reconstruction.description
    assert "entry_selector" in reconstruction.input_schema["properties"]
    selector_schema = reconstruction.input_schema["properties"]["entry_selector"]
    assert selector_schema["additionalProperties"] is False
    assert "document_number" in selector_schema["properties"]
    assert "selected_entry" in reconstruction.output_schema["properties"]
    assert "explicit_accounting_key" in reconstruction.safeguards
    assert "no_amount_based_grouping" in reconstruction.safeguards
    assert "never_return_cell_values" in reconstruction.safeguards


def test_find_ras_counterpart_keeps_related_entries_unconfirmed() -> None:
    registry = create_excel_tool_registry()

    counterpart = registry.get("find_ras_counterpart")

    assert counterpart is not None
    assert "contrepartie RAS" in counterpart.description
    assert "detected_candidate_piece_count" in counterpart.output_schema["properties"]
    assert "counterpart_scope_exclusion_count" in counterpart.output_schema[
        "properties"
    ]
    assert "counterpart_scope_basis" in counterpart.output_schema["properties"]
    assert "same_entry_first" in counterpart.safeguards
    assert "potential_related_not_confirmed" in counterpart.safeguards
    assert "configured_account_mapping_only" in counterpart.safeguards


def test_detect_ras_candidates_is_piece_level_and_review_only() -> None:
    registry = create_excel_tool_registry()

    detection = registry.get("detect_ras_candidates")

    assert detection is not None
    assert "piece_level_deduplication" in detection.safeguards
    assert "review_only" in detection.safeguards
    assert "no_tax_decision" in detection.safeguards
    assert "aggregated_account_numbers_only" in detection.safeguards
    assert "review_case_evidence_only" in detection.safeguards
    assert "column_mapping" in detection.input_schema["properties"]
    assert "filters" in detection.input_schema["properties"]
    assert "soumisRas" not in detection.output_schema["properties"]
    assert "tax_category" not in detection.output_schema["properties"]
    assert "tax_rate" not in detection.output_schema["properties"]


def test_semantic_classifier_is_traceable_and_review_only() -> None:
    registry = create_excel_tool_registry()

    semantic = registry.get("classify_transaction_semantics")

    assert semantic is not None
    assert "model_name" in semantic.output_schema["properties"]
    assert "policy_version" in semantic.output_schema["properties"]
    assert "score_summary" in semantic.output_schema["properties"]
    assert "hash_embeddings_forbidden" in semantic.safeguards
    assert "no_tax_decision" in semantic.safeguards


def test_rule_resolver_requires_traced_facts_and_verified_sources() -> None:
    registry = create_excel_tool_registry()

    resolver = registry.get("resolve_applicable_ras_rule")

    assert resolver is not None
    assert resolver.input_schema["required"] == ["transaction_date"]
    assert "facts" not in resolver.input_schema["properties"]
    assert resolver.input_schema["additionalProperties"] is False
    assert "source_hash_verified" in resolver.safeguards
    assert "missing_facts_never_guessed" in resolver.safeguards
    assert "server_fact_attestation_required" in resolver.safeguards


def test_theoretical_calculator_forbids_conversion_and_implicit_rounding() -> None:
    registry = create_excel_tool_registry()

    calculator = registry.get("calculate_theoretical_ras")

    assert calculator is not None
    assert "decimal_only" in calculator.safeguards
    assert "no_currency_conversion" in calculator.safeguards
    assert "no_implicit_rounding" in calculator.safeguards
    assert "expected_amount" in calculator.output_schema["properties"]
    assert "legal_sources" in calculator.output_schema["properties"]


def test_accounting_assessor_derives_date_currency_and_keeps_output_safe() -> None:
    registry = create_excel_tool_registry()

    assessor = registry.get("assess_ras_accounting")

    assert assessor is not None
    assert "tax_rule_date_derived_from_attested_event" in assessor.safeguards
    assert "currency_derived_from_gl" in assessor.safeguards
    assert "potential_adjustment_not_applied" in assessor.safeguards
    assert "source_scope_complete" not in assessor.input_schema["properties"]
    assert "scope_completeness_never_inferred" in assessor.safeguards
    assert "never_return_cell_values" in assessor.safeguards


def test_excel_tool_registry_rejects_unknown_tool() -> None:
    registry = create_excel_tool_registry()

    assert registry.get("unknown") is None


def test_all_ras_tool_schemas_are_closed_and_resource_bounds_are_explicit() -> None:
    registry = create_excel_tool_registry()
    ras_tools = (
        "normalize_gl",
        "assess_gl_readiness",
        "reconstruct_accounting_entry",
        "find_ras_counterpart",
        "detect_ras_candidates",
        "classify_transaction_semantics",
        "resolve_applicable_ras_rule",
        "calculate_theoretical_ras",
        "run_ras_audit_batch",
        "assess_ras_accounting",
        "generate_ras_audit_report",
        "query_tax_rag",
    )

    for tool_name in ras_tools:
        definition = registry.get(tool_name)
        assert definition is not None
        assert definition.input_schema["additionalProperties"] is False
        assert definition.input_schema["type"] == "object"
        assert definition.output_schema["type"] == "object"

    batch = registry.get("run_ras_audit_batch")
    rag = registry.get("query_tax_rag")
    counterpart = registry.get("find_ras_counterpart")
    assessor = registry.get("assess_ras_accounting")
    assert batch is not None and rag is not None
    assert counterpart is not None and assessor is not None
    assert batch.input_schema["properties"]["max_candidates"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 20_000,
    }
    assert rag.input_schema["properties"]["limit"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 5,
    }
    for definition in (counterpart, batch, assessor):
        assert definition.input_schema["properties"]["related_window_days"] == {
            "type": "integer",
            "minimum": 0,
            "maximum": 366,
        }


def test_generate_ras_audit_report_description_tells_model_audit_id_is_enough() -> None:
    definition = create_excel_tool_registry().get("generate_ras_audit_report")

    assert definition is not None
    assert "audit_id est l'entree suffisante" in definition.description
    assert "ne pas demander de faits" in definition.description
