from pathlib import Path

from app.agent.orchestrator import (
    AgentOrchestrator,
    AgentRunEvent,
    AgentRunRequest,
    _compact_tool_output,
    _deterministic_file_intent_tool_calls,
    _deterministic_tool_results_answer,
    _file_metric_lines,
    _file_tax_candidate_lines,
    _next_ras_workflow_call,
    _ras_workflow_event,
    _single_candidate_ras_followup,
    _with_request_context,
)
from app.excel_agent.domain import ToolExecutionResult
from app.excel_agent.excel_tools import ExcelAgentTools
from app.excel_agent.tests.fixtures import write_minified_grand_livre
from app.excel_agent.tool_executor import ExcelToolExecutor
from app.excel_agent.tool_registry import create_excel_tool_registry
from app.llm.domain import (
    ModelProvider,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ModelToolDefinition,
    ToolCall,
)
from app.llm.fallback_model import FallbackModelProvider
from app.ras_audit.fact_context import (
    RasExplicitFactExtractor,
    RasFactContextAttestor,
    load_ras_user_fact_patterns,
)
from app.ras_audit.legal_rules import load_ras_legal_rules
from app.ras_audit.tax_event_rules import load_ras_tax_event_rules
from app.ras_audit.tax_rag_query import TaxRagQueryService
from app.ras_audit.theoretical_calculation import load_ras_calculation_parameters

ROOT = Path(__file__).resolve().parents[4]


def test_orchestrator_returns_model_answer_without_tool_call(tmp_path: Path) -> None:
    orchestrator = _create_orchestrator(
        tmp_path,
        FakeModelProvider(
            responses=(
                ModelResponse(
                    text="Je peux analyser le Grand Livre fourni.",
                    provider_name="fake",
                    model_name="fake-model",
                    finish_reason="stop",
                    tool_calls=(),
                ),
            ),
        ),
    )

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Que peux-tu faire ?",
            file_path=None,
            sheet_name=None,
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == "Je peux analyser le Grand Livre fourni."
    assert result.tool_results == ()
    assert result.provider_name == "fake"
    assert result.model_name == "fake-model"
    assert [event.event_type for event in result.execution_events] == [
        "run_started",
        "model_requested",
        "answer_ready",
    ]


def test_initial_prompt_keeps_greeting_short_and_hides_tools(tmp_path: Path) -> None:
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="Bonjour. Ajoutez un fichier Excel ou posez une question.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Bonjour",
            file_path=None,
            sheet_name=None,
            allowed_tools=("query_tax_rag", "calculate_theoretical_ras"),
        ),
    )

    system_prompt = model.requests[0].messages[0].content
    assert result.answer == "Bonjour. Ajoutez un fichier Excel ou posez une question."
    assert "une phrase courte et naturelle" in system_prompt
    assert "ne liste jamais les outils disponibles" in system_prompt
    assert "Ne mentionne RAS, fiscalite, droit, CGI ou calcul" in system_prompt


def test_request_context_is_not_injected_into_non_file_tools() -> None:
    request = AgentRunRequest(
        user_message="Question fiscale",
        file_path=Path("ledger.xlsx"),
        sheet_name="GL",
        allowed_tools=("query_tax_rag",),
    )

    contextualized = _with_request_context(
        ToolCall(name="query_tax_rag", arguments={"query": "RAS resident"}),
        request,
    )

    assert contextualized.arguments == {"query": "RAS resident"}


def test_report_generation_guidance_uses_audit_id_as_sufficient_input(
    tmp_path: Path,
) -> None:
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="Preciser un audit_id.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        )
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    orchestrator.run(
        AgentRunRequest(
            user_message="Genere le rapport de l'audit RAS audit-1.",
            file_path=None,
            sheet_name=None,
            allowed_tools=("generate_ras_audit_report",),
        ),
    )

    system_prompt = model.requests[0].messages[0].content
    tool_description = model.requests[0].tool_definitions[0].description
    assert "utilise generate_ras_audit_report" in system_prompt
    assert "L'audit_id suffit" in system_prompt
    assert "L'audit_id est l'entree suffisante" in tool_description


def test_report_output_is_compacted_for_final_answer() -> None:
    compact = _compact_tool_output(
        ToolExecutionResult(
            tool_name="generate_ras_audit_report",
            ok=True,
            output={
                "report_id": "report-1",
                "source_sha256": "a" * 64,
                "generated_at": "2026-08-05T10:00:00Z",
                "case_count": 2,
                "status_counts": {"indeterminate": 2},
                "certainty_counts": {"low": 2},
                "amount_summaries": [{"currency": "XOF", "expected": "0"}],
                "recorded_amount_summaries": [
                    {"currency": "XOF", "recorded_amount": "1000"}
                ],
                "details": [{"candidate_id": "candidate-1"}],
                "reference_versions": ["rules-v1"],
                "decision_status": "report_only_no_tax_decision",
            },
        ),
    )

    assert compact["report_id"] == "report-1"
    assert compact["case_count"] == 2
    assert compact["amount_summaries"] == [{"currency": "XOF", "expected": "0"}]
    assert compact["recorded_amount_summaries"] == [
        {"currency": "XOF", "recorded_amount": "1000"}
    ]
    assert compact["reference_versions"] == ["rules-v1"]


def test_report_result_has_specific_deterministic_answer() -> None:
    answer = _deterministic_tool_results_answer(
        (
            ToolExecutionResult(
                tool_name="generate_ras_audit_report",
                ok=True,
                output={
                    "report_id": "report-1",
                    "case_count": 2,
                    "status_counts": {"indeterminate_missing_data": 1},
                    "certainty_counts": {"indeterminate": 1},
                    "amount_summaries": [],
                    "recorded_amount_summaries": [
                        {
                            "certainty": "indeterminate",
                            "currency": "XOF",
                            "case_count": 1,
                            "recorded_amount": "2500",
                        }
                    ],
                    "reference_versions": ["rules-v1"],
                },
            ),
        )
    )

    assert "**Rapport d'audit RAS**" in answer
    assert "Identifiant du rapport : report-1" in answer
    assert "XOF/Indéterminée: 1 cas, comptabilise 2500" in answer


