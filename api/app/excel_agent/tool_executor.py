from pathlib import Path

from app.account_mapping.classifier import ClassificationRule
from app.account_mapping.rule_loader import load_classification_rules
from app.excel_agent.domain import (
    ExcelAgentError,
    ExcelColumnList,
    ExcelColumnProfile,
    ExcelSheetList,
    ExcelSheetProfile,
    ToolExecutionResult,
    ValidatedToolCall,
)
from app.excel_agent.excel_tools import ExcelAgentTools
from app.excel_agent.tool_registry import AgentToolRegistry
from app.excel_agent.tool_validator import ToolCallValidationError, ToolCallValidator
from app.ledger_analysis.account_balance_rules import (
    AccountBalanceRule,
    load_account_balance_rules,
)
from app.ledger_analysis.analysis_service import (
    LedgerAggregationReport,
    LedgerAnalysisReport,
    LedgerAnalysisService,
    LedgerDataQualityReport,
    LedgerFieldAggregation,
    LedgerMetricsReport,
    LedgerQueryReport,
    LedgerSchemaClassificationReport,
    LedgerTaxCandidateReport,
)
from app.ledger_analysis.posting_key_rules import (
    PostingKeyRule,
    load_posting_key_rules,
)
from app.ledger_analysis.schema_classifier import LedgerSchemaClassification
from app.ledger_analysis.schema_validator import LedgerSchemaValidationError
from app.llm.domain import ModelToolDefinition, ToolCall

QUERY_FILTER_NAMES = {
    "account",
    "period",
    "fiscal_year",
    "tax_code",
    "vendor",
    "customer",
    "amount_min",
    "amount_max",
}

ToolResult = (
    ExcelSheetList
    | ExcelColumnList
    | ExcelSheetProfile
    | LedgerSchemaClassificationReport
    | LedgerAnalysisReport
    | LedgerAggregationReport
    | LedgerQueryReport
    | LedgerMetricsReport
    | LedgerDataQualityReport
    | LedgerTaxCandidateReport
)


