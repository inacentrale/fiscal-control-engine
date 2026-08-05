import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Protocol

from app.agent.answer_policy import AgentAnswerPolicy
from app.agent.constants import AGENT_RUN_TIMEOUT_ANSWER
from app.excel_agent.domain import ToolExecutionResult
from app.excel_agent.tool_executor import ExcelToolExecutor
from app.llm.domain import (
    ModelMessage,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelToolDefinition,
    ToolCall,
)
from app.ras_audit.fact_context import (
    RasExplicitFactExtractor,
    RasFactContextAttestor,
)


@dataclass(frozen=True)
class AgentRunEvent:
    event_type: str
    title: str
    message: str
    status: str
    tool_name: str | None = None
    provider_name: str | None = None
    model_name: str | None = None


@dataclass(frozen=True)
class AgentRunRequest:
    user_message: str
    file_path: Path | None
    sheet_name: str | None
    allowed_tools: tuple[str, ...]
    direct_tool_call: ToolCall | None = None
    session_id: str | None = None
    file_id: str | None = None


@dataclass(frozen=True)
class AgentRunResult:
    answer: str
    provider_name: str
    model_name: str
    execution_events: tuple[AgentRunEvent, ...]
    tool_results: tuple[ToolExecutionResult, ...]


class ToolExecutor(Protocol):
    def execute(self, tool_call: ToolCall) -> ToolExecutionResult:
        pass


class AgentOrchestrator:
    def __init__(
        self,
        model_provider: ModelProvider,
        tool_executor: ExcelToolExecutor,
        max_tool_calls: int = 5,
        max_answer_characters: int = 4_000,
        max_run_seconds: float = 60.0,
        monotonic: Callable[[], float] = monotonic,
        ras_fact_extractor: RasExplicitFactExtractor | None = None,
        ras_fact_attestor: RasFactContextAttestor | None = None,
    ) -> None:
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be positive")
        if max_run_seconds <= 0:
            raise ValueError("max_run_seconds must be positive")
        self._model_provider = model_provider
        self._tool_executor = tool_executor
        self._max_tool_calls = max_tool_calls
        self._max_run_seconds = max_run_seconds
        self._monotonic = monotonic
        self._answer_policy = AgentAnswerPolicy(
            max_answer_characters=max_answer_characters,
        )
        self._ras_fact_extractor = ras_fact_extractor
        self._ras_fact_attestor = ras_fact_attestor

    def run(
        self,
        request: AgentRunRequest,
        event_sink: Callable[[AgentRunEvent], None] | None = None,
    ) -> AgentRunResult:
        started_at = self._monotonic()
        events: list[AgentRunEvent] = []

        def emit(event: AgentRunEvent) -> None:
            events.append(event)
            if event_sink is not None:
                event_sink(event)

        emit(
            AgentRunEvent(
                event_type="run_started",
                title="Demande reçue",
                message="Demande prise en compte.",
                status="completed",
            ),
        )
        if request.file_path is not None:
            emit(
                AgentRunEvent(
                    event_type="file_checked",
                    title="Fichier disponible",
                    message="Fichier prêt pour l'analyse.",
                    status="completed",
                ),
            )
        if request.direct_tool_call is not None:
            emit(_tool_started_event(request.direct_tool_call.name))
            tool_result = self._execute_allowed_tool_call(
                request.direct_tool_call,
                request,
            )
            emit(_tool_finished_event(tool_result))
            answer = (
                _deterministic_tool_results_answer((tool_result,))
                if tool_result.ok
                else "L'analyse déterministe du Grand Livre a échoué."
            )
            emit(
                AgentRunEvent(
                    event_type="answer_ready",
                    title="Réponse prête",
                    message="Réponse prête.",
                    status="completed",
                    provider_name="internal",
                    model_name="direct-tool-call",
                ),
            )
            return AgentRunResult(
                answer=answer,
                provider_name="internal",
                model_name="direct-tool-call",
                execution_events=tuple(events),
                tool_results=(tool_result,),
            )
        initial_model_request = _initial_model_request(
            request,
            tool_definitions=self._tool_executor.get_model_tool_definitions(
                request.allowed_tools,
            ),
        )
        emit(
            AgentRunEvent(
                event_type="model_requested",
                title="Contexte d'analyse",
                message="Identification du contexte utile.",
                status="running",
                provider_name=self._model_provider.provider_name,
            ),
        )
        initial_response = self._model_provider.generate(initial_model_request)
        _emit_fallback_if_needed(
            provider_name=self._model_provider.provider_name,
            response_provider_name=initial_response.provider_name,
            response_model_name=initial_response.model_name,
            emit=emit,
        )
        if self._has_timed_out(started_at):
            return _timeout_result(tuple(events))
        if not initial_response.tool_calls:
            answer = self._answer_policy.apply(initial_response.text).answer
            emit(
                AgentRunEvent(
                    event_type="answer_ready",
                    title="Reponse prete",
                    message="Reponse prete.",
                    status="completed",
                    provider_name=initial_response.provider_name,
                    model_name=initial_response.model_name,
                ),
            )
            return AgentRunResult(
                answer=answer,
                provider_name=initial_response.provider_name,
                model_name=initial_response.model_name,
                execution_events=tuple(events),
                tool_results=(),
            )

        stable_tool_results = self._execute_tool_calls(
            tool_calls=initial_response.tool_calls[: self._max_tool_calls],
            request=request,
            emit=emit,
            provider_name=initial_response.provider_name,
            model_name=initial_response.model_name,
        )
        if self._has_timed_out(started_at):
            return _timeout_result(tuple(events))
        if any(not result.ok for result in stable_tool_results):
            emit(
                AgentRunEvent(
                    event_type="run_failed",
                    title="Analyse arrêtée",
                    message="L'analyse demandée ne peut pas être exécutée.",
                    status="error",
                    provider_name=initial_response.provider_name,
                    model_name=initial_response.model_name,
                ),
            )
            return AgentRunResult(
                answer="Le tool call a ete refuse par les garde-fous.",
                provider_name=initial_response.provider_name,
                model_name=initial_response.model_name,
                execution_events=tuple(events),
                tool_results=stable_tool_results,
            )

        emit(
            AgentRunEvent(
                event_type="model_requested",
                title="Réponse en cours",
                message="Préparation de la réponse.",
                status="running",
                provider_name=self._model_provider.provider_name,
            ),
        )
        final_response = self._model_provider.generate(
            _final_model_request(request, stable_tool_results),
        )
        _emit_fallback_if_needed(
            provider_name=self._model_provider.provider_name,
            response_provider_name=final_response.provider_name,
            response_model_name=final_response.model_name,
            emit=emit,
        )
        if self._has_timed_out(started_at):
            return _timeout_result(tuple(events))
        answer = _final_answer_from_model_or_tools(
            final_response=final_response,
            tool_results=stable_tool_results,
            answer_policy=self._answer_policy,
        )
        emit(
            AgentRunEvent(
                event_type="answer_ready",
                title="Réponse prête",
                message="Réponse prête.",
                status="completed",
                provider_name=final_response.provider_name,
                model_name=final_response.model_name,
            ),
        )
        return AgentRunResult(
            answer=answer,
            provider_name=final_response.provider_name,
            model_name=final_response.model_name,
            execution_events=tuple(events),
            tool_results=stable_tool_results,
        )

    def _execute_allowed_tool_call(
        self,
        tool_call: ToolCall,
        request: AgentRunRequest,
    ) -> ToolExecutionResult:
        if tool_call.name not in request.allowed_tools:
            return ToolExecutionResult(
                tool_name=tool_call.name,
                ok=False,
                output={},
                error_code="tool_not_allowed",
                error_message=f"tool is not allowed: {tool_call.name}",
            )
        fact_context_token = None
        if self._ras_fact_extractor is not None and self._ras_fact_attestor is not None:
            extraction = self._ras_fact_extractor.extract(request.user_message)
            fact_context_token = self._ras_fact_attestor.issue(
                message=request.user_message,
                extraction=extraction,
                session_id=request.session_id,
                file_id=request.file_id,
            )
        return self._tool_executor.execute(
            tool_call,
            ras_fact_context_token=fact_context_token,
        )

    def _has_timed_out(self, started_at: float) -> bool:
        return self._monotonic() - started_at > self._max_run_seconds

    def _execute_tool_calls(
        self,
        tool_calls: tuple[ToolCall, ...],
        request: AgentRunRequest,
        emit: Callable[[AgentRunEvent], None],
        provider_name: str,
        model_name: str,
    ) -> tuple[ToolExecutionResult, ...]:
        tool_results = []
        for tool_call in tool_calls:
            emit(
                AgentRunEvent(
                    event_type="tool_requested",
                    title="Analyse préparée",
                    message=f"{_tool_user_label(tool_call.name)} prête.",
                    status="completed",
                    tool_name=tool_call.name,
                    provider_name=provider_name,
                    model_name=model_name,
                ),
            )
            emit(_tool_started_event(tool_call.name))
            tool_result = self._execute_allowed_tool_call(
                _with_request_context(tool_call, request),
                request,
            )
            tool_results.append(tool_result)
            emit(_tool_finished_event(tool_result))
        return tuple(tool_results)