def test_single_candidate_batch_builds_safe_deterministic_followup() -> None:
    request = AgentRunRequest(
        user_message="Audite la RAS.",
        file_path=Path("ledger.xlsx"),
        sheet_name="GL",
        allowed_tools=("run_ras_audit_batch", "assess_ras_accounting"),
    )
    batch = ToolExecutionResult(
        tool_name="run_ras_audit_batch",
        ok=True,
        output={
            "audit_id": "audit-1",
            "review_candidate_ids": ["candidate-1"],
            "remaining_candidate_count": 0,
        },
    )

    followup = _single_candidate_ras_followup((batch,), request)

    assert followup == ToolCall(
        name="assess_ras_accounting",
        arguments={"base_audit_id": "audit-1", "candidate_id": "candidate-1"},
    )


def test_multi_candidate_batch_never_applies_user_facts_globally() -> None:
    request = AgentRunRequest(
        user_message="Audite la RAS.",
        file_path=Path("ledger.xlsx"),
        sheet_name="GL",
        allowed_tools=("run_ras_audit_batch", "assess_ras_accounting"),
    )
    batch = ToolExecutionResult(
        tool_name="run_ras_audit_batch",
        ok=True,
        output={
            "audit_id": "audit-1",
            "review_candidate_ids": ["candidate-1", "candidate-2"],
            "remaining_candidate_count": 0,
        },
    )

    assert _single_candidate_ras_followup((batch,), request) is None


def test_ras_workflow_plans_assessment_then_derived_report() -> None:
    request = AgentRunRequest(
        user_message="Audite la RAS.",
        file_path=Path("ledger.xlsx"),
        sheet_name="GL",
        allowed_tools=(
            "run_ras_audit_batch",
            "assess_ras_accounting",
            "generate_ras_audit_report",
        ),
    )
    batch = ToolExecutionResult(
        tool_name="run_ras_audit_batch",
        ok=True,
        output={
            "audit_id": "audit-1",
            "review_candidate_ids": ["candidate-1"],
            "remaining_candidate_count": 0,
        },
    )

    assessment_call = _next_ras_workflow_call((batch,), request)

    assert assessment_call == ToolCall(
        name="assess_ras_accounting",
        arguments={"base_audit_id": "audit-1", "candidate_id": "candidate-1"},
    )
    assessment = ToolExecutionResult(
        tool_name="assess_ras_accounting",
        ok=True,
        output={"audit_id": "audit-2", "missing_facts": []},
    )

    assert _next_ras_workflow_call((batch, assessment), request) == ToolCall(
        name="generate_ras_audit_report",
        arguments={"audit_id": "audit-2"},
    )


def test_ras_workflow_chains_selected_entry_to_counterpart_search() -> None:
    request = AgentRunRequest(
        user_message=(
            "Analyse la pièce 000042, reconstruis son écriture et recherche "
            "une éventuelle contrepartie RAS."
        ),
        file_path=Path("ledger.xlsx"),
        sheet_name="GL",
        allowed_tools=(
            "reconstruct_accounting_entry",
            "find_ras_counterpart",
        ),
    )
    reconstruction = ToolExecutionResult(
        tool_name="reconstruct_accounting_entry",
        ok=True,
        output={
            "selector": {"document_number": "000042", "fiscal_year": 2025},
            "selected_entry_found": True,
        },
    )

    assert _next_ras_workflow_call((reconstruction,), request) == ToolCall(
        name="find_ras_counterpart",
        arguments={
            "entry_selector": {
                "document_number": "000042",
                "fiscal_year": 2025,
            }
        },
    )


def test_ras_audit_intent_is_routed_through_readiness_before_batch() -> None:
    request = AgentRunRequest(
        user_message="Audite la RAS de ce Grand Livre.",
        file_path=Path("ledger.xlsx"),
        sheet_name="GL",
        allowed_tools=(
            "normalize_gl",
            "assess_gl_readiness",
            "detect_ras_candidates",
            "run_ras_audit_batch",
        ),
    )

    calls = _deterministic_file_intent_tool_calls(request)

    assert [call.name for call in calls] == [
        "normalize_gl",
        "assess_gl_readiness",
        "detect_ras_candidates",
        "run_ras_audit_batch",
    ]


def test_candidate_detection_emits_safe_detected_workflow_state() -> None:
    event = _ras_workflow_event(
        ToolExecutionResult(
            tool_name="detect_ras_candidates",
            ok=True,
            output={"candidate_piece_count": 3},
        )
    )

    assert event is not None
    assert event.status == "detected"
    assert event.message == "3 candidat(s) ont un identifiant de revue opaque."


def test_ras_workflow_stops_after_report_or_failed_assessment() -> None:
    request = AgentRunRequest(
        user_message="Audite la RAS.",
        file_path=Path("ledger.xlsx"),
        sheet_name="GL",
        allowed_tools=(
            "run_ras_audit_batch",
            "assess_ras_accounting",
            "generate_ras_audit_report",
        ),
    )
    batch = ToolExecutionResult(
        tool_name="run_ras_audit_batch",
        ok=True,
        output={
            "audit_id": "audit-1",
            "review_candidate_ids": ["candidate-1"],
            "remaining_candidate_count": 0,
        },
    )
    failed = ToolExecutionResult(
        tool_name="assess_ras_accounting",
        ok=False,
        output={},
        error_code="ras_fact_context_required",
        error_message="safe failure",
    )
    report = ToolExecutionResult(
        tool_name="generate_ras_audit_report",
        ok=True,
        output={"audit_id": "audit-2", "report_id": "report-1"},
    )

    assert _next_ras_workflow_call((batch, failed), request) is None
    assert _next_ras_workflow_call((batch, report), request) is None