class ExcelToolExecutor:
    def __init__(
        self,
        tools: ExcelAgentTools,
        registry: AgentToolRegistry,
        tax_candidate_rules: tuple[ClassificationRule, ...] | None = None,
        posting_key_rules: tuple[PostingKeyRule, ...] | None = None,
        account_balance_rules: tuple[AccountBalanceRule, ...] | None = None,
    ) -> None:
        self._tools = tools
        self._ledger_analysis_service = LedgerAnalysisService(
            excel_tools=tools,
            tax_candidate_rules=(
                tax_candidate_rules
                if tax_candidate_rules is not None
                else _load_default_tax_candidate_rules()
            ),
            posting_key_rules=(
                posting_key_rules
                if posting_key_rules is not None
                else _load_default_posting_key_rules()
            ),
            account_balance_rules=(
                account_balance_rules
                if account_balance_rules is not None
                else _load_default_account_balance_rules()
            ),
        )
        self._validator = ToolCallValidator(registry=registry)

    def validate(self, tool_call: ToolCall) -> ValidatedToolCall:
        return self._validator.validate(tool_call)

    def get_model_tool_definitions(
        self,
        allowed_tools: tuple[str, ...],
    ) -> tuple[ModelToolDefinition, ...]:
        definitions: list[ModelToolDefinition] = []
        for tool_name in allowed_tools:
            definition = self._validator.get_tool_definition(tool_name)
            if definition is None:
                continue
            definitions.append(
                ModelToolDefinition(
                    name=definition.name,
                    description=definition.description,
                    input_schema=definition.input_schema,
                ),
            )
        return tuple(definitions)

    def execute(self, tool_call: ToolCall) -> ToolExecutionResult:
        try:
            validated_call = self._validator.validate(tool_call)
            result: ToolResult
            if validated_call.name == "list_sheets":
                result = self._tools.list_sheets(
                    Path(str(validated_call.arguments["file_path"])),
                )
            elif validated_call.name == "get_columns":
                result = self._tools.get_columns(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                )
            elif validated_call.name == "profile_sheet":
                result = self._tools.profile_sheet(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                )
            elif validated_call.name == "classify_ledger_schema":
                result = self._ledger_analysis_service.classify_schema(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                )
            elif validated_call.name == "analyze_ledger":
                result = self._ledger_analysis_service.analyze(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                )
            elif validated_call.name == "aggregate_ledger":
                filters = _query_filters(validated_call.arguments.get("filters"))
                if filters is None:
                    return _failed(
                        tool_call.name,
                        "invalid_filter",
                        "aggregation filter is invalid",
                    )
                result = self._ledger_analysis_service.aggregate(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                    group_by=_optional_string_tuple(
                        validated_call.arguments.get("group_by"),
                        default=("account", "period", "tax_code"),
                    ),
                    limit=_optional_positive_int(
                        validated_call.arguments.get("limit"),
                        default=10,
                        maximum=50,
                    ),
                    filters=filters,
                )
            elif validated_call.name == "query_ledger_entries":
                filters = _query_filters(validated_call.arguments.get("filters"))
                if filters is None:
                    return _failed(
                        tool_call.name,
                        "invalid_filter",
                        "query filter is invalid",
                    )
                result = self._ledger_analysis_service.query_entries(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                    filters=filters,
                    page=_optional_positive_int(
                        validated_call.arguments.get("page"),
                        default=1,
                        maximum=10_000,
                    ),
                    page_size=_optional_positive_int(
                        validated_call.arguments.get("page_size"),
                        default=20,
                        maximum=50,
                    ),
                )
            elif validated_call.name == "calculate_ledger_metrics":
                result = self._ledger_analysis_service.calculate_metrics(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                    filters=_optional_dict(validated_call.arguments.get("filters")),
                    metrics=_optional_string_tuple(
                        validated_call.arguments.get("metrics"),
                        default=("sum", "count", "average", "min", "max"),
                    ),
                    top_by=_optional_string(validated_call.arguments.get("top_by")),
                    top_limit=_optional_positive_int(
                        validated_call.arguments.get("top_limit"),
                        default=10,
                        maximum=50,
                    ),
                )
            elif validated_call.name == "detect_data_quality_issues":
                result = self._ledger_analysis_service.detect_data_quality_issues(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                )
            elif validated_call.name == "detect_tax_candidates":
                result = self._ledger_analysis_service.detect_tax_candidates(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                    limit=_optional_positive_int(
                        validated_call.arguments.get("limit"),
                        default=20,
                        maximum=50,
                    ),
                )
            else:
                return _failed(tool_call.name, "unknown_tool", "unknown tool")
        except ToolCallValidationError as exc:
            return _failed(tool_call.name, "invalid_tool_call", str(exc))
        except LedgerSchemaValidationError as exc:
            return _failed(tool_call.name, "ledger_schema_invalid", str(exc))
        except ExcelAgentError as exc:
            return _failed(tool_call.name, _error_code(exc), str(exc))

        return ToolExecutionResult(
            tool_name=tool_call.name,
            ok=True,
            output=_serialize_result(result),
        )