def _timeout_result(events: tuple[AgentRunEvent, ...] = ()) -> AgentRunResult:
    timeout_event = AgentRunEvent(
        event_type="run_failed",
        title="Temps dépassé",
        message="L'analyse a dépassé le temps autorisé.",
        status="error",
        provider_name="internal",
        model_name="timeout-guard",
    )
    return AgentRunResult(
        answer=AGENT_RUN_TIMEOUT_ANSWER,
        provider_name="internal",
        model_name="timeout-guard",
        execution_events=(*events, timeout_event),
        tool_results=(),
    )


def _emit_fallback_if_needed(
    provider_name: str,
    response_provider_name: str,
    response_model_name: str,
    emit: Callable[[AgentRunEvent], None],
) -> None:
    if provider_name != "fallback":
        return
    if response_provider_name == provider_name:
        return
    emit(
        AgentRunEvent(
            event_type="fallback_used",
            title="Moteur d'analyse disponible",
            message="Connexion au moteur d'analyse.",
            status="completed",
            provider_name=response_provider_name,
            model_name=response_model_name,
        ),
    )


def _tool_started_event(tool_name: str) -> AgentRunEvent:
    return AgentRunEvent(
        event_type="tool_started",
        title="Analyse du fichier",
        message=f"{_tool_user_label(tool_name)} en cours.",
        status="running",
        tool_name=tool_name,
    )


def _tool_finished_event(tool_result: ToolExecutionResult) -> AgentRunEvent:
    if not tool_result.ok:
        return AgentRunEvent(
            event_type="tool_finished",
            title="Analyse arrêtée",
            message="L'analyse demandée ne peut pas être exécutée.",
            status="error",
            tool_name=tool_result.tool_name,
        )
    return AgentRunEvent(
        event_type="tool_finished",
        title="Analyse terminée",
        message=_tool_result_summary(tool_result),
        status="completed",
        tool_name=tool_result.tool_name,
    )


def _tool_user_label(tool_name: str) -> str:
    labels = {
        "list_sheets": "Lecture des feuilles",
        "get_columns": "Lecture des colonnes",
        "profile_sheet": "Analyse de la feuille Excel",
        "classify_ledger_schema": "Identification du sens des colonnes",
        "analyze_ledger": "Analyse du Grand Livre",
        "aggregate_ledger": "Agrégation du Grand Livre",
        "query_ledger_entries": "Recherche d'écritures",
        "calculate_ledger_metrics": "Calcul de métriques",
        "detect_data_quality_issues": "Contrôle qualité des données",
        "detect_tax_candidates": "Détection des candidats fiscaux",
        "detect_ras_candidates": "Détection des candidats RAS",
    }
    return labels.get(tool_name, "Analyse demandée")