def test_orchestrator_executes_single_candidate_workflow_to_report() -> None:
    executor = WorkflowToolExecutor()
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(ToolCall(name="run_ras_audit_batch", arguments={}),),
            ),
            ModelResponse(
                text="Rapport prepare.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        )
    )
    orchestrator = AgentOrchestrator(model_provider=model, tool_executor=executor)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Audite la RAS.",
            file_path=Path("ledger.xlsx"),
            sheet_name="GL",
            allowed_tools=(
                "run_ras_audit_batch",
                "assess_ras_accounting",
                "generate_ras_audit_report",
            ),
        )
    )

    assert [call.name for call in executor.calls] == [
        "run_ras_audit_batch",
        "assess_ras_accounting",
        "generate_ras_audit_report",
    ]
    assert executor.calls[1].arguments["base_audit_id"] == "audit-1"
    assert executor.calls[1].arguments["candidate_id"] == "candidate-1"
    assert executor.calls[2].arguments == {"audit_id": "audit-2"}
    assert [result.tool_name for result in result.tool_results] == [
        "run_ras_audit_batch",
        "assess_ras_accounting",
        "generate_ras_audit_report",
    ]
    assert sum(
        event.event_type == "workflow_transition"
        for event in result.execution_events
    ) == 2
    assert [
        event.status
        for event in result.execution_events
        if event.event_type == "workflow_state_changed"
    ] == ["awaiting_facts", "blocked", "reported"]


def test_orchestrator_hides_ras_column_mapping_from_model_schema(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="Precise le perimetre RAS a analyser.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    orchestrator.run(
        AgentRunRequest(
            user_message="Detecte les candidats RAS.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("detect_ras_candidates",),
        ),
    )

    schema = model.requests[0].tool_definitions[0].input_schema
    assert "column_mapping" not in schema.get("properties", {})
    assert "filters" in schema.get("properties", {})


def test_orchestrator_exposes_accounting_entry_selector_to_model(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="Je ne retrouve pas la piece demandee.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    orchestrator.run(
        AgentRunRequest(
            user_message="Reconstitue la piece 2024002341 de l'exercice 2024.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("reconstruct_accounting_entry",),
        ),
    )

    schema = model.requests[0].tool_definitions[0].input_schema
    properties = schema.get("properties", {})
    assert "file_path" not in properties
    assert "sheet_name" not in properties
    assert "column_mapping" not in properties
    assert "entry_selector" in properties


def test_orchestrator_hides_counterpart_column_mapping_from_model_schema(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="Recherche impossible sans donnees.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    orchestrator.run(
        AgentRunRequest(
            user_message="Cherche les contreparties RAS dans la meme piece.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("find_ras_counterpart",),
        ),
    )

    schema = model.requests[0].tool_definitions[0].input_schema
    properties = schema.get("properties", {})
    assert "file_path" not in properties
    assert "sheet_name" not in properties
    assert "column_mapping" not in properties
    assert "related_window_days" in properties


def test_final_context_keeps_selected_accounting_entry_details() -> None:
    result = ToolExecutionResult(
        tool_name="reconstruct_accounting_entry",
        ok=True,
        output={
            "sheet_name": "Sheet1",
            "row_count": 2500,
            "entry_count": 2205,
            "selector": {
                "document_number": "2024002341",
                "fiscal_year": 2024,
            },
            "selected_entry_found": True,
            "selected_entry": {
                "key": {
                    "fiscal_year": 2024,
                    "journal": "KR",
                    "document_number": "2024002341",
                },
                "line_count": 2,
                "balances": [{"currency": "XOF", "difference": "533360"}],
                "lines": [
                    {
                        "account": "61365000",
                        "posting_key": "40",
                        "amount": "452000",
                        "currency": "XOF",
                    },
                ],
            },
        },
    )

    compact = _compact_tool_output(result)

    selector = compact["selector"]
    selected_entry = compact["selected_entry"]
    assert isinstance(selector, dict)
    assert isinstance(selected_entry, dict)
    assert selector["document_number"] == "2024002341"
    assert compact["selected_entry_found"] is True
    assert selected_entry["line_count"] == 2
    lines = selected_entry["lines"]
    assert isinstance(lines, list)
    assert isinstance(lines[0], dict)
    assert lines[0]["account"] == "61365000"


def test_ras_counterpart_answer_hides_technical_scope_details() -> None:
    result = ToolExecutionResult(
        tool_name="find_ras_counterpart",
        ok=True,
        output={
            "detected_candidate_piece_count": 611,
            "candidate_piece_count": 518,
            "counterpart_scope_exclusion_count": 93,
            "counterpart_scope_basis": (
                "Pieces avec au moins une ligne de charge candidate mappee."
            ),
            "status_counts": {
                "found_in_same_entry": 59,
                "potential_related_entry": 0,
                "not_found_in_scope": 0,
                "indeterminate": 459,
            },
            "confirmed_amounts_by_currency": {"XOF": "1693625"},
            "missing_fact_counts": {"company_code": 459, "partner_id": 84},
            "source_scope_complete": False,
            "source_scope_blockers": ["missing_company_scope"],
        },
    )

    answer = _deterministic_tool_results_answer((result,))

    assert "Candidats detectes au sens large : 611" in answer
    assert "Pieces analysees pour contrepartie : 518" in answer
    assert "Hors scope rapprochement : 93" in answer
    assert "RAS trouvee dans la meme piece : 59" in answer
    assert "1693625 XOF" in answer
    assert "source_scope_complete" not in answer
    assert "missing_company_scope" not in answer
    assert "Périmètre technique complet" not in answer
    assert "Blocages" not in answer


