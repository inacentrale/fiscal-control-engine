from datetime import date
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from unicodedata import normalize
from uuid import uuid4

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
from app.ras_audit.account_mapping import (
    RasLedgerAccountMapping,
    has_expense_candidate_mapping,
    has_ras_payable_mapping,
)
from app.ras_audit.accounting_assessment import (
    RasAccountingAssessmentPolicy,
    RasAccountingAssessmentToolReport,
    RasAccountingAssessor,
)
from app.ras_audit.accounting_entry import (
    AccountingEntryReconstructionToolReport,
    AccountingEntryReconstructor,
    ReconstructedAccountingEntry,
)
from app.ras_audit.audit_derivation import (
    RasAuditDerivationError,
    RasAuditDerivationService,
)
from app.ras_audit.audit_report import (
    RasAuditReport,
    RasAuditReportCase,
    RasAuditReportDetail,
    RasAuditReportGenerator,
)
from app.ras_audit.batch_audit import RasBatchAuditResult, RasBatchAuditService
from app.ras_audit.candidate_detection import (
    RasCandidateDetectionReport,
    RasCandidateDetectionToolReport,
    RasCandidateDetector,
    candidate_requires_category_split,
)
from app.ras_audit.candidate_signals import (
    RasCandidateSignal,
    load_ras_candidate_signals,
)
from app.ras_audit.column_aliases import (
    LedgerColumnAlias,
    load_ledger_column_aliases,
    resolve_ledger_columns,
)
from app.ras_audit.counterpart import (
    RasCounterpartAmount,
    RasCounterpartFinder,
    RasCounterpartStatus,
    RasCounterpartToolReport,
)
from app.ras_audit.domain import CanonicalLedgerEntry, LedgerField
from app.ras_audit.fact_context import (
    RasFactContextAttestor,
    RasFactContextError,
    RasVerifiedFactContext,
)
from app.ras_audit.legal_rules import RasLegalRule
from app.ras_audit.normalization import (
    LedgerColumnBinding,
    LedgerNormalizationReport,
    LedgerNormalizationRequest,
    LedgerNormalizer,
)
from app.ras_audit.persisted_report import (
    PersistedRasAuditReportError,
    PersistedRasAuditReportService,
)
from app.ras_audit.persistence import (
    RasAuditCaseSnapshot,
    RasAuditSnapshot,
    SqlAlchemyRasAuditRepository,
)
from app.ras_audit.rule_resolution import (
    RasFactSource,
    RasLegalFact,
    RasRuleResolution,
    RasRuleResolutionRequest,
    RasRuleResolver,
)
from app.ras_audit.semantic_classifier import (
    RasSemanticClassificationToolReport,
    RasTransactionSemanticClassifier,
    SemanticClassificationStatus,
)
from app.ras_audit.source_scope import assess_uploaded_sheet_scope
from app.ras_audit.tax_event_rules import RasTaxEventRule
from app.ras_audit.tax_rag_query import TaxRagQueryResult, TaxRagQueryService
from app.ras_audit.theoretical_calculation import (
    RasCalculationParameter,
    RasTheoreticalCalculationToolReport,
    RasTheoreticalCalculator,
)

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
QUERY_FILTER_ALIASES = {
    "account_number": "account",
    "compte": "account",
    "numero_compte": "account",
    "numero_de_compte": "account",
    "n_compte": "account",
    "periode": "period",
    "exercise": "fiscal_year",
    "exercice": "fiscal_year",
    "annee": "fiscal_year",
    "year": "fiscal_year",
    "code_tva": "tax_code",
    "tva": "tax_code",
    "fournisseur": "vendor",
    "vendeur": "vendor",
    "client": "customer",
    "montant_min": "amount_min",
    "montant_minimum": "amount_min",
    "montant_max": "amount_max",
    "montant_maximum": "amount_max",
}
RAS_DETECTION_FILTER_NAMES = {
    "account",
    "period",
    "fiscal_year",
    "currency",
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
    | LedgerNormalizationReport
    | AccountingEntryReconstructionToolReport
    | RasCounterpartToolReport
    | RasCandidateDetectionToolReport
    | RasSemanticClassificationToolReport
    | RasRuleResolution
    | RasTheoreticalCalculationToolReport
    | RasAccountingAssessmentToolReport
    | RasAuditReport
    | TaxRagQueryResult
    | RasBatchAuditResult
)