def _serialize_result(
    result: ToolResult,
) -> dict[str, object]:
    if isinstance(result, ExcelSheetList):
        return {"sheet_names": list(result.sheet_names)}
    if isinstance(result, ExcelColumnList):
        return {
            "sheet_name": result.sheet_name,
            "columns": list(result.columns),
        }
    if isinstance(result, ExcelSheetProfile):
        return {
            "sheet_name": result.sheet_name,
            "row_count": result.row_count,
            "column_count": result.column_count,
            "columns": [_serialize_column(column) for column in result.columns],
        }
    if isinstance(result, LedgerSchemaClassificationReport):
        return {
            "sheet_name": result.sheet_name,
            "row_count": result.row_count,
            "column_count": result.column_count,
            "schema": _serialize_classification(result.classification),
            "columns": [_serialize_column(column) for column in result.columns],
        }
    if isinstance(result, LedgerAggregationReport):
        return {
            "sheet_name": result.sheet_name,
            "row_count": result.row_count,
            "amount_field": result.amount_field,
            "aggregations": {
                aggregation.canonical_field: {
                    "source_column": aggregation.source_column,
                    "total_groups": aggregation.total_groups,
                    "groups": [
                        {
                            "key": group.key,
                            "entry_count": group.entry_count,
                            "amount_sum": group.amount_sum,
                            "currency": group.currency,
                            "used_entry_count": group.used_entry_count,
                            "excluded_entry_count": group.excluded_entry_count,
                            "raw_amount_sum": group.raw_amount_sum,
                            "debit_total": group.debit_total,
                            "credit_total": group.credit_total,
                            "balance": group.balance,
                        }
                        for group in aggregation.groups
                    ],
                }
                for aggregation in result.aggregations
            },
            "sign_convention": result.sign_convention,
            "filters": result.filters,
        }
    if isinstance(result, LedgerQueryReport):
        return {
            "sheet_name": result.sheet_name,
            "total_matches": result.total_matches,
            "page": result.page,
            "page_size": result.page_size,
            "filters": result.filters,
            "returned_columns": list(result.returned_columns),
            "message": result.message,
            "entries": list(result.entries),
            "sign_convention": result.sign_convention,
        }
    if isinstance(result, LedgerMetricsReport):
        return {
            "sheet_name": result.sheet_name,
            "total_matches": result.total_matches,
            "amount_field": result.amount_field,
            "metrics": result.metrics,
            "top": _serialize_field_aggregation(result.top),
            "sign_convention": result.sign_convention,
            "balance_interpretation": result.balance_interpretation,
            "metrics_by_currency": result.metrics_by_currency,
            "filters": result.filters,
            "balance_reconciliation": result.balance_reconciliation,
        }
    if isinstance(result, LedgerDataQualityReport):
        return {
            "sheet_name": result.sheet_name,
            "row_count": result.row_count,
            "issue_count": result.issue_count,
            "severity_counts": result.severity_counts,
            "issues": [
                {
                    "issue_type": issue.issue_type,
                    "severity": issue.severity,
                    "canonical_field": issue.canonical_field,
                    "source_column": issue.source_column,
                    "affected_count": issue.affected_count,
                    "affected_ratio": issue.affected_ratio,
                    "message": issue.message,
                    "affected_accounts": [
                        {
                            "account": account.account,
                            "affected_count": account.affected_count,
                        }
                        for account in issue.affected_accounts
                    ],
                }
                for issue in result.issues
            ],
        }
    if isinstance(result, LedgerTaxCandidateReport):
        return {
            "sheet_name": result.sheet_name,
            "row_count": result.row_count,
            "decision_status": result.decision_status,
            "candidates": [
                {
                    "category": candidate.category,
                    "confidence": candidate.confidence,
                    "entry_count": candidate.entry_count,
                    "amount_sum": candidate.amount_sum,
                    "matched_keywords": list(candidate.matched_keywords),
                    "top_accounts": [
                        {
                            "key": account.key,
                            "entry_count": account.entry_count,
                            "amount_sum": account.amount_sum,
                        }
                        for account in candidate.top_accounts
                    ],
                    "action_required": candidate.action_required,
                    "amounts_by_currency": candidate.amounts_by_currency,
                }
                for candidate in result.candidates
            ],
            "sign_convention": result.sign_convention,
        }
    return {
        "sheet_name": result.sheet_name,
        "row_count": result.row_count,
        "column_count": result.column_count,
        "schema": {
            "is_valid": result.schema_report.is_valid,
            "present_columns": list(result.schema_report.present_columns),
            "missing_required_columns": list(
                result.schema_report.missing_required_columns,
            ),
            "optional_columns": list(result.schema_report.optional_columns),
            "canonical_schema": _serialize_classification(result.canonical_schema),
        },
        "columns": [_serialize_column(column) for column in result.columns],
    }


def _serialize_classification(
    classification: LedgerSchemaClassification,
) -> dict[str, object]:
    return {
        "is_usable": classification.is_usable,
        "requires_confirmation": classification.requires_confirmation,
        "fields": {
            mapping.canonical_field: mapping.source_column
            for mapping in classification.mappings
            if mapping.status == "mapped"
        },
        "mappings": [
            {
                "canonical_field": mapping.canonical_field,
                "source_column": mapping.source_column,
                "confidence": mapping.confidence,
                "status": mapping.status,
                "reason": mapping.reason,
            }
            for mapping in classification.mappings
        ],
    }