def test_tax_rag_tool_is_selected_by_model_and_final_answer_comes_from_model(
    tmp_path: Path,
) -> None:
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="query_tax_rag",
                        arguments={
                            "query": "RAS prestataires residents",
                            "limit": 2,
                        },
                    ),
                ),
            ),
            ModelResponse(
                text="Reponse sourcee redigee par le modele a partir du RAG.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        )
    )
    orchestrator = AgentOrchestrator(
        model_provider=model,
        tool_executor=ExcelToolExecutor(
            tools=ExcelAgentTools(allowed_root=tmp_path),
            registry=create_excel_tool_registry(),
            tax_rag_query_service=TaxRagQueryService(
                Path("../docs/source-corpus/fiscal")
            ),
        ),
    )

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Que dit le CGI sur la RAS des prestataires residents ?",
            file_path=None,
            sheet_name=None,
            allowed_tools=("query_tax_rag",),
        )
    )

    assert [tool_result.tool_name for tool_result in result.tool_results] == [
        "query_tax_rag",
    ]
    assert result.answer == "Reponse sourcee redigee par le modele a partir du RAG."
    assert model.calls == 2
    assert model.requests[0].allowed_tools == ("query_tax_rag",)
    assert model.requests[1].allowed_tools == ()
    assert (
        "Que dit le CGI sur la RAS des prestataires residents ?"
        in model.requests[1].messages[1].content
    )
    assert "commence par une reponse directe" in model.requests[1].messages[0].content


def test_orchestrator_routes_explicit_dated_ras_calculation_end_to_end(
    tmp_path: Path,
) -> None:
    message = (
        "Le prestataire résident est un prestataire immatriculé à l'IFU. "
        "Il s'agit d'une prestation de services, avec un payeur éligible à la "
        "retenue sur prestations et un service utilisé au Burkina Faso. "
        "Aucune exonération applicable. L'assiette fiscale est de 100 000 XOF. "
        "Le paiement effectué le 2026-04-10. Calcule la RAS."
    )
    message += " Reference partenaire SECRET-PARTENAIRE-42."
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="calculate_theoretical_ras",
                        arguments={"transaction_date": "2026-04-10"},
                    ),
                ),
            ),
            ModelResponse(
                text="RAS theorique calculee par le tool : 5000 XOF.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="calculate_theoretical_ras",
                        arguments={"transaction_date": "2026-04-10"},
                    ),
                ),
            ),
            ModelResponse(
                text="Calcul non possible : faits fiscaux insuffisants.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        )
    )
    attestor = RasFactContextAttestor("test-signing-key-with-at-least-32-bytes")
    orchestrator = AgentOrchestrator(
        model_provider=model,
        tool_executor=ExcelToolExecutor(
            tools=ExcelAgentTools(allowed_root=tmp_path),
            registry=create_excel_tool_registry(),
            ras_legal_rules=load_ras_legal_rules(
                ROOT / "docs/reference/bf-ras-legal-rules.csv",
                repository_root=ROOT,
            ),
            ras_tax_event_rules=load_ras_tax_event_rules(
                ROOT / "docs/reference/bf-ras-tax-event-rules.csv",
                repository_root=ROOT,
            ),
            ras_calculation_parameters=load_ras_calculation_parameters(
                ROOT / "docs/reference/bf-ras-calculation-parameters.csv",
                repository_root=ROOT,
            ),
            ras_fact_context_attestor=attestor,
        ),
        ras_fact_extractor=RasExplicitFactExtractor(
            load_ras_user_fact_patterns(
                ROOT / "docs/reference/ras-user-fact-patterns.csv"
            )
        ),
        ras_fact_attestor=attestor,
    )

    result = orchestrator.run(
        AgentRunRequest(
            user_message=message,
            file_path=None,
            sheet_name=None,
            allowed_tools=("calculate_theoretical_ras",),
            session_id="session-1",
        )
    )

    assert model.calls == 2
    assert len(result.tool_results) == 1
    assert result.tool_results[0].ok is True
    assert result.tool_results[0].output["calculation_status"] == (
        "calculated_provisional"
    )
    assert result.tool_results[0].output["expected_amount"] == "5000"
    assert result.tool_results[0].output["currency"] == "XOF"
    assert result.answer == "RAS theorique calculee par le tool : 5000 XOF."
    assert "SECRET-PARTENAIRE-42" not in repr(model.requests[1:])
    assert "SECRET-PARTENAIRE-42" not in repr(result.tool_results)

    incomplete = orchestrator.run(
        AgentRunRequest(
            user_message="Calcule la RAS, paiement effectué le 2026-04-10.",
            file_path=None,
            sheet_name=None,
            allowed_tools=("calculate_theoretical_ras",),
            session_id="session-1",
        )
    )

    assert model.calls == 4
    assert incomplete.tool_results[0].output["calculation_status"] == (
        "not_calculable"
    )
    assert incomplete.answer == "Calcul non possible : faits fiscaux insuffisants."