def _tool_result_summary(tool_result: ToolExecutionResult) -> str:
    if tool_result.tool_name == "profile_sheet":
        return _rows_columns_summary(
            prefix="L'analyse de la feuille Excel est terminée",
            output=tool_result.output,
        )
    if tool_result.tool_name == "classify_ledger_schema":
        return "Le sens probable des colonnes a été identifié."
    if tool_result.tool_name == "analyze_ledger":
        return _rows_columns_summary(
            prefix="L'analyse du Grand Livre est terminée",
            output=tool_result.output,
        )
    if tool_result.tool_name == "aggregate_ledger":
        aggregation_count = len(tool_result.output.get("aggregations", ()))
        return f"{aggregation_count} regroupement(s) du Grand Livre préparé(s)."
    if tool_result.tool_name == "query_ledger_entries":
        total_matches = tool_result.output.get("total_matches")
        entries = tool_result.output.get("entries", ())
        if isinstance(total_matches, int) and isinstance(entries, list):
            return (
                f"{len(entries)} écriture(s) retournée(s) "
                f"sur {total_matches} correspondance(s)."
            )
        return "La recherche d'écritures est terminée."
    if tool_result.tool_name == "calculate_ledger_metrics":
        total_matches = tool_result.output.get("total_matches")
        if isinstance(total_matches, int):
            return (
                "Les métriques demandées sont calculées "
                f"sur {total_matches} écriture(s)."
            )
        return "Les métriques demandées sont calculées."
    if tool_result.tool_name == "detect_data_quality_issues":
        issue_count = tool_result.output.get("issue_count")
        if isinstance(issue_count, int):
            return f"{issue_count} point(s) de qualité détecté(s)."
        return "Le contrôle qualité des données est terminé."
    if tool_result.tool_name == "detect_tax_candidates":
        candidates = tool_result.output.get("candidates", ())
        if isinstance(candidates, list):
            return f"{len(candidates)} catégorie(s) candidate(s) à revoir."
        return "La détection des candidats fiscaux est terminée."
    if tool_result.tool_name == "detect_ras_candidates":
        candidate_count = tool_result.output.get("candidate_piece_count")
        if isinstance(candidate_count, int):
            return f"{candidate_count} pièce(s) candidate(s) RAS à revoir."
        return "La détection des candidats RAS est terminée."
    if tool_result.tool_name == "find_ras_counterpart":
        status_counts = tool_result.output.get("status_counts")
        if isinstance(status_counts, dict):
            return (
                f"{status_counts.get('found_in_same_entry', 0)} pièce(s) avec "
                "contrepartie RAS dans la même pièce; "
                f"{status_counts.get('indeterminate', 0)} indéterminée(s)."
            )
        return "La recherche de contrepartie RAS est terminée."
    if tool_result.tool_name == "reconstruct_accounting_entry":
        selected_found = tool_result.output.get("selected_entry_found")
        selected_entry = tool_result.output.get("selected_entry")
        if selected_found is True and isinstance(selected_entry, dict):
            line_count = selected_entry.get("line_count")
            return f"PiÃ¨ce comptable reconstituÃ©e: {line_count} ligne(s)."
        if selected_found is False:
            return "La piÃ¨ce comptable demandÃ©e n'a pas Ã©tÃ© retrouvÃ©e."
        entry_count = tool_result.output.get("entry_count")
        if isinstance(entry_count, int):
            return f"{entry_count} piÃ¨ce(s) comptable(s) reconstituÃ©e(s)."
        return "La reconstitution des piÃ¨ces comptables est terminÃ©e."
    if tool_result.tool_name == "generate_ras_audit_report":
        case_count = tool_result.output.get("case_count")
        report_id = tool_result.output.get("report_id")
        if isinstance(case_count, int) and isinstance(report_id, str):
            return f"Rapport RAS genere: {case_count} cas, report_id {report_id}."
        return "Le rapport d'audit RAS est genere."
    if tool_result.tool_name == "list_sheets":
        sheet_count = len(tool_result.output.get("sheet_names", ()))
        return f"{sheet_count} feuille(s) détectée(s) dans le fichier."
    if tool_result.tool_name == "get_columns":
        column_count = len(tool_result.output.get("columns", ()))
        return f"{column_count} colonne(s) détectée(s) dans la feuille."
    return "L'analyse demandée est terminée."


def _rows_columns_summary(prefix: str, output: dict[str, object]) -> str:
    row_count = output.get("row_count")
    column_count = output.get("column_count")
    if isinstance(row_count, int) and isinstance(column_count, int):
        return f"{prefix}: {row_count} lignes, {column_count} colonnes."
    return f"{prefix}."


def _deterministic_tool_answer(tool_result: ToolExecutionResult) -> str:
    summary = normalize_answer_summary(_tool_result_summary(tool_result))
    if tool_result.tool_name != "analyze_ledger":
        return summary

    schema = tool_result.output.get("schema")
    if not isinstance(schema, dict):
        return summary

    missing_columns = schema.get("missing_required_columns")
    if isinstance(missing_columns, list) and missing_columns:
        return (
            f"{summary}\n\n"
            "Colonnes requises manquantes: "
            f"{', '.join(str(column) for column in missing_columns)}."
        )
    return f"{summary}\n\nColonnes requises disponibles."


def _deterministic_tool_results_answer(
    tool_results: tuple[ToolExecutionResult, ...],
) -> str:
    secure_answer = _secure_deterministic_answer(tool_results)
    if secure_answer is not None:
        return secure_answer
    balance_answer = _balance_reconciliation_answer(tool_results)
    if balance_answer is not None:
        return balance_answer
    aggregation_answer = _aggregation_reconciliation_answer(tool_results)
    if aggregation_answer is not None:
        return aggregation_answer
    query_answer = _ledger_query_answer(tool_results)
    if query_answer is not None:
        return query_answer
    for tool_name in (
        "detect_ras_candidates",
        "reconstruct_accounting_entry",
        "detect_tax_candidates",
        "detect_data_quality_issues",
        "analyze_ledger",
        "classify_ledger_schema",
        "profile_sheet",
        "get_columns",
        "list_sheets",
    ):
        for tool_result in reversed(tool_results):
            if tool_result.tool_name == tool_name and tool_result.ok:
                return _deterministic_tool_answer(tool_result)
    return "Les contrôles déterministes sont terminés."


def _secure_deterministic_answer(
    tool_results: tuple[ToolExecutionResult, ...],
) -> str | None:
    tax_rag_answer = _tax_rag_answer(tool_results)
    return (
        tax_rag_answer
        if tax_rag_answer is not None
        else _ras_tool_answer(tool_results)
    )


