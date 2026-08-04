from functools import lru_cache
from pathlib import Path

from app.account_mapping.rule_loader import load_classification_rules
from app.config import Settings
from app.excel_agent.excel_tools import ExcelAgentTools
from app.excel_agent.tool_executor import ExcelToolExecutor
from app.excel_agent.tool_registry import create_excel_tool_registry
from app.ledger_analysis.account_balance_rules import load_account_balance_rules
from app.ledger_analysis.posting_key_rules import load_posting_key_rules
from app.llm.domain import ToolCall
from app.rag_source.embedding_provider_factory import create_embedding_provider
from app.rag_source.fiscal_vector_retriever import create_fiscal_vector_retriever
from app.ras_audit.account_mapping import load_ras_ledger_account_mappings
from app.ras_audit.accounting_assessment import (
    load_ras_accounting_assessment_policies,
)
from app.ras_audit.candidate_signals import load_ras_candidate_signals
from app.ras_audit.column_aliases import load_ledger_column_aliases
from app.ras_audit.fact_context import RasFactContextAttestor
from app.ras_audit.legal_rules import load_ras_legal_rules
from app.ras_audit.persistence import SqlAlchemyRasAuditRepository
from app.ras_audit.semantic_classifier import (
    RasTransactionSemanticClassifier,
    load_ras_semantic_policy,
)
from app.ras_audit.tax_event_rules import load_ras_tax_event_rules
from app.ras_audit.tax_rag_query import TaxRagQueryService
from app.ras_audit.theoretical_calculation import load_ras_calculation_parameters
from app.schemas.agent import AgentDashboardChartResponse, AgentFileDashboardResponse


def create_excel_tool_executor(
    settings: Settings,
    ras_audit_repository: SqlAlchemyRasAuditRepository | None = None,
) -> ExcelToolExecutor:
    candidate_signals = load_ras_candidate_signals(
        Path(settings.ras_candidate_signals_path),
    )
    semantic_classifier = _create_semantic_classifier(
        settings.ras_semantic_embedding_provider,
        settings.ras_semantic_embedding_model_name,
        settings.ras_candidate_signals_path,
        settings.ras_semantic_policy_path,
    )
    return ExcelToolExecutor(
        tools=ExcelAgentTools(
            allowed_root=Path(settings.excel_agent_allowed_root_path),
            allowed_roots=(Path(settings.agent_file_storage_root_path),),
        ),
        registry=create_excel_tool_registry(),
        tax_candidate_rules=load_classification_rules(
            Path(settings.ras_classification_rules_path),
        ),
        posting_key_rules=load_posting_key_rules(
            Path(settings.posting_key_rules_path),
        ),
        account_balance_rules=load_account_balance_rules(
            Path(settings.account_balance_rules_path),
        ),
        ledger_column_aliases=load_ledger_column_aliases(
            Path(settings.ras_gl_column_aliases_path),
        ),
        ras_candidate_signals=candidate_signals,
        ras_semantic_classifier=semantic_classifier,
        ras_legal_rules=load_ras_legal_rules(
            Path(settings.ras_legal_rules_path),
            repository_root=Path(settings.ras_legal_repository_root_path),
        ),
        ras_tax_event_rules=load_ras_tax_event_rules(
            Path(settings.ras_tax_event_rules_path),
            repository_root=Path(settings.ras_legal_repository_root_path),
        ),
        ras_calculation_parameters=load_ras_calculation_parameters(
            Path(settings.ras_calculation_parameters_path),
            repository_root=Path(settings.ras_legal_repository_root_path),
        ),
        ras_accounting_assessment_policies=(
            load_ras_accounting_assessment_policies(
                Path(settings.ras_accounting_assessment_policy_path),
            )
        ),
        ras_fact_context_attestor=(
            RasFactContextAttestor(
                settings.ras_fact_context_signing_key.get_secret_value()
            )
            if settings.ras_fact_context_signing_key is not None
            else None
        ),
        ras_audit_repository=ras_audit_repository,
        max_ras_batch_candidates=settings.ras_batch_max_candidates,
        default_company_code=settings.ras_default_company_code,
        tax_rag_query_service=_create_tax_rag_query_service(
            settings.tax_rag_source_root_path,
            settings.rag_embedding_provider,
            settings.rag_embedding_model_name,
        ),
        ras_ledger_account_mappings=(
            load_ras_ledger_account_mappings(
                Path(settings.ras_ledger_account_mapping_path),
            )
            if settings.ras_ledger_account_mapping_path
            else ()
        ),
    )