def test_orchestrator_executes_excel_tool_then_requests_final_answer(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="profile_sheet",
                        arguments={
                            "file_path": str(workbook_path),
                            "sheet_name": "Grand Livre",
                        },
                    ),
                ),
            ),
            ModelResponse(
                text="Le fichier contient 4 lignes et 5 colonnes.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Profile ce Grand Livre.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == "Le fichier contient 4 lignes et 5 colonnes."
    assert result.tool_results[0].ok is True
    assert result.tool_results[0].output["row_count"] == 4
    assert result.provider_name == "fake"
    assert result.model_name == "fake-model"
    assert [event.event_type for event in result.execution_events] == [
        "run_started",
        "file_checked",
        "model_requested",
        "tool_requested",
        "tool_started",
        "tool_finished",
        "model_requested",
        "answer_ready",
    ]
    assert result.execution_events[3].message == ("Analyse de la feuille Excel prête.")
    assert result.execution_events[5].message == (
        "L'analyse de la feuille Excel est terminée: 4 lignes, 5 colonnes."
    )
    assert model.calls == 2
    assert model.requests[0].tool_definitions
    assert model.requests[0].tool_definitions[0].name == "profile_sheet"
    assert model.requests[0].tool_definitions[0].input_schema["type"] == "object"
    assert model.requests[1].messages[-1].role == "user"
    assert "row_count" in model.requests[1].messages[-1].content


def test_orchestrator_returns_deterministic_answer_when_final_model_is_internal(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="profile_sheet",
                        arguments={
                            "file_path": str(workbook_path),
                            "sheet_name": "Grand Livre",
                        },
                    ),
                ),
            ),
            ModelResponse(
                text=(
                    "Les contrôles déterministes sont disponibles. "
                    "Ajoutez un fichier Excel pour lancer une analyse structurée."
                ),
                provider_name="internal",
                model_name="controlled-response",
                finish_reason="controlled_response",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Profile ce Grand Livre.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == (
        "Analyse de la feuille Excel terminée: 4 lignes, 5 colonnes."
    )
    assert result.tool_results[0].ok is True
    assert result.provider_name == "internal"
    assert result.model_name == "controlled-response"
    assert model.calls == 2


def test_orchestrator_routes_generic_excel_analysis_before_model_call(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="Les contrôles déterministes sont disponibles.",
                provider_name="internal",
                model_name="controlled-response",
                finish_reason="controlled_response",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Analyse ce fichier Excel.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("list_sheets", "profile_sheet", "analyze_ledger"),
        ),
    )

    assert result.answer == (
        "Analyse du Grand Livre terminée: 4 lignes, 5 colonnes.\n\n"
        "Colonnes requises disponibles."
    )
    assert [tool.tool_name for tool in result.tool_results] == ["analyze_ledger"]
    assert result.provider_name == "internal"
    assert result.model_name == "controlled-response"
    assert [event.event_type for event in result.execution_events] == [
        "run_started",
        "file_checked",
        "tool_requested",
        "tool_started",
        "tool_finished",
        "model_requested",
        "answer_ready",
    ]
    assert model.calls == 1


def test_orchestrator_routes_data_quality_before_model_call(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="detect_data_quality_issues",
                        arguments={},
                    ),
                ),
            ),
            ModelResponse(
                text="Des points de qualité sont à vérifier.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Vérifie la qualité des données du Grand Livre.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=(
                "analyze_ledger",
                "detect_data_quality_issues",
                "detect_tax_candidates",
            ),
        ),
    )

    assert [tool_result.tool_name for tool_result in result.tool_results] == [
        "detect_data_quality_issues",
    ]
    assert model.calls == 2
    assert model.requests[0].allowed_tools == (
        "analyze_ledger",
        "detect_data_quality_issues",
        "detect_tax_candidates",
    )
    tool_schema = model.requests[0].tool_definitions[0].input_schema
    assert "file_path" not in tool_schema.get("properties", {})
    assert "sheet_name" not in tool_schema.get("properties", {})
    assert model.requests[1].allowed_tools == ()
    assert "detect_data_quality_issues" in model.requests[1].messages[-1].content
    assert [event.event_type for event in result.execution_events] == [
        "run_started",
        "file_checked",
        "model_requested",
        "tool_requested",
        "tool_started",
        "tool_finished",
        "model_requested",
        "answer_ready",
    ]


def test_orchestrator_routes_tax_candidates_before_model_call(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="detect_tax_candidates",
                        arguments={},
                    ),
                ),
            ),
            ModelResponse(
                text="Les candidats fiscaux doivent être revus par le métier.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Détecte les candidats RAS à confirmer.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=(
                "detect_data_quality_issues",
                "detect_tax_candidates",
            ),
        ),
    )

    assert [tool_result.tool_name for tool_result in result.tool_results] == [
        "detect_tax_candidates",
    ]
    assert result.tool_results[0].output["decision_status"] == "review_required"
    assert model.calls == 2
    assert model.requests[0].allowed_tools == (
        "detect_data_quality_issues",
        "detect_tax_candidates",
    )
    assert model.requests[1].allowed_tools == ()


def test_orchestrator_routes_account_question_to_ledger_query(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="query_ledger_entries",
                        arguments={"filters": {"account": "44585100"}},
                    ),
                ),
            ),
            ModelResponse(
                text="Aucune écriture trouvée pour ce compte.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Montre-moi toutes les écritures du compte 44585100.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("query_ledger_entries",),
        ),
    )

    assert [tool_result.tool_name for tool_result in result.tool_results] == [
        "query_ledger_entries",
    ]
    assert result.tool_results[0].output["total_matches"] == 0
    assert result.tool_results[0].output["message"] == (
        "Aucune écriture ne correspond aux filtres fournis."
    )
    assert model.calls == 2
    assert model.requests[0].allowed_tools == ("query_ledger_entries",)
    assert model.requests[1].allowed_tools == ()
    assert "44585100" in model.requests[1].messages[-1].content


def test_orchestrator_renders_ledger_query_without_llm_narration(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="query_ledger_entries",
                        arguments={"filters": {"account": "601000"}},
                    ),
                ),
            ),
            ModelResponse(
                text="Les contrôles déterministes sont terminés.",
                provider_name="internal",
                model_name="controlled-response",
                finish_reason="controlled_response",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Montre-moi les ecritures du compte 601000.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("query_ledger_entries",),
        ),
    )

    assert [tool_result.tool_name for tool_result in result.tool_results] == [
        "query_ledger_entries",
    ]
    assert "Ecritures comptables" in result.answer
    assert "Correspondances : 1" in result.answer
    assert "| 601000 |" in result.answer
    assert "Les controles deterministes sont termines" not in result.answer
    assert model.calls == 2