def _ras_tool_answer(
    tool_results: tuple[ToolExecutionResult, ...],
) -> str | None:
    result = next(
        (
            item
            for item in reversed(tool_results)
            if item.ok
            and item.tool_name
            in {
                "assess_ras_accounting",
                "calculate_theoretical_ras",
                "resolve_applicable_ras_rule",
                "run_ras_audit_batch",
                "find_ras_counterpart",
                "generate_ras_audit_report",
            }
        ),
        None,
    )
    if result is None:
        return None
    output = result.output
    if result.tool_name == "calculate_theoretical_ras":
        status = str(output.get("calculation_status") or "indisponible")
        if status != "calculated_provisional":
            return _incomplete_ras_answer(
                "Calcul RAS non effectue",
                status,
                output.get("reason"),
                output.get("missing_facts"),
            )
        return "\n".join(
            (
                "**Calcul RAS deterministe**",
                "",
                f"- Statut : {status}",
                f"- Regle : {output.get('rule_id') or 'non renseignee'} "
                f"({output.get('rule_version') or 'version inconnue'})",
                f"- Assiette : {_ras_amount(output.get('base_amount'), output)}",
                f"- Taux : {output.get('rate_percent') or 'non renseigne'} %",
                f"- RAS theorique : "
                f"{_ras_amount(output.get('expected_amount'), output)}",
                "",
                "Resultat provisoire fonde sur les faits attestes et les "
                "referentiels versions.",
            )
        )
    if result.tool_name == "resolve_applicable_ras_rule":
        status = str(output.get("status") or "indisponible")
        if status != "resolved_provisional":
            return _incomplete_ras_answer(
                "Regle RAS non resolue",
                status,
                output.get("reason"),
                output.get("missing_facts"),
            )
        return "\n".join(
            (
                "**Regle RAS resolue provisoirement**",
                "",
                f"- Regle : {output.get('rule_id') or 'non renseignee'}",
                f"- Version : {output.get('rule_version') or 'non renseignee'}",
                f"- Taux : {output.get('rate_percent') or 'non renseigne'} %",
                "",
                "La resolution reste soumise au niveau d'assurance des sources.",
            )
        )
    if result.tool_name == "assess_ras_accounting":
        return "\n".join(
            (
                "**Rapprochement comptable RAS**",
                "",
                f"- Statut : {output.get('status') or 'indisponible'}",
                f"- Attendu : {_ras_amount(output.get('expected_amount'), output)}",
                f"- Comptabilise : "
                f"{_ras_amount(output.get('recorded_amount'), output)}",
                f"- Ecart : {_ras_amount(output.get('difference'), output)}",
                f"- Informations manquantes : "
                f"{_ras_list(output.get('missing_facts'))}",
                f"- Alertes : {_ras_list(output.get('issues'))}",
            )
        )
    if result.tool_name == "run_ras_audit_batch":
        return "\n".join(
            (
                "**Inventaire des candidats RAS**",
                "",
                f"- Candidats : {output.get('candidate_count', 0)}",
                f"- Potentiels : {output.get('potential_count', 0)}",
                f"- Indeterminables : {output.get('indeterminate_count', 0)}",
                f"- Perimetre technique complet : "
                f"{'oui' if output.get('source_scope_complete') is True else 'non'}",
                f"- Blocages : {_ras_list(output.get('source_scope_blockers'))}",
                "",
                "Cet inventaire ne constitue pas une conclusion declarative.",
            )
        )
    if result.tool_name == "generate_ras_audit_report":
        return "\n".join(
            (
                "**Rapport d'audit RAS**",
                "",
                f"- Report ID : {output.get('report_id') or 'non renseigne'}",
                f"- Cas analyses : {output.get('case_count', 0)}",
                f"- Statuts : {_ras_count_map(output.get('status_counts'))}",
                f"- Certitudes : {_ras_count_map(output.get('certainty_counts'))}",
                f"- Montants theoriques rapproches : "
                f"{_ras_summary_list(output.get('amount_summaries'))}",
                f"- Montants comptabilises observes : "
                f"{_ras_summary_list(output.get('recorded_amount_summaries'))}",
                f"- Referentiels : {_ras_list(output.get('reference_versions'))}",
                "",
                "Ce rapport est genere depuis les cas RAS persistés et ne "
                "constitue pas une conclusion declarative.",
            )
        )
    raw_status_counts = output.get("status_counts")
    status_counts: dict[str, object] = (
        raw_status_counts if isinstance(raw_status_counts, dict) else {}
    )
    return "\n".join(
        (
            "**Recherche de contrepartie RAS**",
            "",
            f"- Candidats detectes au sens large : "
            f"{output.get('detected_candidate_piece_count') or 'non calcule'}",
            f"- Pieces analysees pour contrepartie : "
            f"{output.get('candidate_piece_count', 0)}",
            f"- Hors scope rapprochement : "
            f"{output.get('counterpart_scope_exclusion_count') or 0}",
            f"- RAS trouvee dans la meme piece : "
            f"{status_counts.get('found_in_same_entry', 0)}",
            f"- RAS potentiellement liee : "
            f"{status_counts.get('potential_related_entry', 0)}",
            f"- RAS non trouvee dans le perimetre : "
            f"{status_counts.get('not_found_in_scope', 0)}",
            f"- Indeterminees : {status_counts.get('indeterminate', 0)}",
            f"- Montants RAS confirmes : "
            f"{_ras_amount_map(output.get('confirmed_amounts_by_currency'))}",
            f"- Informations manquantes : "
            f"{_ras_count_map(output.get('missing_fact_counts'))}",
            f"- Perimetre technique complet : "
            f"{'oui' if output.get('source_scope_complete') is True else 'non'}",
            f"- Blocages : {_ras_list(output.get('source_scope_blockers'))}",
            "",
            f"Note de perimetre : {output.get('counterpart_scope_basis')}",
        )
    )


def _incomplete_ras_answer(
    title: str,
    status: str,
    reason: object,
    missing_facts: object,
) -> str:
    return "\n".join(
        (
            f"**{title}**",
            "",
            f"- Statut : {status}",
            f"- Motif : {reason or 'information insuffisante'}",
            f"- Informations manquantes : {_ras_list(missing_facts)}",
            "",
            "Aucun montant ni taux n'a ete deduit par le LLM.",
        )
    )


def _ras_amount(value: object, output: dict[str, object]) -> str:
    if value is None:
        return "non calculable"
    currency = output.get("currency")
    if isinstance(currency, str) and currency:
        return f"{value} {currency}"
    return str(value)