@lru_cache(maxsize=4)
def _create_tax_rag_query_service(
    source_root_path: str,
    provider_name: str,
    model_name: str,
) -> TaxRagQueryService:
    source_root = Path(source_root_path)
    return TaxRagQueryService(
        source_root,
        vector_retriever=(
            create_fiscal_vector_retriever(
                source_root,
                provider_name,
                model_name,
            )
            if provider_name == "sentence-transformers"
            else None
        ),
    )


@lru_cache(maxsize=4)
def _create_semantic_classifier(
    provider_name: str,
    model_name: str,
    signals_path: str,
    policy_path: str,
) -> RasTransactionSemanticClassifier | None:
    if provider_name.strip().lower() == "disabled":
        return None
    return RasTransactionSemanticClassifier(
        embedding_provider=create_embedding_provider(
            provider_name=provider_name,
            model_name=model_name,
        ),
        provider_name=provider_name,
        model_name=model_name,
        signals=load_ras_candidate_signals(Path(signals_path)),
        policy=load_ras_semantic_policy(Path(policy_path)),
    )


def build_file_dashboard(
    settings: Settings,
    file_id: str,
    file_path: Path,
    sheet_name: str,
) -> AgentFileDashboardResponse:
    executor = create_excel_tool_executor(settings)
    analysis = _successful_tool_output(
        executor.execute(
            ToolCall(
                name="analyze_ledger",
                arguments={"file_path": str(file_path), "sheet_name": sheet_name},
            ),
        ),
    )
    metrics = _successful_tool_output(
        executor.execute(
            ToolCall(
                name="calculate_ledger_metrics",
                arguments={
                    "file_path": str(file_path),
                    "sheet_name": sheet_name,
                    "metrics": ["sum", "count", "average", "min", "max"],
                    "top_by": "account",
                    "top_limit": 8,
                },
            ),
        ),
    )
    aggregation = _successful_tool_output(
        executor.execute(
            ToolCall(
                name="aggregate_ledger",
                arguments={
                    "file_path": str(file_path),
                    "sheet_name": sheet_name,
                    "group_by": [
                        "account",
                        "currency",
                        "period",
                        "document_type",
                        "tax_code",
                        "vendor",
                        "customer",
                    ],
                    "limit": 12,
                },
            ),
        ),
    )
    quality = _successful_tool_output(
        executor.execute(
            ToolCall(
                name="detect_data_quality_issues",
                arguments={"file_path": str(file_path), "sheet_name": sheet_name},
            ),
        ),
    )
    tax_candidates = _successful_tool_output(
        executor.execute(
            ToolCall(
                name="detect_tax_candidates",
                arguments={
                    "file_path": str(file_path),
                    "sheet_name": sheet_name,
                    "limit": 8,
                },
            ),
        ),
    )
    return AgentFileDashboardResponse(
        file_id=file_id,
        sheet_name=sheet_name,
        summary={
            "row_count": analysis.get("row_count", 0),
            "column_count": analysis.get("column_count", 0),
            "sheet_name": sheet_name,
        },
        schema_overview=_dict_value(analysis.get("schema")),
        metrics=_dict_value(metrics.get("metrics")),
        amount_metrics_by_currency=_currency_metrics(
            metrics.get("metrics_by_currency"),
        ),
        charts=_dashboard_charts(
            metrics=metrics,
            aggregation=aggregation,
            quality=quality,
            tax_candidates=tax_candidates,
        ),
        quality={
            "issue_count": quality.get("issue_count", 0),
            "severity_counts": quality.get("severity_counts", {}),
            "issues": quality.get("issues", []),
        },
    )


def _successful_tool_output(tool_result: object) -> dict[str, object]:
    if not hasattr(tool_result, "ok") or not hasattr(tool_result, "output"):
        raise ValueError("invalid dashboard tool result")
    if not bool(tool_result.ok):
        raise ValueError("dashboard tool failed")
    output = tool_result.output
    if not isinstance(output, dict):
        raise ValueError("dashboard tool output is invalid")
    return output


def _dashboard_charts(
    metrics: dict[str, object],
    aggregation: dict[str, object],
    quality: dict[str, object],
    tax_candidates: dict[str, object],
) -> list[AgentDashboardChartResponse]:
    charts: list[AgentDashboardChartResponse] = []
    aggregations = _dict_value(aggregation.get("aggregations"))
    charts.extend(_account_charts(metrics, aggregations))
    charts.extend(_field_amount_charts(aggregations))
    charts.extend(_quality_charts(quality))
    charts.extend(_tax_candidate_charts(tax_candidates))
    return charts