def test_orchestrator_warns_on_prefix_only_account_query(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="query_ledger_entries",
                        arguments={"filters": {"account": "601"}},
                    ),
                ),
            ),
            ModelResponse(
                text="Les contrôles déterministes sont terminés.",
                provider_name="internal",
                model_name="controlled-response",
                finish_reason="controlled_response",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Montre-moi les ecritures du compte 601.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("query_ledger_entries",),
        ),
    )

    assert "Alerte filtre" in result.answer
    assert "Aucun compte exact 601" in result.answer
    assert "601000" in result.answer
    assert model.calls == 2


def test_orchestrator_asks_for_precision_on_ambiguous_total_question(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text=(
                    "La demande est trop ambigue: precise la metrique "
                    "(somme brute, debit, credit ou solde), le perimetre "
                    "et la devise."
                ),
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Quel est le total ?",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("analyze_ledger", "calculate_ledger_metrics"),
        ),
    )

    assert result.tool_results == ()
    assert result.provider_name == "fake"
    assert result.model_name == "fake-model"
    assert "demande est trop ambigue" in result.answer
    assert "somme brute" in result.answer
    assert model.calls == 1


def test_orchestrator_routes_general_excel_explanation_to_analysis_tools(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="Le fichier est un Grand Livre de 4 lignes avec des contrôles.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Explique-moi cet Excel.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=(
                "list_sheets",
                "analyze_ledger",
                "calculate_ledger_metrics",
                "aggregate_ledger",
                "detect_data_quality_issues",
                "detect_tax_candidates",
            ),
        ),
    )

    assert [tool_result.tool_name for tool_result in result.tool_results] == [
        "analyze_ledger",
        "calculate_ledger_metrics",
        "aggregate_ledger",
        "detect_data_quality_issues",
        "detect_tax_candidates",
    ]
    assert model.calls == 1
    final_context = model.requests[0].messages[-1].content
    assert "analyze_ledger" in final_context
    assert "calculate_ledger_metrics" in final_context
    assert "aggregate_ledger" in final_context
    assert model.requests[0].allowed_tools == ()
    assert result.answer.startswith("**Vue synthétique du Grand Livre**")
    assert "Solde global" not in result.answer


def test_orchestrator_explains_file_with_deterministic_answer_when_model_is_internal(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text=(
                    "Les contrôles déterministes sont disponibles. "
                    "Ajoutez un fichier Excel pour lancer une analyse structurée."
                ),
                provider_name="internal",
                model_name="controlled-response",
                finish_reason="controlled_response",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Explique-moi ce fichier Grand Livre.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("analyze_ledger",),
        ),
    )

    assert [tool_result.tool_name for tool_result in result.tool_results] == [
        "analyze_ledger",
    ]
    assert result.answer == (
        "Analyse du Grand Livre terminée: 4 lignes, 5 colonnes.\n\n"
        "Colonnes requises disponibles."
    )
    assert model.calls == 1


def test_orchestrator_uses_deterministic_file_overview_when_model_is_truncated(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="Ce fichier contient des comptes principaux dont",
                provider_name="gemini",
                model_name="gemini-test",
                finish_reason="MAX_TOKENS",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Explique-moi ce fichier Grand Livre.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=(
                "analyze_ledger",
                "calculate_ledger_metrics",
                "aggregate_ledger",
                "detect_data_quality_issues",
                "detect_tax_candidates",
            ),
        ),
    )

    assert result.answer.startswith("**Vue synthétique du Grand Livre**")
    assert "Ce fichier contient des comptes principaux dont" not in result.answer
    assert "Comptes principaux" in result.answer
    assert "Qualité des données" in result.answer
    assert "Signaux fiscaux à revoir" in result.answer
    assert model.calls == 1


def test_file_overview_does_not_display_global_amount_metrics() -> None:
    lines = _file_metric_lines(
        ToolExecutionResult(
            tool_name="calculate_ledger_metrics",
            ok=True,
            output={
                "metrics": {
                    "sum": -9_522_740,
                    "average": -3_809.096,
                    "min": -565_000,
                    "max": 500_000,
                },
                "metrics_by_currency": {"XOF": {}},
            },
        )
    )

    assert lines == []


def test_ras_candidate_detection_answer_translates_codes_and_hides_scope() -> None:
    result = ToolExecutionResult(
        tool_name="detect_ras_candidates",
        ok=True,
        output={
            "row_count": 3010,
            "evaluated_piece_count": 100,
            "candidate_piece_count": 43,
            "status_counts": {
                "candidate_text_only": 17,
                "candidate_account_only": 4,
                "candidate_account_and_text": 22,
            },
            "candidate_amounts_by_currency": {"XOF": "1250000"},
            "missing_fact_counts": {"strong_semantic_signal": 27},
            "source_scope_complete": False,
            "source_scope_blockers": [
                "journal_is_document_type_proxy",
                "missing_company_scope",
                "posting_date_is_document_date_proxy",
            ],
            "decision_status": "review_only_no_tax_conclusion",
        },
    )

    answer = _deterministic_tool_results_answer((result,))

    assert "Libellé uniquement : 17" in answer
    assert "Compte uniquement : 4" in answer
    assert "Compte et libellé concordants : 22" in answer
    assert "Signal sémantique fort à confirmer : 27" in answer
    assert "candidate_" not in answer
    assert "strong_semantic_signal" not in answer
    assert "source_scope_complete" not in answer
    assert "journal_is_document_type_proxy" not in answer
    assert "Bloqueurs" not in answer