class ExcelToolExecutor:
    def __init__(
        self,
        tools: ExcelAgentTools,
        registry: AgentToolRegistry,
        tax_candidate_rules: tuple[ClassificationRule, ...] | None = None,
        posting_key_rules: tuple[PostingKeyRule, ...] | None = None,
        account_balance_rules: tuple[AccountBalanceRule, ...] | None = None,
        ledger_column_aliases: tuple[LedgerColumnAlias, ...] | None = None,
        ras_ledger_account_mappings: tuple[RasLedgerAccountMapping, ...] = (),
        ras_candidate_signals: tuple[RasCandidateSignal, ...] | None = None,
        ras_semantic_classifier: RasTransactionSemanticClassifier | None = None,
        ras_legal_rules: tuple[RasLegalRule, ...] = (),
        ras_tax_event_rules: tuple[RasTaxEventRule, ...] = (),
        ras_calculation_parameters: tuple[RasCalculationParameter, ...] = (),
        ras_accounting_assessment_policies: tuple[
            RasAccountingAssessmentPolicy, ...
        ] = (),
        ras_fact_context_attestor: RasFactContextAttestor | None = None,
        ras_audit_repository: SqlAlchemyRasAuditRepository | None = None,
        tax_rag_query_service: TaxRagQueryService | None = None,
        max_ras_batch_candidates: int = 5_000,
        default_company_code: str | None = None,
    ) -> None:
        if not 1 <= max_ras_batch_candidates <= 20_000:
            raise ValueError("max_ras_batch_candidates must be between 1 and 20000")
        self._tools = tools
        resolved_posting_key_rules = (
            posting_key_rules
            if posting_key_rules is not None
            else _load_default_posting_key_rules()
        )
        self._posting_key_rules = resolved_posting_key_rules
        self._ledger_column_aliases = (
            ledger_column_aliases
            if ledger_column_aliases is not None
            else _load_default_ledger_column_aliases()
        )
        self._ras_ledger_account_mappings = ras_ledger_account_mappings
        self._ras_candidate_signals = (
            ras_candidate_signals
            if ras_candidate_signals is not None
            else _load_default_ras_candidate_signals()
        )
        self._ras_semantic_classifier = ras_semantic_classifier
        self._ras_legal_rules = ras_legal_rules
        self._ras_tax_event_rules = ras_tax_event_rules
        self._ras_calculation_parameters = ras_calculation_parameters
        self._ras_accounting_assessment_policies = ras_accounting_assessment_policies
        self._ras_fact_context_attestor = ras_fact_context_attestor
        self._ras_audit_repository = ras_audit_repository
        self._tax_rag_query_service = tax_rag_query_service
        self._max_ras_batch_candidates = max_ras_batch_candidates
        self._default_company_code = (
            default_company_code.strip() if default_company_code else None
        )
        self._ledger_analysis_service = LedgerAnalysisService(
            excel_tools=tools,
            tax_candidate_rules=(
                tax_candidate_rules
                if tax_candidate_rules is not None
                else _load_default_tax_candidate_rules()
            ),
            posting_key_rules=resolved_posting_key_rules,
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

    def execute(
        self,
        tool_call: ToolCall,
        *,
        ras_fact_context_token: str | None = None,
    ) -> ToolExecutionResult:
        persisted_audit_id: str | None = None
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
            elif validated_call.name == "resolve_applicable_ras_rule":
                if not self._ras_legal_rules or not self._ras_tax_event_rules:
                    return _failed(
                        tool_call.name,
                        "ras_legal_rules_unavailable",
                        "RAS legal rule or tax event matrix is unavailable",
                    )
                trusted_context = self._verified_ras_context(ras_fact_context_token)
                if trusted_context is None:
                    return _failed(
                        tool_call.name,
                        "ras_fact_context_required",
                        "a valid server-attested RAS fact context is required",
                    )
                legal_request = _ras_rule_resolution_request(
                    validated_call.arguments,
                    trusted_context.facts,
                )
                if legal_request is None:
                    return _failed(
                        tool_call.name,
                        "invalid_legal_facts",
                        "RAS legal facts or transaction date are invalid",
                    )
                result = RasRuleResolver(
                    self._ras_legal_rules,
                    self._ras_tax_event_rules,
                ).resolve(legal_request)
            elif validated_call.name == "calculate_theoretical_ras":
                if (
                    not self._ras_legal_rules
                    or not self._ras_tax_event_rules
                    or not self._ras_calculation_parameters
                ):
                    return _failed(
                        tool_call.name,
                        "ras_calculation_reference_unavailable",
                        "RAS legal rules or calculation parameters are unavailable",
                    )
                trusted_context = self._verified_ras_context(ras_fact_context_token)
                if trusted_context is None:
                    return _failed(
                        tool_call.name,
                        "ras_fact_context_required",
                        "a valid server-attested RAS fact context is required",
                    )
                calculation_request = _ras_rule_resolution_request(
                    validated_call.arguments,
                    trusted_context.facts,
                )
                if calculation_request is None:
                    return _failed(
                        tool_call.name,
                        "invalid_legal_facts",
                        "RAS legal facts or transaction date are invalid",
                    )
                calculation_resolution = RasRuleResolver(
                    self._ras_legal_rules,
                    self._ras_tax_event_rules,
                ).resolve(calculation_request)
                result = RasTheoreticalCalculationToolReport(
                    resolution=calculation_resolution,
                    calculation=RasTheoreticalCalculator(
                        rules=self._ras_legal_rules,
                        parameters=self._ras_calculation_parameters,
                    ).calculate(
                        transaction_date=calculation_request.transaction_date,
                        facts=calculation_request.facts,
                        resolution=calculation_resolution,
                    ),
                )
            elif validated_call.name == "generate_ras_audit_report":
                if self._ras_audit_repository is None:
                    return _failed(
                        tool_call.name,
                        "ras_audit_repository_unavailable",
                        "RAS audit persistence is unavailable",
                    )
                trusted_context = self._verified_ras_context(ras_fact_context_token)
                if trusted_context is None:
                    return _failed(
                        tool_call.name,
                        "ras_fact_context_required",
                        "a valid server-attested RAS context is required",
                    )
                audit_id = validated_call.arguments.get("audit_id")
                if not isinstance(audit_id, str) or not audit_id.strip():
                    return _failed(
                        tool_call.name,
                        "invalid_audit_id",
                        "RAS audit identifier is invalid",
                    )
                access_error = self._validate_audit_access(
                    audit_id=audit_id,
                    fact_context=trusted_context,
                )
                if access_error is not None:
                    return _failed(
                        tool_call.name,
                        access_error[0],
                        access_error[1],
                    )
                try:
                    result = PersistedRasAuditReportService(
                        self._ras_audit_repository
                    ).generate(audit_id)
                except PersistedRasAuditReportError as exc:
                    return _failed(
                        tool_call.name,
                        "ras_audit_report_unavailable",
                        str(exc),
                    )
            elif validated_call.name == "query_tax_rag":
                if self._tax_rag_query_service is None:
                    return _failed(
                        tool_call.name,
                        "tax_rag_unavailable",
                        "validated tax RAG sources are unavailable",
                    )
                raw_query = validated_call.arguments.get("query")
                raw_as_of_date = validated_call.arguments.get("as_of_date")
                raw_limit = validated_call.arguments.get("limit", 5)
                if (
                    not isinstance(raw_query, str)
                    or not isinstance(raw_limit, int)
                    or isinstance(raw_limit, bool)
                    or raw_as_of_date is not None
                    and not isinstance(raw_as_of_date, str)
                ):
                    return _failed(
                        tool_call.name,
                        "invalid_tax_rag_query",
                        "tax RAG query arguments are invalid",
                    )
                try:
                    result = self._tax_rag_query_service.query(
                        raw_query,
                        limit=raw_limit,
                        as_of_date=(
                            date.fromisoformat(raw_as_of_date)
                            if raw_as_of_date is not None
                            else None
                        ),
                    )
                except ValueError as exc:
                    return _failed(
                        tool_call.name,
                        "invalid_tax_rag_query",
                        str(exc),
                    )
            elif validated_call.name in {
                "normalize_gl",
                "assess_gl_readiness",
                "reconstruct_accounting_entry",
                "find_ras_counterpart",
                "detect_ras_candidates",
                "classify_transaction_semantics",
                "assess_ras_accounting",
                "run_ras_audit_batch",
            }:
                raw_window = validated_call.arguments.get("related_window_days")
                if not _optional_boolean_is_valid(
                    validated_call.arguments,
                    "source_scope_complete",
                ):
                    return _failed(
                        tool_call.name,
                        "invalid_tool_call",
                        "normalization flags must be booleans",
                    )
                if (
                    validated_call.name
                    in {"find_ras_counterpart", "assess_ras_accounting"}
                    and raw_window is not None
                    and (
                        not isinstance(raw_window, int)
                        or isinstance(raw_window, bool)
                        or not 0 <= raw_window <= 366
                    )
                ):
                    return _failed(
                        tool_call.name,
                        "invalid_tool_call",
                        "related_window_days must be between 0 and 366",
                    )
                sheet_rows = self._tools.read_sheet_rows(
                    Path(str(validated_call.arguments["file_path"])),
                    sheet_name=str(validated_call.arguments["sheet_name"]),
                )
                raw_mapping = validated_call.arguments.get("column_mapping")
                if isinstance(raw_mapping, dict) and not raw_mapping:
                    raw_mapping = None
                if raw_mapping is None:
                    if not self._ledger_column_aliases:
                        return _failed(
                            tool_call.name,
                            "column_alias_reference_unavailable",
                            "ledger column alias reference is unavailable",
                        )
                    resolution = resolve_ledger_columns(
                        sheet_rows.columns,
                        self._ledger_column_aliases,
                    )
                    if resolution.ambiguities:
                        ambiguity_details = "; ".join(
                            f"{ambiguity.field.value}="
                            f"{','.join(ambiguity.source_columns)}"
                            for ambiguity in resolution.ambiguities
                        )
                        return _failed(
                            tool_call.name,
                            "ambiguous_column_mapping",
                            f"ambiguous automatic column mapping: {ambiguity_details}",
                        )
                    bindings = resolution.bindings
                else:
                    explicit_bindings = _normalization_bindings(raw_mapping)
                    if explicit_bindings is None:
                        return _failed(
                            tool_call.name,
                            "invalid_column_mapping",
                            "explicit ledger column mapping is invalid",
                        )
                    bindings = explicit_bindings
                if not bindings:
                    return _failed(
                        tool_call.name,
                        "invalid_column_mapping",
                        "no unambiguous ledger column mapping is available",
                    )
                try:
                    normalization_report = LedgerNormalizer().normalize(
                        LedgerNormalizationRequest(
                            source_file_name=sheet_rows.file_path.name,
                            content_sha256=sheet_rows.content_sha256,
                            sheet_name=sheet_rows.sheet_name,
                            first_data_row=2,
                            source_columns=sheet_rows.columns,
                            rows=sheet_rows.rows,
                            bindings=bindings,
                            known_posting_keys=frozenset(
                                rule.posting_key for rule in self._posting_key_rules
                            ),
                            source_scope_complete=_optional_boolean(
                                validated_call.arguments.get("source_scope_complete"),
                            ),
                            ras_account_mappings=self._ras_ledger_account_mappings,
                            default_company_code=self._default_company_code,
                        ),
                    )
                    if validated_call.name in {
                        "reconstruct_accounting_entry",
                        "find_ras_counterpart",
                        "detect_ras_candidates",
                        "classify_transaction_semantics",
                        "assess_ras_accounting",
                        "run_ras_audit_batch",
                    }:
                        reconstruction = AccountingEntryReconstructor(
                            self._posting_key_rules
                        ).reconstruct(normalization_report.entries)
                    if validated_call.name == "reconstruct_accounting_entry":
                        raw_selector = validated_call.arguments.get("entry_selector")
                        selector = _reconstruction_entry_selector(raw_selector)
                        if raw_selector is not None and selector is None:
                            return _failed(
                                tool_call.name,
                                "invalid_accounting_entry_selector",
                                "accounting entry selector is invalid",
                            )
                        selected_entry = _select_reconstructed_entry(
                            reconstruction.entries,
                            selector,
                        )
                        selected_line_ids = (
                            set(selected_entry.line_ids)
                            if selected_entry is not None
                            else set()
                        )
                        result = AccountingEntryReconstructionToolReport(
                            sheet_name=normalization_report.sheet_name,
                            source_row_count=(
                                len(normalization_report.entries)
                                + len(normalization_report.rejected_rows)
                            ),
                            normalized_issue_codes=tuple(
                                issue.code for issue in normalization_report.issues
                            ),
                            rejected_row_count=len(normalization_report.rejected_rows),
                            reconstruction=reconstruction,
                            selected_entry=selected_entry,
                            selected_lines=tuple(
                                entry
                                for entry in normalization_report.entries
                                if entry.line_id in selected_line_ids
                            ),
                            selector=selector,
                        )
                    elif validated_call.name == "find_ras_counterpart":
                        if not has_expense_candidate_mapping(
                            self._ras_ledger_account_mappings
                        ) or not has_ras_payable_mapping(
                            self._ras_ledger_account_mappings
                        ):
                            return _failed(
                                tool_call.name,
                                "ras_account_mapping_unavailable",
                                "expense and RAS payable mappings are required",
                            )
                        scope = assess_uploaded_sheet_scope(
                            normalization=normalization_report,
                            reconstruction=reconstruction,
                            posting_key_rules=self._posting_key_rules,
                            account_mappings=self._ras_ledger_account_mappings,
                        )
                        source_scope_complete = scope.is_complete
                        detected_candidate_piece_count = (
                            len(
                                RasCandidateDetector(
                                    posting_key_rules=self._posting_key_rules,
                                    account_mappings=(
                                        self._ras_ledger_account_mappings
                                    ),
                                    signals=self._ras_candidate_signals,
                                    semantic_classifier=(
                                        self._ras_semantic_classifier
                                    ),
                                )
                                .detect(
                                    ledger_entries=normalization_report.entries,
                                    reconstruction=reconstruction,
                                )
                                .candidates
                            )
                            if self._ras_candidate_signals
                            else None
                        )
                        result = RasCounterpartToolReport(
                            sheet_name=normalization_report.sheet_name,
                            source_row_count=(
                                len(normalization_report.entries)
                                + len(normalization_report.rejected_rows)
                            ),
                            rejected_row_count=len(normalization_report.rejected_rows),
                            normalization_issue_codes=tuple(
                                issue.code for issue in normalization_report.issues
                            ),
                            source_scope_complete=source_scope_complete,
                            source_scope_blockers=scope.blocker_codes,
                            source_scope_policy_version=scope.policy_version,
                            detected_candidate_piece_count=(
                                detected_candidate_piece_count
                            ),
                            report=RasCounterpartFinder(
                                posting_key_rules=self._posting_key_rules,
                                account_mappings=self._ras_ledger_account_mappings,
                                related_window_days=(
                                    int(raw_window) if raw_window is not None else 31
                                ),
                            ).find(
                                ledger_entries=normalization_report.entries,
                                reconstruction=reconstruction,
                                source_scope_complete=source_scope_complete,
                            ),
                        )
                    elif validated_call.name == "detect_ras_candidates":
                        if not has_expense_candidate_mapping(
                            self._ras_ledger_account_mappings
                        ):
                            return _failed(
                                tool_call.name,
                                "ras_expense_mapping_unavailable",
                                "expense candidate account mappings are required",
                            )
                        if not self._ras_candidate_signals:
                            return _failed(
                                tool_call.name,
                                "ras_candidate_signal_reference_unavailable",
                                "RAS candidate signal reference is unavailable",
                            )
                        filters = _ras_detection_filters(
                            validated_call.arguments.get("filters")
                        )
                        if filters is None:
                            return _failed(
                                tool_call.name,
                                "invalid_filter",
                                "RAS candidate filter is invalid",
                            )
                        filtered_entries = _filter_ras_detection_entries(
                            normalization_report.entries,
                            filters,
                        )
                        filtered_line_ids = {
                            entry.line_id for entry in filtered_entries
                        }
                        filtered_issue_codes = tuple(
                            issue.code
                            for issue in normalization_report.issues
                            if issue.line_id in filtered_line_ids
                        )
                        filtered_reconstruction = AccountingEntryReconstructor(
                            self._posting_key_rules
                        ).reconstruct(filtered_entries)
                        result = RasCandidateDetectionToolReport(
                            sheet_name=normalization_report.sheet_name,
                            source_row_count=(
                                len(normalization_report.entries)
                                + len(normalization_report.rejected_rows)
                            ),
                            filtered_row_count=len(filtered_entries),
                            filters=filters,
                            rejected_row_count=(
                                len(normalization_report.rejected_rows)
                                if not filters
                                else 0
                            ),
                            normalization_issue_codes=filtered_issue_codes,
                            ledger_entries=filtered_entries,
                            reconstruction=filtered_reconstruction,
                            report=RasCandidateDetector(
                                posting_key_rules=self._posting_key_rules,
                                account_mappings=self._ras_ledger_account_mappings,
                                signals=self._ras_candidate_signals,
                                semantic_classifier=self._ras_semantic_classifier,
                            ).detect(
                                ledger_entries=filtered_entries,
                                reconstruction=filtered_reconstruction,
                            ),
                        )
                    elif validated_call.name == "classify_transaction_semantics":
                        if self._ras_semantic_classifier is None:
                            return _failed(
                                tool_call.name,
                                "ras_semantic_classifier_unavailable",
                                "RAS semantic classification is not configured",
                            )
                        labels_by_line = {
                            entry.line_id: entry.label
                            for entry in normalization_report.entries
                        }
                        piece_labels = tuple(
                            " | ".join(
                                dict.fromkeys(
                                    label
                                    for line_id in entry.line_ids
                                    if (label := labels_by_line.get(line_id))
                                )
                            )
                            or None
                            for entry in reconstruction.entries
                        )
                        result = RasSemanticClassificationToolReport(
                            sheet_name=normalization_report.sheet_name,
                            source_row_count=(
                                len(normalization_report.entries)
                                + len(normalization_report.rejected_rows)
                            ),
                            rejected_row_count=len(normalization_report.rejected_rows),
                            report=self._ras_semantic_classifier.classify(piece_labels),
                        )
                    elif validated_call.name == "run_ras_audit_batch":
                        if (
                            self._ras_audit_repository is None
                            or not has_expense_candidate_mapping(
                                self._ras_ledger_account_mappings
                            )
                            or not has_ras_payable_mapping(
                                self._ras_ledger_account_mappings
                            )
                            or not self._ras_candidate_signals
                        ):
                            return _failed(
                                tool_call.name,
                                "ras_batch_reference_unavailable",
                                "RAS persistence, mappings and candidate signals "
                                "are required",
                            )
                        batch_context = self._verified_ras_context(
                            ras_fact_context_token
                        )
                        if batch_context is None:
                            return _failed(
                                tool_call.name,
                                "ras_fact_context_required",
                                "a valid server-attested RAS context is required",
                            )
                        max_candidates = _optional_positive_int(
                            validated_call.arguments.get("max_candidates"),
                            default=self._max_ras_batch_candidates,
                            maximum=self._max_ras_batch_candidates,
                        )
                        scope = assess_uploaded_sheet_scope(
                            normalization=normalization_report,
                            reconstruction=reconstruction,
                            posting_key_rules=self._posting_key_rules,
                            account_mappings=self._ras_ledger_account_mappings,
                        )
                        source_scope_complete = scope.is_complete
                        detection = RasCandidateDetector(
                            posting_key_rules=self._posting_key_rules,
                            account_mappings=self._ras_ledger_account_mappings,
                            signals=self._ras_candidate_signals,
                            semantic_classifier=self._ras_semantic_classifier,
                        ).detect(
                            ledger_entries=normalization_report.entries,
                            reconstruction=reconstruction,
                        )
                        if len(detection.candidates) > max_candidates:
                            return _failed(
                                tool_call.name,
                                "ras_batch_limit_exceeded",
                                "candidate count exceeds the configured batch limit",
                            )
                        counterpart_report = RasCounterpartFinder(
                            posting_key_rules=self._posting_key_rules,
                            account_mappings=self._ras_ledger_account_mappings,
                            related_window_days=(
                                int(raw_window) if raw_window is not None else 31
                            ),
                        ).find(
                            ledger_entries=normalization_report.entries,
                            reconstruction=reconstruction,
                            source_scope_complete=source_scope_complete,
                        )
                        result = RasBatchAuditService(
                            self._ras_audit_repository
                        ).persist(
                            source_sha256=normalization_report.content_sha256,
                            detection=detection,
                            counterparts=counterpart_report,
                            reference_versions=_batch_reference_versions(
                                self,
                                detection,
                            ),
                            source_scope_complete=source_scope_complete,
                            source_scope_blockers=scope.blocker_codes,
                            source_scope_policy_version=scope.policy_version,
                            session_id=batch_context.session_id,
                            file_id=batch_context.file_id,
                        )
                    elif validated_call.name == "assess_ras_accounting":
                        if (
                            not has_expense_candidate_mapping(
                                self._ras_ledger_account_mappings
                            )
                            or not has_ras_payable_mapping(
                                self._ras_ledger_account_mappings
                            )
                            or not self._ras_legal_rules
                            or not self._ras_tax_event_rules
                            or not self._ras_calculation_parameters
                            or not self._ras_accounting_assessment_policies
                        ):
                            return _failed(
                                tool_call.name,
                                "ras_assessment_reference_unavailable",
                                "RAS mappings, rules, parameters and policy "
                                "are required",
                            )
                        raw_base_audit_id = validated_call.arguments.get(
                            "base_audit_id"
                        )
                        base_audit_id = _optional_non_empty_string(raw_base_audit_id)
                        if raw_base_audit_id is not None and base_audit_id is None:
                            return _failed(
                                tool_call.name,
                                "invalid_base_audit_id",
                                "base RAS audit identifier is invalid",
                            )
                        raw_candidate_id = validated_call.arguments.get("candidate_id")
                        candidate_id = _optional_non_empty_string(raw_candidate_id)
                        raw_selector = validated_call.arguments.get(
                            "accounting_entry"
                        )
                        if raw_candidate_id is not None and candidate_id is None:
                            return _failed(
                                tool_call.name,
                                "invalid_candidate_id",
                                "RAS candidate identifier is invalid",
                            )
                        if candidate_id is not None and raw_selector is not None:
                            return _failed(
                                tool_call.name,
                                "ambiguous_accounting_entry_selector",
                                "provide either candidate_id or accounting_entry",
                            )
                        assessment_selector = _accounting_entry_selector(raw_selector)
                        if candidate_id is None and assessment_selector is None:
                            return _failed(
                                tool_call.name,
                                "invalid_accounting_entry_selector",
                                "candidate_id or accounting entry selector is required",
                            )
                        if candidate_id is not None:
                            candidate_error = self._validate_persisted_candidate(
                                candidate_id=candidate_id,
                                base_audit_id=base_audit_id,
                                source_sha256=normalization_report.content_sha256,
                                fact_context=(
                                    self._verified_ras_context(
                                        ras_fact_context_token
                                    )
                                ),
                            )
                            if candidate_error is not None:
                                return _failed(
                                    tool_call.name,
                                    candidate_error[0],
                                    candidate_error[1],
                                )
                        selected_entry = _select_accounting_entry(
                            reconstruction.entries,
                            candidate_id=candidate_id,
                            selector=assessment_selector,
                        )
                        if selected_entry is None:
                            return _failed(
                                tool_call.name,
                                "accounting_entry_not_found",
                                "selected accounting entry was not found",
                            )
                        assessment_line_ids = frozenset(selected_entry.line_ids)
                        selected_lines = tuple(
                            entry
                            for entry in normalization_report.entries
                            if entry.line_id in assessment_line_ids
                        )
                        posting_dates = {
                            entry.posting_date
                            for entry in selected_lines
                            if entry.posting_date is not None
                        }
                        currencies = {
                            entry.currency
                            for entry in selected_lines
                            if entry.currency is not None
                        }
                        if len(posting_dates) != 1 or len(currencies) != 1:
                            return _failed(
                                tool_call.name,
                                "accounting_entry_date_or_currency_ambiguous",
                                "selected entry must have one posting date "
                                "and currency",
                            )
                        selected_detection = RasCandidateDetector(
                            posting_key_rules=self._posting_key_rules,
                            account_mappings=self._ras_ledger_account_mappings,
                            signals=self._ras_candidate_signals,
                            semantic_classifier=self._ras_semantic_classifier,
                        ).detect(
                            ledger_entries=normalization_report.entries,
                            reconstruction=reconstruction,
                        )
                        selected_candidate = next(
                            (
                                candidate
                                for candidate in selected_detection.candidates
                                if candidate.accounting_entry_id
                                == selected_entry.entry_id
                            ),
                            None,
                        )
                        if (
                            selected_candidate is not None
                            and candidate_requires_category_split(
                                selected_candidate
                            )
                        ):
                            return _failed(
                                tool_call.name,
                                "ras_candidate_requires_category_split",
                                "candidate contains multiple RAS operation categories",
                            )
                        trusted_context = self._verified_ras_context(
                            ras_fact_context_token
                        )
                        if trusted_context is None:
                            return _failed(
                                tool_call.name,
                                "invalid_legal_facts",
                                "RAS legal facts are invalid",
                            )
                        facts = trusted_context.facts
                        entry_currency = next(iter(currencies))
                        supplied_currency = next(
                            (fact.value for fact in facts if fact.name == "currency"),
                            None,
                        )
                        if (
                            supplied_currency is not None
                            and supplied_currency != entry_currency
                        ):
                            return _failed(
                                tool_call.name,
                                "currency_fact_mismatch",
                                "fact currency differs from the selected entry",
                            )
                        if supplied_currency is None:
                            facts += (
                                RasLegalFact(
                                    name="currency",
                                    value=entry_currency,
                                    source=RasFactSource.GL,
                                    evidence_reference=selected_entry.entry_id,
                                ),
                            )
                        event_dates = _attested_tax_event_dates(
                            facts,
                            self._ras_tax_event_rules,
                        )
                        if len(event_dates) > 1:
                            return _failed(
                                tool_call.name,
                                "ambiguous_tax_event_date",
                                "multiple tax event dates apply to the candidate",
                            )
                        transaction_date = (
                            event_dates[0]
                            if event_dates
                            else next(iter(posting_dates))
                        )
                        legal_resolution = RasRuleResolver(
                            self._ras_legal_rules,
                            self._ras_tax_event_rules,
                        ).resolve(
                            RasRuleResolutionRequest(
                                transaction_date=transaction_date,
                                facts=facts,
                            )
                        )
                        theoretical = RasTheoreticalCalculator(
                            rules=self._ras_legal_rules,
                            parameters=self._ras_calculation_parameters,
                        ).calculate(
                            transaction_date=transaction_date,
                            facts=facts,
                            resolution=legal_resolution,
                        )
                        scope = assess_uploaded_sheet_scope(
                            normalization=normalization_report,
                            reconstruction=reconstruction,
                            posting_key_rules=self._posting_key_rules,
                            account_mappings=self._ras_ledger_account_mappings,
                        )
                        source_scope_complete = scope.is_complete
                        counterpart_report = RasCounterpartFinder(
                            posting_key_rules=self._posting_key_rules,
                            account_mappings=self._ras_ledger_account_mappings,
                            related_window_days=(
                                int(raw_window) if raw_window is not None else 31
                            ),
                        ).find(
                            ledger_entries=normalization_report.entries,
                            reconstruction=reconstruction,
                            source_scope_complete=source_scope_complete,
                        )
                        counterpart = next(
                            (
                                item
                                for item in counterpart_report.assessments
                                if item.candidate_entry_id == selected_entry.entry_id
                            ),
                            None,
                        )
                        if counterpart is None:
                            return _failed(
                                tool_call.name,
                                "selected_entry_not_expense_candidate",
                                "selected entry is not a configured expense candidate",
                            )
                        result = RasAccountingAssessmentToolReport(
                            sheet_name=normalization_report.sheet_name,
                            source_row_count=(
                                len(normalization_report.entries)
                                + len(normalization_report.rejected_rows)
                            ),
                            rejected_row_count=len(normalization_report.rejected_rows),
                            source_scope_complete=source_scope_complete,
                            resolution=legal_resolution,
                            calculation=theoretical,
                            assessment=RasAccountingAssessor(
                                self._ras_accounting_assessment_policies
                            ).assess(
                                calculation=theoretical,
                                counterpart=counterpart,
                            ),
                        )
                        if self._ras_audit_repository is not None:
                            try:
                                persisted_audit_id = self._persist_assessment(
                                    file_path=Path(
                                        str(validated_call.arguments["file_path"])
                                    ),
                                    report=result,
                                    fact_context=trusted_context,
                                    base_audit_id=base_audit_id,
                                )
                            except RasAuditDerivationError as exc:
                                return _failed(
                                    tool_call.name,
                                    "ras_audit_derivation_invalid",
                                    str(exc),
                                )
                    else:
                        result = normalization_report
                except ValueError as exc:
                    return _failed(
                        tool_call.name,
                        "normalization_invalid",
                        str(exc),
                    )
            else:
                return _failed(tool_call.name, "unknown_tool", "unknown tool")
        except ToolCallValidationError as exc:
            return _failed(tool_call.name, "invalid_tool_call", str(exc))
        except LedgerSchemaValidationError as exc:
            return _failed(tool_call.name, "ledger_schema_invalid", str(exc))
        except ExcelAgentError as exc:
            error_code = _error_code(exc)
            return _failed(
                tool_call.name,
                error_code,
                _safe_excel_error_message(error_code),
            )

        output = _serialize_result(result, tool_call.name)
        if tool_call.name in {
            "resolve_applicable_ras_rule",
            "calculate_theoretical_ras",
            "assess_ras_accounting",
        }:
            verified_context = self._verified_ras_context(ras_fact_context_token)
            if verified_context is not None:
                output["fact_attestation"] = _fact_attestation_payload(
                    verified_context
                )
        if persisted_audit_id is not None:
            output["audit_id"] = persisted_audit_id
        return ToolExecutionResult(
            tool_name=tool_call.name,
            ok=True,
            output=output,
        )

    def _verified_ras_context(
        self,
        token: str | None,
    ) -> RasVerifiedFactContext | None:
        if self._ras_fact_context_attestor is None or token is None:
            return None
        try:
            return self._ras_fact_context_attestor.verify(token)
        except RasFactContextError:
            return None

    def _persist_assessment(
        self,
        *,
        file_path: Path,
        report: RasAccountingAssessmentToolReport,
        fact_context: RasVerifiedFactContext,
        base_audit_id: str | None,
    ) -> str:
        if self._ras_audit_repository is None:
            raise ValueError("RAS audit repository is unavailable")
        source_sha256 = _file_sha256(file_path)
        versions = _assessment_reference_versions(self, report)
        detail = (
            RasAuditReportGenerator()
            .generate(
                source_sha256=source_sha256,
                cases=(
                    RasAuditReportCase(
                        candidate_id=report.assessment.candidate_entry_id,
                        assessment=report.assessment,
                        resolution=report.resolution,
                        calculation=report.calculation,
                    ),
                ),
                reference_versions=versions,
            )
            .details[0]
        )
        case = RasAuditCaseSnapshot(
            candidate_id=detail.candidate_id,
            status=detail.status,
            certainty=detail.certainty.value,
            payload=_ras_report_detail_payload(detail),
        )
        fact_context_payload: dict[str, object] = {
            "message_sha256": fact_context.message_sha256,
            "issued_at": fact_context.issued_at.isoformat(),
            "pattern_versions": list(fact_context.pattern_versions),
            "fact_names": sorted(fact.name for fact in fact_context.facts),
            "evidence_references": sorted(
                fact.evidence_reference for fact in fact_context.facts
            ),
            "conflicting_fact_names": list(
                fact_context.conflicting_fact_names
            ),
        }
        if base_audit_id is not None:
            return RasAuditDerivationService(self._ras_audit_repository).replace_case(
                base_audit_id=base_audit_id,
                source_sha256=source_sha256,
                replacement=case,
                added_reference_versions=versions,
                fact_context=fact_context_payload,
                created_at=fact_context.issued_at,
            )
        audit_id = uuid4().hex
        self._ras_audit_repository.save(
            RasAuditSnapshot(
                audit_id=audit_id,
                session_id=fact_context.session_id,
                file_id=fact_context.file_id,
                source_sha256=source_sha256,
                status="completed_provisional",
                reference_versions=versions,
                fact_context=fact_context_payload,
                cases=(case,),
                created_at=fact_context.issued_at,
            )
        )
        return audit_id

    def _validate_persisted_candidate(
        self,
        *,
        candidate_id: str,
        base_audit_id: str | None,
        source_sha256: str,
        fact_context: RasVerifiedFactContext | None,
    ) -> tuple[str, str] | None:
        if self._ras_audit_repository is None or base_audit_id is None:
            return (
                "base_audit_required",
                "a persisted base audit is required for candidate selection",
            )
        if fact_context is None:
            return (
                "ras_fact_context_required",
                "a valid server-attested RAS context is required",
            )
        snapshot = self._ras_audit_repository.get(base_audit_id)
        if snapshot is None:
            return ("ras_audit_not_found", "base RAS audit was not found")
        if snapshot.source_sha256 != source_sha256:
            return (
                "ras_audit_source_mismatch",
                "base RAS audit belongs to a different source file",
            )
        if (
            snapshot.session_id != fact_context.session_id
            or snapshot.file_id != fact_context.file_id
        ):
            return (
                "ras_audit_access_denied",
                "base RAS audit does not belong to the active session and file",
            )
        if not any(case.candidate_id == candidate_id for case in snapshot.cases):
            return (
                "ras_candidate_not_found",
                "candidate does not belong to the base RAS audit",
            )
        return None

    def _validate_audit_access(
        self,
        *,
        audit_id: str,
        fact_context: RasVerifiedFactContext,
    ) -> tuple[str, str] | None:
        assert self._ras_audit_repository is not None
        snapshot = self._ras_audit_repository.get(audit_id)
        if snapshot is None:
            return ("ras_audit_not_found", "RAS audit was not found")
        if (
            snapshot.session_id != fact_context.session_id
            or snapshot.file_id != fact_context.file_id
        ):
            return (
                "ras_audit_access_denied",
                "RAS audit does not belong to the active session and file",
            )
        return None


def _fact_attestation_payload(
    context: RasVerifiedFactContext,
) -> dict[str, object]:
    return {
        "message_sha256": context.message_sha256,
        "issued_at": context.issued_at.isoformat(),
        "pattern_versions": list(context.pattern_versions),
        "fact_names": sorted(fact.name for fact in context.facts),
        "evidence_references": sorted(
            fact.evidence_reference for fact in context.facts
        ),
        "conflicting_fact_names": list(context.conflicting_fact_names),
    }


def _serialize_result(
    result: ToolResult,
    tool_name: str,
) -> dict[str, object]:
    if isinstance(result, RasAuditReport):
        return _serialize_ras_audit_report(result)
    if isinstance(result, TaxRagQueryResult):
        return {
            "query": result.query,
            "as_of_date": result.as_of_date,
            "citations": [
                {
                    "article_or_section": citation.article_or_section,
                    "passage": citation.passage,
                    "title": citation.title,
                    "version": citation.version,
                    "source_url": citation.source_url,
                    "source_sha256": citation.source_sha256,
                    "score": citation.score,
                    "applicability_status": citation.applicability_status,
                    "applicable_from": citation.applicable_from,
                    "applicable_to": citation.applicable_to,
                }
                for citation in result.citations
            ],
            "indexed_source_count": result.indexed_source_count,
            "retrieval_mode": result.retrieval_mode,
            "retrieval_policy_version": result.retrieval_policy_version,
            "decision_status": result.decision_status,
        }
    if isinstance(result, RasBatchAuditResult):
        return {
            "audit_id": result.audit_id,
            "candidate_count": result.candidate_count,
            "potential_count": result.potential_count,
            "indeterminate_count": result.indeterminate_count,
            "status_counts": dict(result.status_counts),
            "review_candidate_ids": list(result.review_candidate_ids),
            "remaining_candidate_count": result.remaining_candidate_count,
            "source_scope_complete": result.source_scope_complete,
            "source_scope_blockers": list(result.source_scope_blockers),
            "decision_status": "candidate_inventory_pending_legal_facts",
        }
    if isinstance(result, ExcelSheetList):
        return {
            "sheet_names": list(result.sheet_names),
            "sheets": [
                {"name": sheet.name, "visibility": sheet.visibility}
                for sheet in result.sheets
            ],
        }
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
    if isinstance(result, RasRuleResolution):
        return {
            "status": result.status.value,
            "rule_id": result.rule_id,
            "rule_version": result.rule_version,
            "calculation_method": result.calculation_method,
            "rate_percent": (
                str(result.rate_percent) if result.rate_percent is not None else None
            ),
            "missing_facts": list(result.missing_facts),
            "alternative_rule_ids": list(result.alternative_rule_ids),
            "sources": [
                {
                    "source_kind": evidence.source_kind,
                    "source_url": evidence.source_url,
                    "source_locator": evidence.source_locator,
                    "source_sha256": evidence.source_sha256,
                }
                for evidence in result.evidence
            ],
            "source_assurance": result.source_assurance,
            "fact_sources": [
                {"fact_name": name, "source": source}
                for name, source in result.fact_sources
            ],
            "decision_status": "provisional_no_firm_audit_finding",
        }
    if isinstance(result, RasTheoreticalCalculationToolReport):
        calculation = result.calculation
        return {
            "legal_resolution_status": result.resolution.status.value,
            "calculation_status": calculation.status.value,
            "rule_id": calculation.rule_id,
            "rule_version": calculation.rule_version,
            "base_fact_name": calculation.base_fact_name,
            "base_amount": (
                str(calculation.base_amount)
                if calculation.base_amount is not None
                else None
            ),
            "expected_amount": (
                str(calculation.expected_amount)
                if calculation.expected_amount is not None
                else None
            ),
            "currency": calculation.currency,
            "calculation_method": calculation.calculation_method,
            "rate_percent": (
                str(calculation.rate_percent)
                if calculation.rate_percent is not None
                else None
            ),
            "steps": [
                {
                    "step": step.step,
                    "expression": step.expression,
                    "result": str(step.result),
                }
                for step in calculation.steps
            ],
            "parameter_versions": list(calculation.parameter_versions),
            "source_locators": list(calculation.source_locators),
            "legal_sources": [
                {
                    "source_kind": evidence.source_kind,
                    "source_url": evidence.source_url,
                    "source_locator": evidence.source_locator,
                    "source_sha256": evidence.source_sha256,
                }
                for evidence in result.resolution.evidence
            ],
            "missing_facts": list(result.resolution.missing_facts),
            "rounding_policy": calculation.rounding_policy,
            "reason": calculation.reason,
            "decision_status": "provisional_deterministic_calculation",
        }
    if isinstance(result, RasAccountingAssessmentToolReport):
        accounting_assessment = result.assessment
        return {
            "sheet_name": result.sheet_name,
            "row_count": result.source_row_count,
            "status": accounting_assessment.status.value,
            "legal_resolution_status": result.resolution.status.value,
            "calculation_status": result.calculation.status.value,
            "rule_id": result.calculation.rule_id,
            "rule_version": result.calculation.rule_version,
            "expected_amount": (
                str(accounting_assessment.expected_amount)
                if accounting_assessment.expected_amount is not None
                else None
            ),
            "recorded_amount": (
                str(accounting_assessment.recorded_amount)
                if accounting_assessment.recorded_amount is not None
                else None
            ),
            "difference": (
                str(accounting_assessment.difference)
                if accounting_assessment.difference is not None
                else None
            ),
            "currency": accounting_assessment.currency,
            "tolerance": (
                str(accounting_assessment.tolerance)
                if accounting_assessment.tolerance is not None
                else None
            ),
            "policy_version": accounting_assessment.policy_version,
            "missing_facts": list(accounting_assessment.missing_facts),
            "issues": list(accounting_assessment.issues),
            "potential_adjustments_present": (
                accounting_assessment.potential_adjustments_present
            ),
            "basis_is_complete": accounting_assessment.basis_is_complete,
            "source_scope_complete": result.source_scope_complete,
            "rejected_row_count": result.rejected_row_count,
            "legal_sources": [
                {
                    "source_kind": evidence.source_kind,
                    "source_url": evidence.source_url,
                    "source_locator": evidence.source_locator,
                    "source_sha256": evidence.source_sha256,
                }
                for evidence in result.resolution.evidence
            ],
            "decision_status": "provisional_accounting_assessment",
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
            "filter_warnings": list(result.filter_warnings),
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
            "filter_warnings": list(result.filter_warnings),
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
    if isinstance(result, LedgerNormalizationReport):
        issue_counts: dict[str, int] = {}
        for issue in result.issues:
            issue_counts[issue.code] = issue_counts.get(issue.code, 0) + 1
        output: dict[str, object] = {
            "sheet_name": result.sheet_name,
            "content_sha256": result.content_sha256,
            "row_count": len(result.entries) + len(result.rejected_rows),
            "normalized_count": len(result.entries),
            "rejected_count": len(result.rejected_rows),
            "issue_counts": issue_counts,
            "mapped_fields": {
                binding.field.value: binding.source_column
                for binding in result.bindings
            },
            "readiness": [
                {
                    "capability": readiness.capability.value,
                    "status": readiness.status.value,
                    "blockers": list(readiness.blockers),
                    "warnings": list(readiness.warnings),
                }
                for readiness in result.readiness.capabilities
            ],
        }
        if tool_name == "assess_gl_readiness":
            return {
                key: value
                for key, value in output.items()
                if key
                in {
                    "sheet_name",
                    "row_count",
                    "issue_counts",
                    "mapped_fields",
                    "readiness",
                }
            }
        return output
    if isinstance(result, AccountingEntryReconstructionToolReport):
        reconstruction = result.reconstruction
        all_issues = [
            issue for entry in reconstruction.entries for issue in entry.issues
        ] + list(reconstruction.issues)
        normalization_issue_counts: dict[str, int] = {}
        for issue_code in result.normalized_issue_codes:
            normalization_issue_counts[issue_code] = (
                normalization_issue_counts.get(issue_code, 0) + 1
            )
        entry_issue_counts: dict[str, int] = {}
        for reconstruction_issue in all_issues:
            entry_issue_counts[reconstruction_issue.code] = (
                entry_issue_counts.get(reconstruction_issue.code, 0) + 1
            )
        reconstruction_issue_counts = {
            issue_code: max(
                normalization_issue_counts.get(issue_code, 0),
                entry_issue_counts.get(issue_code, 0),
            )
            for issue_code in normalization_issue_counts.keys()
            | entry_issue_counts.keys()
        }
        currencies = sorted(
            {
                balance.currency
                for entry in reconstruction.entries
                for balance in entry.balances
            }
        )
        balanced_count = sum(entry.is_balanced for entry in reconstruction.entries)
        output = {
            "sheet_name": result.sheet_name,
            "row_count": result.source_row_count,
            "entry_count": len(reconstruction.entries),
            "grouped_line_count": sum(
                len(entry.line_ids) for entry in reconstruction.entries
            ),
            "balanced_count": balanced_count,
            "unbalanced_count": len(reconstruction.entries) - balanced_count,
            "ungrouped_line_count": len(reconstruction.ungrouped_line_ids),
            "rejected_row_count": result.rejected_row_count,
            "issue_counts": reconstruction_issue_counts,
            "currencies": currencies,
        }
        if result.selector is not None:
            output["selector"] = result.selector
            output["selected_entry_found"] = result.selected_entry is not None
        if result.selected_entry is not None:
            selected_entry = result.selected_entry
            output["selected_entry"] = {
                "entry_id": selected_entry.entry_id,
                "key": {
                    "company_code": selected_entry.key.company_code,
                    "fiscal_year": selected_entry.key.fiscal_year,
                    "journal": selected_entry.key.journal,
                    "document_number": selected_entry.key.document_number,
                },
                "line_count": len(selected_entry.line_ids),
                "is_balanced": selected_entry.is_balanced,
                "balances": [
                    {
                        "currency": balance.currency,
                        "debit_total": str(balance.debit_total),
                        "credit_total": str(balance.credit_total),
                        "difference": str(balance.difference),
                        "used_line_count": balance.used_line_count,
                        "excluded_line_count": balance.excluded_line_count,
                    }
                    for balance in selected_entry.balances
                ],
                "issues": [
                    {
                        "code": issue.code,
                        "severity": issue.severity.value,
                    }
                    for issue in selected_entry.issues
                ],
                "lines": [
                    {
                        "account": line.account_number,
                        "posting_key": line.posting_key,
                        "amount": str(line.amount) if line.amount is not None else None,
                        "currency": line.currency,
                        "period": line.period,
                        "fiscal_year": line.fiscal_year,
                    }
                    for line in result.selected_lines
                ],
            }
        return output
    if isinstance(result, RasCounterpartToolReport):
        assessments = result.report.assessments
        status_counts = {
            status.value: sum(item.status is status for item in assessments)
            for status in RasCounterpartStatus
        }
        confirmed_amounts = _counterpart_amount_totals(
            tuple(
                amount
                for item in assessments
                if item.status is RasCounterpartStatus.FOUND_IN_SAME_ENTRY
                for amount in item.recorded_amounts
            ),
        )
        potential_related_amounts = _counterpart_amount_totals(
            tuple(
                amount
                for item in assessments
                if item.status is RasCounterpartStatus.POTENTIAL_RELATED_ENTRY
                for amount in item.recorded_amounts
            ),
        )
        potential_adjustments = _counterpart_amount_totals(
            tuple(
                amount
                for item in assessments
                for amount in item.potential_adjustment_amounts
            ),
        )
        missing_fact_counts: dict[str, int] = {}
        counterpart_issue_counts: dict[str, int] = {}
        for issue_code in result.normalization_issue_codes:
            counterpart_issue_counts[issue_code] = (
                counterpart_issue_counts.get(issue_code, 0) + 1
            )
        for assessment in assessments:
            for missing_fact in assessment.missing_facts:
                missing_fact_counts[missing_fact] = (
                    missing_fact_counts.get(missing_fact, 0) + 1
                )
            for issue_code in assessment.issues:
                counterpart_issue_counts[issue_code] = (
                    counterpart_issue_counts.get(issue_code, 0) + 1
                )
        return {
            "sheet_name": result.sheet_name,
            "row_count": result.source_row_count,
            "detected_candidate_piece_count": (
                result.detected_candidate_piece_count
            ),
            "candidate_piece_count": len(assessments),
            "counterpart_scope_exclusion_count": (
                (
                    result.detected_candidate_piece_count
                    - len(assessments)
                )
                if result.detected_candidate_piece_count is not None
                else None
            ),
            "counterpart_scope_basis": (
                "Pieces avec au moins une ligne de charge candidate mappee; "
                "les candidats purement textuels ou hors mapping comptable "
                "ne sont pas rapproches ici."
            ),
            "status_counts": status_counts,
            "confirmed_amounts_by_currency": confirmed_amounts,
            "potential_related_amounts_by_currency": potential_related_amounts,
            "potential_adjustments_by_currency": potential_adjustments,
            "missing_fact_counts": missing_fact_counts,
            "issue_counts": counterpart_issue_counts,
            "rejected_row_count": result.rejected_row_count,
            "source_scope_complete": result.source_scope_complete,
            "source_scope_blockers": list(result.source_scope_blockers),
            "source_scope_policy_version": result.source_scope_policy_version,
        }
    if isinstance(result, RasCandidateDetectionToolReport):
        candidates = result.report.candidates
        candidate_status_counts: dict[str, int] = {}
        signal_counts: dict[str, int] = {}
        operation_hint_counts: dict[str, int] = {}
        candidate_missing_fact_counts: dict[str, int] = {}
        amount_totals: dict[str, Decimal] = {}
        semantic_scores: list[float] = []
        for candidate in candidates:
            candidate_status_counts[candidate.status.value] = (
                candidate_status_counts.get(candidate.status.value, 0) + 1
            )
            for signal_id in candidate.signal_ids:
                signal_counts[signal_id] = signal_counts.get(signal_id, 0) + 1
            for hint in candidate.operation_hints:
                operation_hint_counts[hint] = operation_hint_counts.get(hint, 0) + 1
            for fact in candidate.missing_facts:
                candidate_missing_fact_counts[fact] = (
                    candidate_missing_fact_counts.get(fact, 0) + 1
                )
            for amount in candidate.amounts:
                amount_totals[amount.currency] = (
                    amount_totals.get(amount.currency, Decimal("0")) + amount.amount
                )
            if candidate.semantic_similarity is not None:
                semantic_scores.append(candidate.semantic_similarity)
        candidate_issue_counts: dict[str, int] = {}
        for code in result.normalization_issue_codes:
            candidate_issue_counts[code] = candidate_issue_counts.get(code, 0) + 1
        return {
            "sheet_name": result.sheet_name,
            "row_count": result.filtered_row_count,
            "source_row_count": result.source_row_count,
            "filters": result.filters,
            "evaluated_piece_count": result.report.evaluated_piece_count,
            "candidate_piece_count": len(candidates),
            "excluded_piece_count": result.report.excluded_piece_count,
            "status_counts": candidate_status_counts,
            "signal_counts": signal_counts,
            "operation_hint_counts": operation_hint_counts,
            "candidate_amounts_by_currency": {
                currency: str(amount)
                for currency, amount in sorted(amount_totals.items())
            },
            "ras_review": _ras_review_summary(result),
            "missing_fact_counts": candidate_missing_fact_counts,
            "issue_counts": candidate_issue_counts,
            "rejected_row_count": result.rejected_row_count,
            "decision_status": "review_only_no_tax_conclusion",
            "semantic_model": (
                {
                    "provider_name": result.report.semantic_provider_name,
                    "model_name": result.report.semantic_model_name,
                    "policy_version": result.report.semantic_policy_version,
                    "calibration_status": (result.report.semantic_calibration_status),
                    "score_count": len(semantic_scores),
                }
                if result.report.semantic_model_name is not None
                else None
            ),
        }
    if isinstance(result, RasSemanticClassificationToolReport):
        semantic_results = result.report.results
        semantic_status_counts = {
            status.value: sum(item.status is status for item in semantic_results)
            for status in SemanticClassificationStatus
        }
        semantic_signal_counts: dict[str, int] = {}
        semantic_missing_fact_counts: dict[str, int] = {}
        scores: list[float] = []
        for item in semantic_results:
            if item.signal_id is not None:
                semantic_signal_counts[item.signal_id] = (
                    semantic_signal_counts.get(item.signal_id, 0) + 1
                )
            if item.similarity is not None:
                scores.append(item.similarity)
            for fact in item.missing_facts:
                semantic_missing_fact_counts[fact] = (
                    semantic_missing_fact_counts.get(fact, 0) + 1
                )
        return {
            "sheet_name": result.sheet_name,
            "row_count": result.source_row_count,
            "classified_piece_count": len(semantic_results),
            "status_counts": semantic_status_counts,
            "signal_counts": semantic_signal_counts,
            "missing_fact_counts": semantic_missing_fact_counts,
            "score_summary": (
                {
                    "count": len(scores),
                    "minimum": min(scores),
                    "maximum": max(scores),
                    "average": sum(scores) / len(scores),
                }
                if scores
                else {"count": 0}
            ),
            "provider_name": result.report.provider_name,
            "model_name": result.report.model_name,
            "policy_version": result.report.policy_version,
            "calibration_status": result.report.calibration_status,
            "rejected_row_count": result.rejected_row_count,
            "decision_status": "semantic_suggestion_for_review_only",
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


def _serialize_ras_audit_report(report: RasAuditReport) -> dict[str, object]:
    return {
        "report_id": report.report_id,
        "source_sha256": report.source_sha256,
        "generated_at": report.generated_at.isoformat(),
        "case_count": report.case_count,
        "status_counts": dict(report.status_counts),
        "certainty_counts": dict(report.certainty_counts),
        "amount_summaries": [
            {
                "certainty": summary.certainty.value,
                "currency": summary.currency,
                "case_count": summary.case_count,
                "expected_amount": str(summary.expected_amount),
                "recorded_amount": str(summary.recorded_amount),
                "difference": str(summary.difference),
            }
            for summary in report.amount_summaries
        ],
        "recorded_amount_summaries": [
            {
                "certainty": summary.certainty.value,
                "currency": summary.currency,
                "case_count": summary.case_count,
                "recorded_amount": str(summary.recorded_amount),
            }
            for summary in report.recorded_amount_summaries
        ],
        "details": [
            {
                "candidate_id": detail.candidate_id,
                "status": detail.status,
                "certainty": detail.certainty.value,
                "rule_id": detail.rule_id,
                "rule_version": detail.rule_version,
                "expected_amount": (
                    str(detail.expected_amount)
                    if detail.expected_amount is not None
                    else None
                ),
                "recorded_amount": (
                    str(detail.recorded_amount)
                    if detail.recorded_amount is not None
                    else None
                ),
                "difference": (
                    str(detail.difference) if detail.difference is not None else None
                ),
                "currency": detail.currency,
                "missing_facts": list(detail.missing_facts),
                "issues": list(detail.issues),
                "legal_source_locators": list(detail.legal_source_locators),
                "basis_is_complete": detail.basis_is_complete,
            }
            for detail in report.details
        ],
        "reference_versions": list(report.reference_versions),
        "decision_status": "deterministic_persisted_audit_report",
    }


def _ras_report_detail_payload(
    detail: RasAuditReportDetail,
) -> dict[str, object]:
    return {
        "candidate_id": detail.candidate_id,
        "status": detail.status,
        "certainty": detail.certainty.value,
        "rule_id": detail.rule_id,
        "rule_version": detail.rule_version,
        "expected_amount": (
            str(detail.expected_amount) if detail.expected_amount is not None else None
        ),
        "recorded_amount": (
            str(detail.recorded_amount) if detail.recorded_amount is not None else None
        ),
        "difference": (
            str(detail.difference) if detail.difference is not None else None
        ),
        "currency": detail.currency,
        "missing_facts": list(detail.missing_facts),
        "issues": list(detail.issues),
        "legal_source_locators": list(detail.legal_source_locators),
        "basis_is_complete": detail.basis_is_complete,
    }


def _assessment_reference_versions(
    executor: ExcelToolExecutor,
    report: RasAccountingAssessmentToolReport,
) -> tuple[str, ...]:
    versions = {
        *(
            f"account-mapping:{item.version}"
            for item in executor._ras_ledger_account_mappings
        ),
        *(
            f"calculation:{version}"
            for version in report.calculation.parameter_versions
        ),
        *(
            f"tax-event:{item.version}"
            for item in executor._ras_tax_event_rules
        ),
    }
    if report.resolution.rule_version is not None:
        versions.add(f"legal:{report.resolution.rule_version}")
    if report.assessment.policy_version is not None:
        versions.add(f"assessment:{report.assessment.policy_version}")
    return tuple(sorted(versions))


def _batch_reference_versions(
    executor: ExcelToolExecutor,
    detection: RasCandidateDetectionReport,
) -> tuple[str, ...]:
    versions = {
        *(
            f"account-mapping:{item.version}"
            for item in executor._ras_ledger_account_mappings
        ),
        *(
            f"candidate-signals:{item.version}"
            for item in executor._ras_candidate_signals
        ),
    }
    semantic_version = detection.semantic_policy_version
    if semantic_version:
        versions.add(f"semantic-policy:{semantic_version}")
    return tuple(sorted(versions))


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def _safe_excel_error_message(error_code: str) -> str:
    return {
        "unsafe_excel_path": "Excel file path is not allowed",
        "unsupported_excel_file": "Excel file type is not supported",
        "excel_sheet_not_found": "Requested Excel sheet is unavailable",
        "excel_file_read": "Excel file cannot be read",
    }.get(error_code, "Excel operation failed")


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
    raw_filters = _optional_dict(raw_value)
    filters: dict[str, object] = {}
    for raw_filter_name, filter_value in raw_filters.items():
        if not isinstance(raw_filter_name, str):
            return None
        filter_name = _canonical_query_filter_name(raw_filter_name)
        if filter_name not in QUERY_FILTER_NAMES:
            return None
        normalized_value = _query_filter_value(filter_name, filter_value)
        if normalized_value is None:
            return None
        existing_value = filters.get(filter_name)
        if existing_value is not None and existing_value != normalized_value:
            return None
        filters[filter_name] = normalized_value
    return filters


def _ras_detection_filters(raw_value: object) -> dict[str, object] | None:
    raw_filters = _optional_dict(raw_value)
    filters: dict[str, object] = {}
    for raw_filter_name, filter_value in raw_filters.items():
        if not isinstance(raw_filter_name, str):
            return None
        filter_name = _canonical_query_filter_name(raw_filter_name)
        if filter_name not in RAS_DETECTION_FILTER_NAMES:
            return None
        normalized_value = _query_filter_value(filter_name, filter_value)
        if normalized_value is None:
            return None
        if filter_name == "currency":
            normalized_value = str(normalized_value).upper()
        existing_value = filters.get(filter_name)
        if existing_value is not None and existing_value != normalized_value:
            return None
        filters[filter_name] = normalized_value
    return filters


def _filter_ras_detection_entries(
    entries: tuple[CanonicalLedgerEntry, ...],
    filters: dict[str, object],
) -> tuple[CanonicalLedgerEntry, ...]:
    if not filters:
        return entries
    return tuple(entry for entry in entries if _ras_entry_matches(entry, filters))


def _ras_entry_matches(
    entry: CanonicalLedgerEntry,
    filters: dict[str, object],
) -> bool:
    for filter_name, filter_value in filters.items():
        expected = str(filter_value)
        if filter_name == "account" and entry.account_number != expected:
            return False
        if filter_name == "period" and str(entry.period or "") != expected:
            return False
        if filter_name == "fiscal_year" and str(entry.fiscal_year or "") != expected:
            return False
        if filter_name == "currency" and (entry.currency or "") != expected:
            return False
    return True


def _reconstruction_entry_selector(
    raw_value: object,
) -> dict[str, str | int | None] | None:
    if raw_value is None:
        return None
    if not isinstance(raw_value, dict):
        return None
    selector: dict[str, str | int | None] = {}
    for raw_key, raw_selector_value in raw_value.items():
        if not isinstance(raw_key, str):
            return None
        key = _canonical_entry_selector_name(raw_key)
        if key not in {
            "company_code",
            "fiscal_year",
            "journal",
            "document_number",
        }:
            return None
        value = _entry_selector_value(key, raw_selector_value)
        if value is None and key != "company_code":
            return None
        existing_value = selector.get(key)
        if existing_value is not None and existing_value != value:
            return None
        selector[key] = value
    if "document_number" not in selector:
        return None
    return selector


def _canonical_entry_selector_name(raw_key: str) -> str:
    normalized = _canonical_query_filter_name(raw_key)
    aliases = {
        "piece": "document_number",
        "numero_piece": "document_number",
        "numero_de_piece": "document_number",
        "document": "document_number",
        "document_no": "document_number",
        "document_id": "document_number",
        "type_piece": "journal",
        "type_de_piece": "journal",
        "journal_code": "journal",
        "societe": "company_code",
        "company": "company_code",
    }
    return aliases.get(normalized, normalized)


def _entry_selector_value(
    key: str,
    raw_value: object,
) -> str | int | None:
    if raw_value is None and key == "company_code":
        return None
    if isinstance(raw_value, bool):
        return None
    if key == "fiscal_year":
        if isinstance(raw_value, int):
            return raw_value if raw_value > 0 else None
        if isinstance(raw_value, float) and raw_value.is_integer():
            return int(raw_value) if raw_value > 0 else None
        if isinstance(raw_value, str) and raw_value.strip().isdigit():
            year = int(raw_value.strip())
            return year if year > 0 else None
        return None
    if isinstance(raw_value, int):
        return str(raw_value)
    if isinstance(raw_value, float):
        return str(int(raw_value)) if raw_value.is_integer() else str(raw_value)
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        return stripped or None
    return None


def _select_reconstructed_entry(
    entries: tuple[ReconstructedAccountingEntry, ...],
    selector: dict[str, str | int | None] | None,
) -> ReconstructedAccountingEntry | None:
    if selector is None:
        return None
    matches = tuple(
        entry for entry in entries if _reconstructed_entry_matches(entry, selector)
    )
    if len(matches) != 1:
        return None
    return matches[0]


def _reconstructed_entry_matches(
    entry: ReconstructedAccountingEntry,
    selector: dict[str, str | int | None],
) -> bool:
    if entry.key.document_number != selector["document_number"]:
        return False
    fiscal_year = selector.get("fiscal_year")
    if fiscal_year is not None and entry.key.fiscal_year != fiscal_year:
        return False
    journal = selector.get("journal")
    if journal is not None and entry.key.journal != journal:
        return False
    company_code = selector.get("company_code")
    return not (
        company_code is not None and entry.key.company_code != company_code
    )


def _canonical_query_filter_name(raw_filter_name: str) -> str:
    normalized = normalize("NFKD", raw_filter_name.strip().lower())
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    stable_name = "_".join(ascii_name.replace("-", "_").split())
    return QUERY_FILTER_ALIASES.get(stable_name, stable_name)


def _query_filter_value(filter_name: str, raw_value: object) -> object | None:
    if filter_name in {"amount_min", "amount_max"}:
        if isinstance(raw_value, bool):
            return None
        if isinstance(raw_value, int | float):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return float(raw_value.replace(" ", "").replace(",", "."))
            except ValueError:
                return None
        return None
    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, int):
        return str(raw_value)
    if isinstance(raw_value, float):
        return str(int(raw_value)) if raw_value.is_integer() else str(raw_value)
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        return stripped or None
    return None


def _optional_string(raw_value: object) -> str | None:
    return raw_value if isinstance(raw_value, str) else None


def _optional_non_empty_string(raw_value: object) -> str | None:
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    return normalized or None


def _normalization_bindings(
    raw_value: object,
) -> tuple[LedgerColumnBinding, ...] | None:
    if not isinstance(raw_value, dict) or not raw_value:
        return None
    bindings: list[LedgerColumnBinding] = []
    seen_columns: set[str] = set()
    try:
        for raw_field, raw_column in raw_value.items():
            if not isinstance(raw_field, str) or not isinstance(raw_column, str):
                return None
            field = LedgerField(raw_field)
            source_column = raw_column.strip()
            if not source_column or source_column in seen_columns:
                return None
            seen_columns.add(source_column)
            bindings.append(LedgerColumnBinding(field, source_column))
    except ValueError:
        return None
    return tuple(bindings)


def _optional_boolean(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_boolean_is_valid(
    arguments: MappingProxyType[str, object],
    argument_name: str,
) -> bool:
    return argument_name not in arguments or isinstance(
        arguments[argument_name],
        bool,
    )


def _ras_rule_resolution_request(
    arguments: MappingProxyType[str, object],
    facts: tuple[RasLegalFact, ...],
) -> RasRuleResolutionRequest | None:
    raw_date = arguments.get("transaction_date")
    raw_jurisdiction = arguments.get("jurisdiction", "BF")
    if not isinstance(raw_date, str) or not isinstance(raw_jurisdiction, str):
        return None
    try:
        transaction_date = date.fromisoformat(raw_date)
        return RasRuleResolutionRequest(
            transaction_date=transaction_date,
            facts=facts,
            jurisdiction=raw_jurisdiction,
        )
    except ValueError:
        return None


def _select_accounting_entry(
    entries: tuple[ReconstructedAccountingEntry, ...],
    *,
    candidate_id: str | None,
    selector: dict[str, str | int] | None,
) -> ReconstructedAccountingEntry | None:
    if candidate_id is not None:
        return next(
            (entry for entry in entries if entry.entry_id == candidate_id),
            None,
        )
    if selector is None:
        return None
    return next(
        (
            entry
            for entry in entries
            if entry.key.company_code == selector["company_code"]
            and entry.key.fiscal_year == selector["fiscal_year"]
            and entry.key.journal == selector["journal"]
            and entry.key.document_number == selector["document_number"]
        ),
        None,
    )


def _attested_tax_event_dates(
    facts: tuple[RasLegalFact, ...],
    rules: tuple[RasTaxEventRule, ...],
) -> tuple[date, ...]:
    date_fact_names = {rule.event_date_fact for rule in rules}
    return tuple(
        sorted(
            {
                date.fromisoformat(fact.value)
                for fact in facts
                if fact.name in date_fact_names
            }
        )
    )


def _accounting_entry_selector(raw_value: object) -> dict[str, str | int] | None:
    if not isinstance(raw_value, dict) or set(raw_value) != {
        "company_code",
        "fiscal_year",
        "journal",
        "document_number",
    }:
        return None
    company_code = raw_value.get("company_code")
    fiscal_year = raw_value.get("fiscal_year")
    journal = raw_value.get("journal")
    document_number = raw_value.get("document_number")
    if (
        not isinstance(company_code, str)
        or not company_code.strip()
        or not isinstance(fiscal_year, int)
        or isinstance(fiscal_year, bool)
        or fiscal_year < 1
        or not isinstance(journal, str)
        or not journal.strip()
        or not isinstance(document_number, str)
        or not document_number.strip()
    ):
        return None
    return {
        "company_code": company_code.strip(),
        "fiscal_year": fiscal_year,
        "journal": journal.strip(),
        "document_number": document_number.strip(),
    }


def _ras_review_summary(result: RasCandidateDetectionToolReport) -> dict[str, object]:
    line_by_id = {entry.line_id: entry for entry in result.ledger_entries}
    evaluated_counts: dict[str, int] = {}
    for entry in result.reconstruction.entries:
        period = _ledger_entry_period(entry.line_ids, line_by_id)
        evaluated_counts[period] = evaluated_counts.get(period, 0) + 1

    candidate_counts: dict[str, int] = {}
    amounts_by_period_currency: dict[tuple[str, str | None], Decimal] = {}
    for candidate in result.report.candidates:
        period = _ledger_entry_period(candidate.line_ids, line_by_id)
        candidate_counts[period] = candidate_counts.get(period, 0) + 1
        if not candidate.amounts:
            amounts_by_period_currency.setdefault((period, None), Decimal("0"))
        for amount in candidate.amounts:
            key = (period, amount.currency)
            amounts_by_period_currency[key] = (
                amounts_by_period_currency.get(key, Decimal("0")) + amount.amount
            )

    period_currency_keys = set(amounts_by_period_currency)
    periods_with_amount = {
        period for period, currency in period_currency_keys if currency
    }
    period_currency_keys.update(
        (period, None)
        for period in candidate_counts
        if period not in periods_with_amount
    )
    periods: list[dict[str, object]] = []
    for period, currency in sorted(period_currency_keys, key=_ras_period_sort_key):
        evaluated_count = evaluated_counts.get(period, 0)
        candidate_count = candidate_counts.get(period, 0)
        periods.append(
            {
                "period": period,
                "evaluated_entry_count": evaluated_count,
                "candidate_entry_count": candidate_count,
                "candidate_amount": str(
                    amounts_by_period_currency.get((period, currency), Decimal("0"))
                ),
                "currency": currency,
                "candidate_rate": (
                    round(candidate_count / evaluated_count, 6)
                    if evaluated_count > 0
                    else 0
                ),
            }
        )
    return {"periods": periods}


def _ledger_entry_period(
    line_ids: tuple[str, ...],
    line_by_id: dict[str, CanonicalLedgerEntry],
) -> str:
    period_values: set[int] = set()
    for line_id in line_ids:
        line = line_by_id.get(line_id)
        if line is not None and line.period is not None:
            period_values.add(line.period)
    periods = sorted(period_values)
    if len(periods) == 1:
        return str(periods[0])
    if len(periods) > 1:
        return "Multi-périodes"
    return "Sans période"


def _ras_period_sort_key(item: tuple[str, str | None]) -> tuple[int, int, str]:
    period, currency = item
    try:
        period_value = int(float(period))
    except ValueError:
        return (1, 99, f"{period}:{currency or ''}")
    return (0, period_value, currency or "")


def _counterpart_amount_totals(
    amounts: tuple[RasCounterpartAmount, ...],
) -> dict[str, str]:
    totals: dict[str, Decimal] = {}
    for amount in amounts:
        totals[amount.currency] = totals.get(amount.currency, Decimal("0")) + (
            amount.amount
        )
    return {currency: str(amount) for currency, amount in sorted(totals.items())}


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


def _load_default_ledger_column_aliases() -> tuple[LedgerColumnAlias, ...]:
    for aliases_path in (
        Path("../docs/reference/ras-gl-column-aliases.csv"),
        Path("docs/reference/ras-gl-column-aliases.csv"),
        Path("/workspace/docs/reference/ras-gl-column-aliases.csv"),
    ):
        if aliases_path.is_file():
            return load_ledger_column_aliases(aliases_path)
    return ()


def _load_default_ras_candidate_signals() -> tuple[RasCandidateSignal, ...]:
    for signals_path in (
        Path("../docs/reference/ras-candidate-signals.csv"),
        Path("docs/reference/ras-candidate-signals.csv"),
        Path("/workspace/docs/reference/ras-candidate-signals.csv"),
    ):
        if signals_path.is_file():
            return load_ras_candidate_signals(signals_path)
    return ()