def _account_charts(
    metrics: dict[str, object],
    aggregations: dict[str, object],
) -> list[AgentDashboardChartResponse]:
    top = _dict_value(metrics.get("top"))
    amount_groups = _list_value(top.get("groups")) or _aggregation_groups(
        aggregations,
        "account",
    )
    count_groups = _aggregation_groups(aggregations, "account") or amount_groups
    labels: list[str] = []
    amount_values: list[float | int] = []
    for group in amount_groups:
        key = group.get("key")
        amount_sum = group.get("amount_sum")
        if isinstance(key, str) and isinstance(amount_sum, int | float):
            labels.append(key)
            amount_values.append(amount_sum)
    count_labels: list[str] = []
    count_values: list[float | int] = []
    for group in count_groups:
        key = group.get("key")
        entry_count = group.get("entry_count")
        if isinstance(key, str) and isinstance(entry_count, int | float):
            count_labels.append(key)
            count_values.append(entry_count)
    if not labels and not count_labels:
        return []
    charts: list[AgentDashboardChartResponse] = []
    if labels:
        charts.append(
            _chart(
                chart_id="top_accounts_by_amount",
                title="Top comptes par montant",
                kind="bar",
                metric="amount_sum",
                labels=labels,
                values=amount_values,
                series_name="Montant",
                metadata={
                    "dimension": "account",
                    "currencies": _group_currencies(amount_groups),
                    "currency": _common_group_currency(amount_groups),
                },
            ),
        )
    if count_labels:
        charts.append(
            _chart(
                chart_id="entries_by_account",
                title="Nombre d'écritures par compte",
                kind="bar",
                metric="entry_count",
                labels=count_labels,
                values=count_values,
                series_name="Ecritures",
                metadata={"dimension": "account"},
            ),
        )
    return charts


def _field_amount_charts(
    aggregations: dict[str, object],
) -> list[AgentDashboardChartResponse]:
    charts: list[AgentDashboardChartResponse] = []
    field_specs = (
        ("period", "amount_by_period", "Montants par période", "line", "Montant"),
        ("period", "entries_by_period", "Ecritures par période", "line", "Ecritures"),
        (
            "document_type",
            "amount_by_document_type",
            "Montants par type de pièce",
            "doughnut",
            "Montant",
        ),
        (
            "tax_code",
            "amount_by_tax_code",
            "Montants par code TVA",
            "doughnut",
            "Montant",
        ),
        (
            "vendor",
            "top_vendors_by_amount",
            "Top fournisseurs par montant",
            "horizontal_bar",
            "Montant",
        ),
        (
            "customer",
            "top_customers_by_amount",
            "Top clients par montant",
            "horizontal_bar",
            "Montant",
        ),
    )
    for field_name, chart_id, title, kind, series_name in field_specs:
        groups = _aggregation_groups(aggregations, field_name)
        if not groups:
            continue
        sorted_groups = (
            _sort_period_groups(groups) if field_name == "period" else groups
        )
        metric = "entry_count" if chart_id == "entries_by_period" else "amount_sum"
        labels, values = (
            _period_labels_and_values(sorted_groups, metric)
            if field_name == "period"
            else _group_labels_and_values(sorted_groups, metric)
        )
        if not labels:
            continue
        charts.append(
            _chart(
                chart_id=chart_id,
                title=title,
                kind=kind,
                metric=metric,
                labels=labels,
                values=values,
                series_name=series_name,
                metadata={
                    "dimension": field_name,
                    "currencies": _group_currencies(sorted_groups),
                    "currency": _common_group_currency(sorted_groups),
                },
            ),
        )
    return charts


def _quality_charts(quality: dict[str, object]) -> list[AgentDashboardChartResponse]:
    severity_counts = _dict_value(quality.get("severity_counts"))
    labels: list[str] = []
    values: list[float | int] = []
    for severity in ("error", "warning", "info"):
        raw_count = severity_counts.get(severity)
        if isinstance(raw_count, int | float):
            labels.append(severity)
            values.append(raw_count)
    if not labels:
        return []
    return [
        _chart(
            chart_id="data_quality_by_severity",
            title="Qualité des données par sévérité",
            kind="doughnut",
            metric="issue_count",
            labels=labels,
            values=values,
            series_name="Anomalies",
            metadata={"dimension": "severity"},
        ),
    ]