def _ras_amount_map(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "aucun"
    return ", ".join(
        f"{amount} {currency}" for currency, amount in sorted(value.items())
    )


def _ras_count_map(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "aucune"
    return ", ".join(f"{key}: {count}" for key, count in sorted(value.items()))


def _ras_summary_list(value: object) -> str:
    if not isinstance(value, list) or not value:
        return "aucun"
    parts: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        currency = item.get("currency") or "devise inconnue"
        count = item.get("case_count") or 0
        certainty = item.get("certainty") or "certitude inconnue"
        if item.get("expected_amount") is not None:
            parts.append(
                f"{currency}/{certainty}: {count} cas, attendu "
                f"{item.get('expected_amount')}, comptabilise "
                f"{item.get('recorded_amount')}, ecart {item.get('difference')}"
            )
        elif item.get("recorded_amount") is not None:
            parts.append(
                f"{currency}/{certainty}: {count} cas, comptabilise "
                f"{item.get('recorded_amount')}"
            )
    return "; ".join(parts) if parts else "aucun"


def _ras_list(value: object) -> str:
    if not isinstance(value, list | tuple) or not value:
        return "aucun"
    return ", ".join(str(item) for item in value)


def _final_answer_from_model_or_tools(
    final_response: ModelResponse,
    tool_results: tuple[ToolExecutionResult, ...],
    answer_policy: AgentAnswerPolicy,
) -> str:
    if (
        _is_controlled_internal_response(final_response)
        or not final_response.text.strip()
    ):
        return _deterministic_tool_results_answer(tool_results)
    return answer_policy.apply(final_response.text).answer


def _tax_rag_answer(
    tool_results: tuple[ToolExecutionResult, ...],
) -> str | None:
    result = next(
        (
            item
            for item in reversed(tool_results)
            if item.ok and item.tool_name == "query_tax_rag"
        ),
        None,
    )
    if result is None:
        return None
    citations = result.output.get("citations")
    if not isinstance(citations, list):
        return None
    if not citations:
        return (
            "Aucun passage suffisamment pertinent n'a été retrouvé dans les "
            "sources fiscales validées. Aucune conclusion juridique ne peut être "
            "tirée de cette recherche."
        )
    lines = [
        "**Sources fiscales retrouvées**",
        "",
        "Ces passages sont documentaires et ne constituent pas, à eux seuls, "
        "une décision fiscale ni un calcul de RAS.",
    ]
    for index, raw_citation in enumerate(citations, start=1):
        if not isinstance(raw_citation, dict):
            continue
        passage = " ".join(str(raw_citation.get("passage") or "").split())[:500]
        title = str(raw_citation.get("title") or "Source sans titre")
        article = str(raw_citation.get("article_or_section") or "Section non précisée")
        version = str(raw_citation.get("version") or "Version non précisée")
        source_url = str(raw_citation.get("source_url") or "URL indisponible")
        source_hash = str(raw_citation.get("source_sha256") or "")
        score = raw_citation.get("score")
        applicability = str(raw_citation.get("applicability_status") or "non précisée")
        lines.extend(
            (
                "",
                f"{index}. **{title} — {article}**",
                f"   Version : {version}",
                f"   Applicabilité : {applicability}",
                f"   Passage : {passage}",
                f"   Source : {source_url}",
                f"   Empreinte SHA-256 : `{source_hash}` · Score : {score}",
            )
        )
    return "\n".join(lines)


def _aggregation_reconciliation_answer(
    tool_results: tuple[ToolExecutionResult, ...],
) -> str | None:
    successful_results = tuple(result for result in tool_results if result.ok)
    if len(successful_results) != 1:
        return None
    result = successful_results[0]
    if result.tool_name != "aggregate_ledger":
        return None
    aggregations = result.output.get("aggregations")
    if not isinstance(aggregations, dict):
        return None
    filters = result.output.get("filters")
    filter_text = "Aucun"
    if isinstance(filters, dict) and filters:
        filter_text = ", ".join(f"{key} = {value}" for key, value in filters.items())
    lines = [
        "**Rapprochement des agrégations**",
        "",
        f"Filtres appliqués : {filter_text}",
        f"Écritures filtrées : {result.output.get('row_count', 0)}",
    ]
    for dimension, raw_aggregation in aggregations.items():
        if not isinstance(raw_aggregation, dict):
            continue
        groups = raw_aggregation.get("groups")
        if not isinstance(groups, list):
            continue
        lines.extend(
            (
                "",
                f"**Regroupement par {dimension}**",
                "",
                "| Groupe | Devise | Lignes | Utilisées | Exclues | "
                "Brut | Débit | Crédit | Solde |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|",
            ),
        )
        for raw_group in groups:
            if not isinstance(raw_group, dict):
                continue
            currency = str(raw_group.get("currency") or "Sans devise")
            lines.append(
                f"| {raw_group.get('key', 'Sans valeur')} | {currency} "
                f"| {_integer_value(raw_group, 'entry_count')} "
                f"| {_integer_value(raw_group, 'used_entry_count')} "
                f"| {_integer_value(raw_group, 'excluded_entry_count')} "
                f"| {_amount_value(raw_group, 'raw_amount_sum', currency)} "
                f"| {_amount_value(raw_group, 'debit_total', currency)} "
                f"| {_amount_value(raw_group, 'credit_total', currency)} "
                f"| {_amount_value(raw_group, 'balance', currency)} |",
            )
    return "\n".join(lines)


def _ledger_query_answer(
    tool_results: tuple[ToolExecutionResult, ...],
) -> str | None:
    successful_results = tuple(result for result in tool_results if result.ok)
    if len(successful_results) != 1:
        return None
    result = successful_results[0]
    if result.tool_name != "query_ledger_entries":
        return None
    entries = result.output.get("entries")
    if not isinstance(entries, list):
        return None
    filters = result.output.get("filters")
    filter_text = "Aucun"
    if isinstance(filters, dict) and filters:
        filter_text = ", ".join(f"{key} = {value}" for key, value in filters.items())
    total_matches = result.output.get("total_matches", 0)
    page = result.output.get("page", 1)
    page_size = result.output.get("page_size", len(entries))
    lines = [
        "**Ecritures comptables**",
        "",
        f"Filtres appliques : {filter_text}",
        f"Correspondances : {_plain_int(total_matches)}",
        f"Page : {_plain_int(page)} (taille {_plain_int(page_size)})",
    ]
    if not entries:
        lines.extend(
            (
                "",
                "Aucune ecriture ne correspond aux filtres. Ce resultat ne doit pas "
                "etre interprete comme un solde nul.",
            )
        )
        lines.extend(_filter_warning_lines(result.output.get("filter_warnings")))
        return "\n".join(lines)

    headers = (
        ("account", "Compte"),
        ("amount", "Montant signe"),
        ("posting_key", "Cle"),
        ("currency", "Devise"),
        ("period", "Periode"),
        ("fiscal_year", "Exercice"),
        ("document_type", "Type piece"),
        ("tax_code", "Code fiscal"),
        ("vendor", "Fournisseur"),
        ("customer", "Client"),
    )
    present_headers = tuple(
        header
        for header in headers
        if any(isinstance(entry, dict) and header[0] in entry for entry in entries)
    )
    lines.extend(
        (
            "",
            "| " + " | ".join(label for _, label in present_headers) + " |",
            "| "
            + " | ".join(
                "---:" if key == "amount" else "---"
                for key, _ in present_headers
            )
            + " |",
        )
    )
    for entry in entries[:20]:
        if not isinstance(entry, dict):
            continue
        cells = [
            _markdown_cell(_format_query_value(entry.get(key), key))
            for key, _ in present_headers
        ]
        lines.append("| " + " | ".join(cells) + " |")
    if result.output.get("sign_convention") == "debit_positive_credit_negative":
        lines.extend(
            (
                "",
                "Convention : montant signe = debit positif, credit negatif, "
                "d'apres les cles de comptabilisation connues.",
            )
        )
    return "\n".join(lines)


def _balance_reconciliation_answer(
    tool_results: tuple[ToolExecutionResult, ...],
) -> str | None:
    result = next(
        (
            item
            for item in reversed(tool_results)
            if item.ok and item.tool_name == "calculate_ledger_metrics"
        ),
        None,
    )
    if result is None:
        return None
    reconciliation = result.output.get("balance_reconciliation")
    if not isinstance(reconciliation, dict):
        return None

    filters = result.output.get("filters")
    filter_text = "Aucun"
    if isinstance(filters, dict) and filters:
        filter_text = ", ".join(f"{key} = {value}" for key, value in filters.items())
    by_currency = reconciliation.get("by_currency")
    currency_names = tuple(by_currency) if isinstance(by_currency, dict) else ()
    display_currency = currency_names[0] if len(currency_names) == 1 else None
    lines = [
        "**Rapprochement du solde**",
        "",
        f"Filtres appliqués : {filter_text}",
        f"Colonne de montant : {result.output.get('amount_field', 'Non renseignée')}",
        "",
        f"- Écritures trouvées : {_integer_value(reconciliation, 'entry_count')}",
        f"- Écritures utilisées : {_integer_value(reconciliation, 'used_entry_count')}",
        "- Écritures exclues : "
        f"{_integer_value(reconciliation, 'excluded_entry_count')}",
    ]
    entry_count = _integer_value(reconciliation, "entry_count")
    used_entry_count = _integer_value(reconciliation, "used_entry_count")
    if entry_count == 0:
        lines.extend(
            (
                "",
                "Aucune écriture ne correspond aux filtres. Aucun solde "
                "comptable ne peut être calculé ; ce résultat n'est pas un "
                "solde nul.",
            )
        )
        lines.extend(_filter_warning_lines(result.output.get("filter_warnings")))
        return "\n".join(lines)
    if used_entry_count == 0:
        lines.extend(
            (
                "",
                "Des écritures correspondent aux filtres, mais aucune n'est "
                "interprétable pour le calcul débit/crédit. Aucun solde "
                "calculable n'est présenté.",
            )
        )
        return "\n".join(lines)
    if len(currency_names) <= 1:
        lines.extend(
            (
                "- Somme brute : "
                f"{_amount_value(reconciliation, 'raw_amount_sum', display_currency)}",
                "- Total débit : "
                f"{_amount_value(reconciliation, 'debit_total', display_currency)}",
                "- Total crédit : "
                f"{_amount_value(reconciliation, 'credit_total', display_currency)}",
                "- **Solde (débit − crédit) : "
                f"{_amount_value(reconciliation, 'balance', display_currency)}**",
            ),
        )
    else:
        lines.append(
            "- Montants globaux non présentés : plusieurs devises sont présentes.",
        )
    if isinstance(by_currency, dict) and by_currency:
        lines.extend(
            (
                "",
                "**Rapprochement par devise**",
                "",
                "| Devise | Brut | Débit | Crédit | Solde | Utilisées | Exclues |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ),
        )
        for currency, raw_totals in by_currency.items():
            if not isinstance(raw_totals, dict):
                continue
            raw_sum = _amount_value(raw_totals, "raw_amount_sum", currency)
            lines.append(
                f"| {currency} | {raw_sum} "
                f"| {_amount_value(raw_totals, 'debit_total', currency)} "
                f"| {_amount_value(raw_totals, 'credit_total', currency)} "
                f"| {_amount_value(raw_totals, 'balance', currency)} "
                f"| {_integer_value(raw_totals, 'used_entry_count')} "
                f"| {_integer_value(raw_totals, 'excluded_entry_count')} |",
            )
    by_key = reconciliation.get("by_posting_key")
    if isinstance(by_key, list) and by_key:
        lines.extend(
            (
                "",
                "**Détail par clé de comptabilisation**",
                "",
                "| Clé | Sens | Écritures | Utilisées | Montant brut |",
                "|---|---|---:|---:|---:|",
            ),
        )
        for raw_key in by_key:
            if not isinstance(raw_key, dict):
                continue
            lines.append(
                f"| {raw_key.get('posting_key', 'Sans clé')} "
                f"| {raw_key.get('side', 'unknown')} "
                f"| {_integer_value(raw_key, 'entry_count')} "
                f"| {_integer_value(raw_key, 'used_entry_count')} "
                f"| {_amount_value(raw_key, 'raw_amount_sum')} |",
            )
    reasons = reconciliation.get("excluded_reasons")
    if (
        isinstance(reasons, dict)
        and _integer_value(
            reconciliation,
            "excluded_entry_count",
        )
        > 0
    ):
        lines.extend(
            (
                "",
                "**Avertissement**",
                "",
                "Le solde est calculé uniquement sur les écritures interprétables. "
                "Clé absente ou inconnue : "
                f"{reasons.get('missing_or_unknown_posting_key', 0)} ; "
                "montant absent ou invalide : "
                f"{reasons.get('missing_or_invalid_amount', 0)}.",
            ),
        )
    return "\n".join(lines)


def _amount_value(
    values: dict[str, object],
    key: str,
    currency: str | None = None,
) -> str:
    value = values.get(key, 0)
    if not isinstance(value, int | float):
        return "0"
    formatted = f"{value:,.2f}".replace(",", " ")
    return f"{formatted} {currency}" if currency else formatted


def _filter_warning_lines(raw_warnings: object) -> list[str]:
    if not isinstance(raw_warnings, list) or not raw_warnings:
        return []
    lines = ["", "**Alerte filtre**"]
    for warning in raw_warnings:
        if not isinstance(warning, dict):
            continue
        if warning.get("warning_type") != "account_prefix_matches_only":
            continue
        samples = warning.get("sample_accounts")
        sample_text = (
            ", ".join(str(account) for account in samples)
            if isinstance(samples, list)
            else "non disponible"
        )
        lines.append(
            "Aucun compte exact "
            f"{warning.get('account_filter')} n'a ete trouve, mais "
            f"{warning.get('matching_entry_count', 0)} ecriture(s) existent sur "
            f"{warning.get('matching_account_count', 0)} compte(s) commencant par "
            f"ce prefixe : {sample_text}."
        )
    return lines if len(lines) > 2 else []


def _integer_value(values: dict[str, object], key: str) -> int:
    value = values.get(key, 0)
    return int(value) if isinstance(value, int | float) else 0


def _plain_int(value: object) -> int:
    return int(value) if isinstance(value, int | float) else 0


def _format_query_value(value: object, key: str) -> str:
    if value is None or value == "":
        return "Sans valeur"
    if key == "amount" and isinstance(value, int | float):
        return f"{value:,.2f}".replace(",", " ")
    return str(value)


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _is_controlled_internal_response(response: ModelResponse) -> bool:
    return response.provider_name in {"internal", "internal-fallback"}


def normalize_answer_summary(message: str) -> str:
    return message.replace(
        "L'analyse de la feuille Excel est terminée:",
        "Analyse de la feuille Excel terminée:",
    ).replace(
        "L'analyse du Grand Livre est terminée:",
        "Analyse du Grand Livre terminée:",
    )


def _initial_model_request(
    request: AgentRunRequest,
    tool_definitions: tuple[ModelToolDefinition, ...],
) -> ModelRequest:
    messages = [
        ModelMessage(
            role="system",
            content=(
                "Tu es un agent d'analyse Excel. Utilise seulement les tools "
                "autorises. Ne prends aucune decision fiscale. "
                "Le RAG fournit seulement des passages a citer; il ne choisit "
                "jamais une regle structuree. Une resolution ou un calcul fiscal "
                "doit venir du tool deterministe correspondant. Reponds en "
                "Markdown clair avec des paragraphes courts. Pour une reponse "
                "simple, n'ajoute pas de titre comme Introduction. Evite les "
                "formulations a la premiere personne. Choisis toujours le tool "
                "le plus specifique a la question finale de l'utilisateur, pas "
                "un tool preparatoire. Si l'utilisateur demande "
                "d'afficher, lister ou rechercher des ecritures detaillees du "
                "Grand Livre, utilise query_ledger_entries. Si l'utilisateur "
                "demande un solde, un total, un debit ou un credit, utilise "
                "calculate_ledger_metrics. Si l'utilisateur demande une "
                "structure, des colonnes ou le mapping d'une feuille, utilise "
                "classify_ledger_schema ou get_columns. Si l'utilisateur "
                "demande de reconstituer, controler ou analyser une piece "
                "comptable precise par numero de piece, utilise "
                "reconstruct_accounting_entry avec entry_selector. N'utilise "
                "pas query_ledger_entries pour un numero de piece/document, "
                "car ce tool ne filtre pas les numeros de piece. Si "
                "l'utilisateur demande une contrepartie RAS, une RAS "
                "comptabilisee dans la meme piece ou un rapprochement entre "
                "depense candidate et compte RAS, utilise find_ras_counterpart. "
                "Une question du type 'les pieces candidates RAS ont-elles une "
                "contrepartie' doit appeler find_ras_counterpart directement. "
                "N'utilise detect_ras_candidates que pour inventorier les "
                "candidats RAS, jamais pour verifier leur contrepartie. "
                "Si l'utilisateur pose une question juridique ou fiscale sur "
                "un taux, un article, le CGI, une loi de finances, un delai, "
                "une condition, une exemption ou le champ d'application d'une "
                "retenue, utilise query_tax_rag, meme s'il ne demande pas "
                "explicitement les sources indexees. Si l'utilisateur demande "
                "un rapport, une synthese ou un export d'un audit RAS avec un "
                "audit_id, utilise generate_ras_audit_report. L'audit_id suffit "
                "pour retrouver les cas deja persistés; ne redemande pas les "
                "faits, la juridiction ou le fichier pour cette generation."
            ),
        ),
        ModelMessage(role="user", content=request.user_message),
    ]
    if request.file_path is not None:
        messages.append(
            ModelMessage(
                role="system",
                content=(
                    "Un fichier actif est attache cote serveur. Son chemin et "
                    "son identifiant ne sont pas divulgues au modele."
                ),
            ),
        )
    if request.sheet_name is not None:
        messages.append(
            ModelMessage(
                role="system",
                content=(
                    "La feuille active est selectionnee cote serveur et sera "
                    "injectee dans les appels de tools autorises."
                ),
            ),
        )
    return ModelRequest(
        messages=tuple(messages),
        allowed_tools=request.allowed_tools,
        temperature=0.0,
        max_output_tokens=1200,
        timeout_seconds=30.0,
        tool_definitions=_server_context_aware_tool_definitions(
            request,
            tool_definitions,
        ),
    )


def _server_context_aware_tool_definitions(
    request: AgentRunRequest,
    tool_definitions: tuple[ModelToolDefinition, ...],
) -> tuple[ModelToolDefinition, ...]:
    if request.file_path is None:
        return tool_definitions
    return tuple(
        ModelToolDefinition(
            name=definition.name,
            description=definition.description,
            input_schema=_without_server_injected_properties(
                definition.input_schema,
                inject_sheet=request.sheet_name is not None,
                model_hidden_properties=_model_hidden_properties(definition.name),
            ),
        )
        for definition in tool_definitions
    )


def _without_server_injected_properties(
    input_schema: dict[str, object],
    *,
    inject_sheet: bool,
    model_hidden_properties: set[str] | None = None,
) -> dict[str, object]:
    schema = dict(input_schema)
    raw_properties = schema.get("properties")
    if isinstance(raw_properties, dict):
        removed_properties = {"file_path"}
        if inject_sheet:
            removed_properties.add("sheet_name")
        if model_hidden_properties:
            removed_properties.update(model_hidden_properties)
        schema["properties"] = {
            key: value
            for key, value in raw_properties.items()
            if key not in removed_properties
        }
    raw_required = schema.get("required")
    if isinstance(raw_required, list):
        removed_required = {"file_path"}
        if inject_sheet:
            removed_required.add("sheet_name")
        if model_hidden_properties:
            removed_required.update(model_hidden_properties)
        schema["required"] = [
            field for field in raw_required if field not in removed_required
        ]
    return schema


def _model_hidden_properties(tool_name: str) -> set[str]:
    if tool_name in {
        "detect_ras_candidates",
        "find_ras_counterpart",
        "reconstruct_accounting_entry",
    }:
        return {"column_mapping"}
    return set()


def _with_request_context(
    tool_call: ToolCall,
    request: AgentRunRequest,
) -> ToolCall:
    arguments = dict(tool_call.arguments)
    tools_without_file_context = {
        "query_tax_rag",
        "resolve_applicable_ras_rule",
        "calculate_theoretical_ras",
        "generate_ras_audit_report",
    }
    if (
        request.file_path is not None
        and tool_call.name not in tools_without_file_context
    ):
        arguments["file_path"] = str(request.file_path)
    if (
        request.sheet_name is not None
        and tool_call.name != "list_sheets"
        and tool_call.name not in tools_without_file_context
    ):
        arguments["sheet_name"] = request.sheet_name
    return ToolCall(name=tool_call.name, arguments=arguments)


def _single_candidate_ras_followup(
    tool_results: tuple[ToolExecutionResult, ...],
    request: AgentRunRequest,
) -> ToolCall | None:
    if "assess_ras_accounting" not in request.allowed_tools:
        return None
    batch = next(
        (
            result
            for result in reversed(tool_results)
            if result.tool_name == "run_ras_audit_batch" and result.ok
        ),
        None,
    )
    if batch is None:
        return None
    audit_id = batch.output.get("audit_id")
    candidate_ids = batch.output.get("review_candidate_ids")
    remaining = batch.output.get("remaining_candidate_count")
    if (
        not isinstance(audit_id, str)
        or not isinstance(candidate_ids, list)
        or len(candidate_ids) != 1
        or not isinstance(candidate_ids[0], str)
        or remaining != 0
    ):
        return None
    return ToolCall(
        name="assess_ras_accounting",
        arguments={
            "base_audit_id": audit_id,
            "candidate_id": candidate_ids[0],
        },
    )


def _final_model_request(
    request: AgentRunRequest,
    tool_results: tuple[ToolExecutionResult, ...],
) -> ModelRequest:
    has_tax_rag_only = bool(tool_results) and all(
        result.tool_name == "query_tax_rag" for result in tool_results
    )
    sensitive_tool_names = {
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
    }
    if has_tax_rag_only:
        user_context = request.user_message
    elif any(result.tool_name in sensitive_tool_names for result in tool_results):
        user_context = (
            "Explique uniquement le resultat structure du controle fiscal demande."
        )
    else:
        user_context = request.user_message
    return ModelRequest(
        messages=(
            ModelMessage(
                role="system",
                content=(
                    "Redige une reponse courte a partir des resultats de tools. "
                    "Pour query_tax_rag, commence par une reponse directe en "
                    "une phrase quand les citations contiennent clairement "
                    "l'information demandee. Cite ensuite 1 a 3 sources les "
                    "plus pertinentes avec article, version et URL. Ecarte les "
                    "citations hors cas, par exemple non-resident ou loyers si "
                    "la question porte sur un prestataire resident. Si les "
                    "sources ne suffisent pas, dis-le. Presente le resultat "
                    "comme information documentaire, jamais comme calcul ou "
                    "decision fiscale. "
                    "Pour reconstruct_accounting_entry, presente le numero de "
                    "piece, l'exercice, le journal, l'equilibrage, les totaux "
                    "debit/credit par devise et les lignes retournees. "
                    "Pour find_ras_counterpart, presente les pieces analysees, "
                    "les contreparties trouvees, les cas indetermines, les "
                    "montants confirmes par devise et les limites de perimetre. "
                    "Pour generate_ras_audit_report, presente report_id, audit_id "
                    "si disponible, nombre de cas, statuts, certitudes, montants "
                    "theoriques rapproches par devise si disponibles, montants "
                    "comptabilises observes par devise, versions de referentiels "
                    "et limites; ne demande pas de faits supplementaires si le "
                    "tool a reussi. "
                    "Utilise du Markdown lisible: paragraphes courts, listes "
                    "a puces si utile, tableaux simples seulement si cela clarifie. "
                    "Pour une reponse simple, n'ajoute pas de titre comme "
                    "Introduction. Evite les formulations a la premiere personne. "
                    "Ne revele pas de donnees sensibles."
                ),
            ),
            ModelMessage(role="user", content=user_context),
            ModelMessage(
                role="user",
                content=(
                    "Résultats déterministes déjà calculés par l'API. "
                    "Réponds uniquement à partir de ces résultats, sans inventer.\n"
                    f"{_tool_results_context(tool_results)}"
                ),
            ),
        ),
        allowed_tools=(),
        temperature=0.0,
        max_output_tokens=1200,
        timeout_seconds=30.0,
    )


def _tool_results_context(tool_results: tuple[ToolExecutionResult, ...]) -> str:
    payload = [
        {
            "tool_name": tool_result.tool_name,
            "ok": tool_result.ok,
            "summary": normalize_answer_summary(_tool_result_summary(tool_result)),
            "output": _compact_tool_output(tool_result),
            "error_code": tool_result.error_code,
        }
        for tool_result in tool_results
    ]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _compact_tool_output(tool_result: ToolExecutionResult) -> dict[str, object]:
    output = tool_result.output
    compact_output: dict[str, object] = {}
    for key in (
        "sheet_names",
        "sheet_name",
        "row_count",
        "entry_count",
        "balanced_count",
        "unbalanced_count",
        "column_count",
        "schema",
        "columns",
        "report_id",
        "source_sha256",
        "generated_at",
        "case_count",
        "issue_count",
        "severity_counts",
        "issues",
        "decision_status",
        "candidates",
        "aggregations",
        "metrics",
        "amount_field",
        "balance_interpretation",
        "metrics_by_currency",
        "balance_reconciliation",
        "selector",
        "selected_entry_found",
        "selected_entry",
        "detected_candidate_piece_count",
        "counterpart_scope_exclusion_count",
        "counterpart_scope_basis",
        "total_matches",
        "filters",
        "filter_warnings",
        "page",
        "page_size",
        "returned_columns",
        "message",
        "entries",
        "citations",
        "as_of_date",
        "indexed_source_count",
        "audit_id",
        "candidate_count",
        "potential_count",
        "indeterminate_count",
        "remaining_candidate_count",
        "status_counts",
        "certainty_counts",
        "amount_summaries",
        "recorded_amount_summaries",
        "details",
        "reference_versions",
        "confirmed_amounts_by_currency",
        "potential_related_amounts_by_currency",
        "potential_adjustments_by_currency",
        "missing_fact_counts",
        "source_scope_complete",
        "source_scope_blockers",
        "source_scope_policy_version",
        "status",
        "legal_resolution_status",
        "calculation_status",
        "rule_id",
        "rule_version",
        "expected_amount",
        "recorded_amount",
        "difference",
        "currency",
        "missing_facts",
        "basis_is_complete",
        "legal_sources",
        "decision_status",
    ):
        if key in output:
            compact_output[key] = output[key]
    return compact_output