def _serialize_column(column: ExcelColumnProfile) -> dict[str, object]:
    return {
        "name": column.name,
        "position": column.position,
        "detected_type": column.detected_type,
        "non_empty_count": column.non_empty_count,
        "missing_count": column.missing_count,
        "missing_ratio": column.missing_ratio,
    }


def _failed(tool_name: str, error_code: str, message: str) -> ToolExecutionResult:
    return ToolExecutionResult(
        tool_name=tool_name,
        ok=False,
        output={},
        error_code=error_code,
        error_message=message,
    )


def _error_code(error: ExcelAgentError) -> str:
    error_name = type(error).__name__
    return "".join(
        f"_{character.lower()}" if character.isupper() else character
        for character in error_name.removesuffix("Error")
    ).lstrip("_")


def _serialize_field_aggregation(
    aggregation: LedgerFieldAggregation | None,
) -> dict[str, object] | None:
    if aggregation is None:
        return None
    return {
        "canonical_field": aggregation.canonical_field,
        "source_column": aggregation.source_column,
        "total_groups": aggregation.total_groups,
        "groups": [
            {
                "key": group.key,
                "entry_count": group.entry_count,
                "amount_sum": group.amount_sum,
                "currency": group.currency,
                "used_entry_count": group.used_entry_count,
                "excluded_entry_count": group.excluded_entry_count,
                "raw_amount_sum": group.raw_amount_sum,
                "debit_total": group.debit_total,
                "credit_total": group.credit_total,
                "balance": group.balance,
            }
            for group in aggregation.groups
        ],
    }


def _optional_string_tuple(
    raw_value: object,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    if raw_value is None:
        return default
    if not isinstance(raw_value, list):
        return default
    values = tuple(str(value) for value in raw_value if isinstance(value, str))
    return values or default


def _optional_positive_int(
    raw_value: object,
    default: int,
    maximum: int,
) -> int:
    if not isinstance(raw_value, int):
        return default
    return min(max(1, raw_value), maximum)


def _optional_dict(raw_value: object) -> dict[str, object]:
    if not isinstance(raw_value, dict):
        return {}
    return dict(raw_value)


def _query_filters(raw_value: object) -> dict[str, object] | None:
    filters = _optional_dict(raw_value)
    for filter_name, filter_value in filters.items():
        if filter_name not in QUERY_FILTER_NAMES:
            return None
        if filter_name in {"amount_min", "amount_max"}:
            if not isinstance(filter_value, int | float):
                return None
            continue
        if not isinstance(filter_value, str):
            return None
    return filters


def _optional_string(raw_value: object) -> str | None:
    return raw_value if isinstance(raw_value, str) else None


def _load_default_tax_candidate_rules() -> tuple[ClassificationRule, ...]:
    for rules_path in (
        Path("../docs/reference/ras-classification-rules.csv"),
        Path("docs/reference/ras-classification-rules.csv"),
        Path("/workspace/docs/reference/ras-classification-rules.csv"),
    ):
        if rules_path.is_file():
            return load_classification_rules(rules_path)
    return ()


def _load_default_posting_key_rules() -> tuple[PostingKeyRule, ...]:
    for rules_path in (
        Path("../docs/reference/sap-posting-key-rules.csv"),
        Path("docs/reference/sap-posting-key-rules.csv"),
        Path("/workspace/docs/reference/sap-posting-key-rules.csv"),
    ):
        if rules_path.is_file():
            return load_posting_key_rules(rules_path)
    return ()


def _load_default_account_balance_rules() -> tuple[AccountBalanceRule, ...]:
    for rules_path in (
        Path("../docs/reference/syscohada-account-balance-rules.csv"),
        Path("docs/reference/syscohada-account-balance-rules.csv"),
        Path("/workspace/docs/reference/syscohada-account-balance-rules.csv"),
    ):
        if rules_path.is_file():
            return load_account_balance_rules(rules_path)
    return ()