def _tax_candidate_charts(
    tax_candidates: dict[str, object],
) -> list[AgentDashboardChartResponse]:
    candidates = _list_value(tax_candidates.get("candidates"))
    labels: list[str] = []
    amount_values: list[float | int] = []
    count_values: list[float | int] = []
    currencies: list[str] = []
    for candidate in candidates:
        category = candidate.get("category")
        entry_count = candidate.get("entry_count")
        amounts_by_currency = _dict_value(candidate.get("amounts_by_currency"))
        if not isinstance(category, str) or not isinstance(entry_count, int | float):
            continue
        for currency, amount in amounts_by_currency.items():
            if not isinstance(amount, int | float):
                continue
            labels.append(category)
            amount_values.append(amount)
            count_values.append(entry_count)
            currencies.append(currency)
    if not labels:
        return []
    return [
        AgentDashboardChartResponse(
            chart_id="tax_candidates_by_amount",
            title="Candidats fiscaux par montant",
            kind="bar",
            metric="amount_sum",
            labels=labels,
            values=amount_values,
            series=[
                {"name": "Montant", "values": amount_values},
                {"name": "Ecritures", "values": count_values},
            ],
            metadata={
                "dimension": "tax_candidate_category",
                "decision_status": tax_candidates.get("decision_status"),
                "currencies": currencies,
            },
        ),
    ]


def _dict_value(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _currency_metrics(value: object) -> dict[str, dict[str, float | int]]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, dict[str, float | int]] = {}
    for currency, raw_metrics in value.items():
        if not isinstance(currency, str) or not isinstance(raw_metrics, dict):
            continue
        output[currency] = {
            str(metric): amount
            for metric, amount in raw_metrics.items()
            if isinstance(amount, int | float)
        }
    return output


def _list_value(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _aggregation_groups(
    aggregations: dict[str, object],
    field_name: str,
) -> list[dict[str, object]]:
    aggregation = _dict_value(aggregations.get(field_name))
    return _list_value(aggregation.get("groups"))


def _group_labels_and_values(
    groups: list[dict[str, object]],
    metric: str,
) -> tuple[list[str], list[float | int]]:
    labels: list[str] = []
    values: list[float | int] = []
    for group in groups:
        key = group.get("key")
        value = group.get(metric)
        if isinstance(key, str) and isinstance(value, int | float):
            labels.append(key)
            values.append(value)
    return labels, values


def _group_currencies(groups: list[dict[str, object]]) -> list[str | None]:
    return [
        str(group["currency"]) if group.get("currency") is not None else None
        for group in groups
    ]


def _common_group_currency(groups: list[dict[str, object]]) -> str | None:
    currencies = {
        str(group["currency"]) for group in groups if group.get("currency") is not None
    }
    return next(iter(currencies)) if len(currencies) == 1 else None


def _period_labels_and_values(
    groups: list[dict[str, object]],
    metric: str,
) -> tuple[list[str], list[float | int]]:
    values_by_period: dict[int, float | int] = {}
    for group in groups:
        period = _period_int(group.get("key"))
        value = group.get(metric)
        if period is not None and isinstance(value, int | float):
            values_by_period[period] = value
    return (
        [str(period) for period in range(1, 13)],
        [values_by_period.get(period, 0) for period in range(1, 13)],
    )


def _sort_period_groups(
    groups: list[dict[str, object]],
) -> list[dict[str, object]]:
    return sorted(groups, key=lambda group: _period_sort_key(group.get("key")))


def _period_sort_key(value: object) -> tuple[int, str]:
    try:
        return (0, f"{int(float(str(value))):02d}")
    except ValueError:
        return (1, str(value))


def _period_int(value: object) -> int | None:
    try:
        period = int(float(str(value)))
    except ValueError:
        return None
    return period if 1 <= period <= 12 else None


def _chart(
    chart_id: str,
    title: str,
    kind: str,
    metric: str,
    labels: list[str],
    values: list[float | int],
    series_name: str,
    metadata: dict[str, object],
) -> AgentDashboardChartResponse:
    return AgentDashboardChartResponse(
        chart_id=chart_id,
        title=title,
        kind=kind,
        metric=metric,
        labels=labels,
        values=values,
        series=[{"name": series_name, "values": values}],
        metadata=metadata,
    )