def test_tax_candidate_summary_is_french_and_actionable() -> None:
    lines = _file_tax_candidate_lines(
        ToolExecutionResult(
            tool_name="detect_tax_candidates",
            ok=True,
            output={
                "candidates": [
                    {
                        "category": "resident_services",
                        "entry_count": 227,
                        "amount_sum": 61_173_000,
                        "amounts_by_currency": {"XOF": 61_173_000},
                        "matched_keywords": ["honoraire", "conseil"],
                        "top_accounts": [
                            {
                                "key": "61365000",
                                "entry_count": 227,
                                "amount_sum": 61_173_000,
                            }
                        ],
                        "action_required": "Verifier IFU et seuil facture.",
                    }
                ]
            },
        )
    )
    answer = "\n".join(lines)

    assert "Prestations de services à des résidents" in answer
    assert "resident_services" not in answer
    assert "Volume : 227 écriture(s)" in answer
    assert "Montant repéré : 61 173 000.00 XOF" in answer
    assert "Preuves disponibles" in answer
    assert "honoraire" in answer
    assert "61365000" in answer
    assert "À vérifier : Verifier IFU et seuil facture." in answer


def test_orchestrator_routes_column_role_question_to_schema_classification(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text=(
                    "Les contrôles déterministes sont disponibles. "
                    "Ajoutez un fichier Excel pour lancer une analyse structurée."
                ),
                provider_name="internal",
                model_name="controlled-response",
                finish_reason="controlled_response",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Quelles sont les colonnes détectées et leur rôle ?",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("get_columns", "classify_ledger_schema"),
        ),
    )

    assert [tool_result.tool_name for tool_result in result.tool_results] == [
        "classify_ledger_schema",
    ]
    assert result.answer.startswith("**Colonnes détectées et rôles probables**")
    assert "| # | Colonne | Rôle | Type | Complétude |" in result.answer
    assert "Compte comptable" in result.answer
    assert "Montant" in result.answer
    assert model.calls == 1


def test_orchestrator_refuses_disallowed_tool_call(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="delete_file",
                        arguments={"file_path": str(workbook_path)},
                    ),
                ),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Supprime le fichier.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == "Le tool call a ete refuse par les garde-fous."
    assert result.tool_results[0].ok is False
    assert result.tool_results[0].error_code == "tool_not_allowed"
    assert result.provider_name == "fake"
    assert result.model_name == "fake-model"
    assert model.calls == 1


def test_orchestrator_refuses_invalid_tool_arguments(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="profile_sheet",
                        arguments={"file_path": str(workbook_path)},
                    ),
                ),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Profile ce Grand Livre.",
            file_path=workbook_path,
            sheet_name=None,
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == "Le tool call a ete refuse par les garde-fous."
    assert result.tool_results[0].ok is False
    assert result.tool_results[0].error_code == "invalid_tool_call"
    assert "sheet_name" in str(result.tool_results[0].error_message)
    assert result.provider_name == "fake"
    assert result.model_name == "fake-model"
    assert model.calls == 1


def test_orchestrator_injects_request_file_and_sheet_into_tool_call(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="profile_sheet",
                        arguments={},
                    ),
                ),
            ),
            ModelResponse(
                text="Analyse prête.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Profile ce Grand Livre.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == "Analyse prête."
    assert result.tool_results[0].ok is True
    assert result.tool_results[0].output["sheet_name"] == "Grand Livre"


def test_orchestrator_limits_tool_calls(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        name="list_sheets",
                        arguments={"file_path": str(workbook_path)},
                    ),
                    ToolCall(
                        name="profile_sheet",
                        arguments={
                            "file_path": str(workbook_path),
                            "sheet_name": "Grand Livre",
                        },
                    ),
                ),
            ),
            ModelResponse(
                text="Premier tool execute seulement.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    orchestrator = AgentOrchestrator(
        model_provider=model,
        tool_executor=ExcelToolExecutor(
            tools=ExcelAgentTools(allowed_root=tmp_path),
            registry=create_excel_tool_registry(),
        ),
        max_tool_calls=1,
    )

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Analyse le fichier.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("list_sheets", "profile_sheet"),
        ),
    )

    assert len(result.tool_results) == 1
    assert result.tool_results[0].tool_name == "list_sheets"


def test_orchestrator_uses_model_fallback(tmp_path: Path) -> None:
    fallback_model = FallbackModelProvider(
        (
            FakeModelProvider(error=ModelProviderError()),
            FakeModelProvider(
                responses=(
                    ModelResponse(
                        text="Reponse du modele fallback.",
                        provider_name="secondary",
                        model_name="model-b",
                        finish_reason="stop",
                        tool_calls=(),
                    ),
                ),
            ),
        ),
    )
    orchestrator = _create_orchestrator(tmp_path, fallback_model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Analyse le fichier.",
            file_path=None,
            sheet_name=None,
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == "Reponse du modele fallback."
    assert result.provider_name == "secondary"
    assert result.model_name == "model-b"
    assert "fallback_used" in [event.event_type for event in result.execution_events]


def test_orchestrator_returns_internal_model_for_direct_tool_call(
    tmp_path: Path,
) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider()
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Analyse deterministe.",
            file_path=workbook_path,
            sheet_name="Grand Livre",
            allowed_tools=("profile_sheet",),
            direct_tool_call=ToolCall(
                name="profile_sheet",
                arguments={
                    "file_path": str(workbook_path),
                    "sheet_name": "Grand Livre",
                },
            ),
        ),
    )

    assert result.answer == (
        "Analyse de la feuille Excel terminée: 4 lignes, 5 colonnes."
    )
    assert result.tool_results[0].ok is True
    assert result.provider_name == "internal"
    assert result.model_name == "direct-tool-call"
    assert [event.event_type for event in result.execution_events] == [
        "run_started",
        "file_checked",
        "tool_started",
        "tool_finished",
        "answer_ready",
    ]
    assert model.calls == 0


