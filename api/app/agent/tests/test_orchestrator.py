from pathlib import Path

from app.agent.orchestrator import AgentOrchestrator, AgentRunEvent, AgentRunRequest
from app.excel_agent.excel_tools import ExcelAgentTools
from app.excel_agent.tests.fixtures import write_minified_grand_livre
from app.excel_agent.tool_executor import ExcelToolExecutor
from app.excel_agent.tool_registry import create_excel_tool_registry
from app.llm.domain import (
    ModelProvider,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ToolCall,
)
from app.llm.fallback_model import FallbackModelProvider


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
    assert result.execution_events[3].message == (
        "Analyse de la feuille Excel prête."
    )
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


def test_orchestrator_runs_default_excel_analysis_when_model_skips_tool_call(
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
    assert result.tool_results[0].ok is True
    assert result.tool_results[0].tool_name == "analyze_ledger"
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
    assert model.calls == 1
    assert model.requests[0].allowed_tools == ()
    assert "detect_data_quality_issues" in model.requests[0].messages[-1].content
    assert [event.event_type for event in result.execution_events] == [
        "run_started",
        "file_checked",
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
    assert model.calls == 1
    assert model.requests[0].allowed_tools == ()


def test_orchestrator_routes_account_question_to_ledger_query(tmp_path: Path) -> None:
    workbook_path = write_minified_grand_livre(tmp_path)
    model = FakeModelProvider(
        responses=(
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
    assert model.calls == 1
    assert model.requests[0].allowed_tools == ()
    assert "44585100" in model.requests[0].messages[-1].content


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
    assert result.answer == (
        "Le fichier est un Grand Livre de 4 lignes avec des contrôles."
    )


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

    assert result.answer == "L'analyse déterministe du Grand Livre est terminée."
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
            sheet_name="Grand Livre",
            allowed_tools=("profile_sheet",),
        ),
        event_sink=emitted_events.append,
    )

    serialized_events = repr(result.execution_events)
    assert emitted_events == list(result.execution_events)
    assert "/secret/client.xlsx" not in serialized_events
    assert str(secret_path) not in serialized_events


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