def test_orchestrator_emits_safe_user_facing_events(tmp_path: Path) -> None:
    secret_path = tmp_path / "secret-client.xlsx"
    model = FakeModelProvider(
        responses=(
            ModelResponse(
                text="Analyse prête.",
                provider_name="fake",
                model_name="fake-model",
                finish_reason="stop",
                tool_calls=(),
            ),
        ),
    )
    emitted_events: list[AgentRunEvent] = []
    orchestrator = _create_orchestrator(tmp_path, model)

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Analyse /secret/client.xlsx",
            file_path=secret_path,
            sheet_name="Client Confidentiel 2025",
            allowed_tools=("profile_sheet",),
        ),
        event_sink=emitted_events.append,
    )

    serialized_events = repr(result.execution_events)
    serialized_model_requests = repr(model.requests)
    assert emitted_events == list(result.execution_events)
    assert "/secret/client.xlsx" not in serialized_events
    assert str(secret_path) not in serialized_events
    assert str(secret_path) not in serialized_model_requests
    assert "Client Confidentiel 2025" not in serialized_model_requests


def test_orchestrator_blocks_direct_tax_decision_in_answer(tmp_path: Path) -> None:
    orchestrator = _create_orchestrator(
        tmp_path,
        FakeModelProvider(
            responses=(
                ModelResponse(
                    text="Decision: soumisRas=true avec taux RAS 12.5%.",
                    provider_name="fake",
                    model_name="fake-model",
                    finish_reason="stop",
                    tool_calls=(),
                ),
            ),
        ),
    )

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Ce compte est-il soumis a la RAS ?",
            file_path=None,
            sheet_name=None,
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == (
        "La reponse du modele a ete bloquee: seule une explication appuyee "
        "sur les controles deterministes est autorisee."
    )


def test_orchestrator_blocks_oversized_answer(tmp_path: Path) -> None:
    orchestrator = AgentOrchestrator(
        model_provider=FakeModelProvider(
            responses=(
                ModelResponse(
                    text="x" * 51,
                    provider_name="fake",
                    model_name="fake-model",
                    finish_reason="stop",
                    tool_calls=(),
                ),
            ),
        ),
        tool_executor=ExcelToolExecutor(
            tools=ExcelAgentTools(allowed_root=tmp_path),
            registry=create_excel_tool_registry(),
        ),
        max_answer_characters=50,
    )

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Resume.",
            file_path=None,
            sheet_name=None,
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == "La reponse du modele est trop longue pour etre retournee."


def test_orchestrator_blocks_run_when_global_timeout_is_exceeded(
    tmp_path: Path,
) -> None:
    orchestrator = AgentOrchestrator(
        model_provider=FakeModelProvider(
            responses=(
                ModelResponse(
                    text="Reponse arrivee trop tard.",
                    provider_name="fake",
                    model_name="fake-model",
                    finish_reason="stop",
                    tool_calls=(),
                ),
            ),
        ),
        tool_executor=ExcelToolExecutor(
            tools=ExcelAgentTools(allowed_root=tmp_path),
            registry=create_excel_tool_registry(),
        ),
        max_run_seconds=1.0,
        monotonic=FakeClock((10.0, 12.0)),
    )

    result = orchestrator.run(
        AgentRunRequest(
            user_message="Analyse le fichier.",
            file_path=None,
            sheet_name=None,
            allowed_tools=("profile_sheet",),
        ),
    )

    assert result.answer == "L'execution agent a depasse le temps autorise."
    assert result.tool_results == ()


def _create_orchestrator(
    allowed_root: Path,
    model_provider: ModelProvider,
) -> AgentOrchestrator:
    return AgentOrchestrator(
        model_provider=model_provider,
        tool_executor=ExcelToolExecutor(
            tools=ExcelAgentTools(allowed_root=allowed_root),
            registry=create_excel_tool_registry(),
        ),
    )


class WorkflowToolExecutor:
    def __init__(self) -> None:
        self.calls: list[ToolCall] = []

    def get_model_tool_definitions(
        self,
        allowed_tools: tuple[str, ...],
    ) -> tuple[ModelToolDefinition, ...]:
        return ()

    def execute(
        self,
        tool_call: ToolCall,
        *,
        ras_fact_context_token: str | None = None,
    ) -> ToolExecutionResult:
        self.calls.append(tool_call)
        if tool_call.name == "run_ras_audit_batch":
            return ToolExecutionResult(
                tool_name=tool_call.name,
                ok=True,
                output={
                    "audit_id": "audit-1",
                    "review_candidate_ids": ["candidate-1"],
                    "remaining_candidate_count": 0,
                },
            )
        if tool_call.name == "assess_ras_accounting":
            return ToolExecutionResult(
                tool_name=tool_call.name,
                ok=True,
                output={"audit_id": "audit-2", "missing_facts": []},
            )
        if tool_call.name == "generate_ras_audit_report":
            return ToolExecutionResult(
                tool_name=tool_call.name,
                ok=True,
                output={
                    "audit_id": "audit-2",
                    "report_id": "report-1",
                    "case_count": 1,
                    "status_counts": {"ras_accounted_compliant": 1},
                    "certainty_counts": {"supported_provisional": 1},
                    "amount_summaries": [],
                    "recorded_amount_summaries": [],
                    "reference_versions": ["rules-v1"],
                },
            )
        raise AssertionError(f"unexpected tool call: {tool_call.name}")


class FakeModelProvider:
    provider_name = "fake"

    def __init__(
        self,
        responses: tuple[ModelResponse, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self._responses = list(responses)
        self._error = error
        self.calls = 0
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        if not self._responses:
            raise AssertionError("fake response is required")
        return self._responses.pop(0)


class FakeClock:
    def __init__(self, values: tuple[float, ...]) -> None:
        self._values = list(values)

    def __call__(self) -> float:
        return self._values.pop(0)
