from dataclasses import dataclass
from pathlib import Path
from unicodedata import normalize

import pandas as pd

from app.account_mapping.classifier import ClassificationRule
from app.account_mapping.domain import RasCategory
from app.excel_agent.domain import ExcelColumnProfile, ExcelSheetProfile
from app.excel_agent.excel_tools import ExcelAgentTools
from app.ledger_analysis.account_balance_rules import (
    AccountBalanceRule,
    find_account_balance_rule,
)
from app.ledger_analysis.constants import (
    LEDGER_AGGREGATION_FIELDS,
    LEDGER_COUNTERPARTY_FIELDS,
    LEDGER_QUALITY_CRITICAL_FIELDS,
    LEDGER_QUERY_OUTPUT_FIELDS,
    LEDGER_TAX_CANDIDATE_LIMIT,
)
from app.ledger_analysis.posting_key_rules import PostingKeyRule
from app.ledger_analysis.schema_classifier import (
    LedgerSchemaClassification,
    LedgerSchemaClassifier,
)
from app.ledger_analysis.schema_validator import (
    LedgerSchemaReport,
    LedgerSchemaValidationError,
    LedgerSchemaValidator,
)

SIGNED_AMOUNT_COLUMN = "__signed_amount"


@dataclass(frozen=True)
class LedgerAnalysisReport:
    sheet_name: str
    row_count: int
    column_count: int
    schema_report: LedgerSchemaReport
    canonical_schema: LedgerSchemaClassification
    columns: tuple[ExcelColumnProfile, ...]


@dataclass(frozen=True)
class LedgerSchemaClassificationReport:
    sheet_name: str
    row_count: int
    column_count: int
    classification: LedgerSchemaClassification
    columns: tuple[ExcelColumnProfile, ...]


@dataclass(frozen=True)
class LedgerAggregationGroup:
    key: str
    entry_count: int
    amount_sum: float
    currency: str | None = None
    used_entry_count: int = 0
    excluded_entry_count: int = 0
    raw_amount_sum: float = 0.0
    debit_total: float = 0.0
    credit_total: float = 0.0
    balance: float = 0.0


@dataclass(frozen=True)
class LedgerFieldAggregation:
    canonical_field: str
    source_column: str
    total_groups: int
    groups: tuple[LedgerAggregationGroup, ...]


@dataclass(frozen=True)
class LedgerAggregationReport:
    sheet_name: str
    row_count: int
    amount_field: str
    aggregations: tuple[LedgerFieldAggregation, ...]
    sign_convention: str | None = None
    filters: dict[str, object] | None = None


@dataclass(frozen=True)
class LedgerQueryReport:
    sheet_name: str
    total_matches: int
    page: int
    page_size: int
    filters: dict[str, object]
    returned_columns: tuple[str, ...]
    message: str
    entries: tuple[dict[str, object], ...]
    sign_convention: str | None = None


@dataclass(frozen=True)
class LedgerMetricsReport:
    sheet_name: str
    total_matches: int
    amount_field: str
    metrics: dict[str, float | int]
    top: LedgerFieldAggregation | None
    sign_convention: str | None = None
    balance_interpretation: dict[str, object] | None = None
    metrics_by_currency: dict[str, dict[str, float | int]] | None = None
    filters: dict[str, object] | None = None
    balance_reconciliation: dict[str, object] | None = None


@dataclass(frozen=True)
class LedgerDataQualityIssue:
    issue_type: str
    severity: str
    canonical_field: str | None
    source_column: str | None
    affected_count: int
    affected_ratio: float
    message: str
    affected_accounts: tuple["LedgerQualityAffectedAccount", ...] = ()


@dataclass(frozen=True)
class LedgerQualityAffectedAccount:
    account: str
    affected_count: int


@dataclass(frozen=True)
class LedgerDataQualityReport:
    sheet_name: str
    row_count: int
    issue_count: int
    severity_counts: dict[str, int]
    issues: tuple[LedgerDataQualityIssue, ...]


@dataclass(frozen=True)
class LedgerTaxCandidate:
    category: str
    confidence: str
    entry_count: int
    amount_sum: float
    matched_keywords: tuple[str, ...]
    top_accounts: tuple[LedgerAggregationGroup, ...]
    action_required: str
    amounts_by_currency: dict[str, float]


@dataclass(frozen=True)
class LedgerTaxCandidateReport:
    sheet_name: str
    row_count: int
    decision_status: str
    candidates: tuple[LedgerTaxCandidate, ...]
    sign_convention: str | None = None


class LedgerAnalysisService:
    def __init__(
        self,
        excel_tools: ExcelAgentTools,
        schema_validator: LedgerSchemaValidator | None = None,
        schema_classifier: LedgerSchemaClassifier | None = None,
        tax_candidate_rules: tuple[ClassificationRule, ...] = (),
        posting_key_rules: tuple[PostingKeyRule, ...] = (),
        account_balance_rules: tuple[AccountBalanceRule, ...] = (),
    ) -> None:
        self._excel_tools = excel_tools
        self._schema_validator = schema_validator or LedgerSchemaValidator()
        self._schema_classifier = schema_classifier or LedgerSchemaClassifier()
        self._tax_candidate_rules = tax_candidate_rules
        self._posting_key_rules = {
            rule.posting_key: rule for rule in posting_key_rules
        }
        self._account_balance_rules = account_balance_rules
        self._canonical_frame_cache: dict[
            tuple[str, str],
            _CanonicalLedgerFrame,
        ] = {}
        self._sheet_profile_cache: dict[tuple[str, str], ExcelSheetProfile] = {}

    def analyze(self, file_path: Path, sheet_name: str) -> LedgerAnalysisReport:
        sheet_profile = self._excel_tools.profile_sheet(file_path, sheet_name)
        self._sheet_profile_cache[
            (str(file_path.resolve()), sheet_name)
        ] = sheet_profile
        column_names = tuple(column.name for column in sheet_profile.columns)
        canonical_schema = self._schema_classifier.classify(sheet_profile.columns)
        schema_report = _canonical_schema_report(column_names, canonical_schema)
        return LedgerAnalysisReport(
            sheet_name=sheet_profile.sheet_name,
            row_count=sheet_profile.row_count,
            column_count=sheet_profile.column_count,
            schema_report=schema_report,
            canonical_schema=canonical_schema,
            columns=sheet_profile.columns,
        )

    def classify_schema(
        self,
        file_path: Path,
        sheet_name: str,
    ) -> LedgerSchemaClassificationReport:
        cache_key = (str(file_path.resolve()), sheet_name)
        sheet_profile = self._sheet_profile_cache.get(cache_key)
        if sheet_profile is None:
            sheet_profile = self._excel_tools.profile_sheet(file_path, sheet_name)
            self._sheet_profile_cache[cache_key] = sheet_profile
        return LedgerSchemaClassificationReport(
            sheet_name=sheet_profile.sheet_name,
            row_count=sheet_profile.row_count,
            column_count=sheet_profile.column_count,
            classification=self._schema_classifier.classify(sheet_profile.columns),
            columns=sheet_profile.columns,
        )

    def aggregate(
        self,
        file_path: Path,
        sheet_name: str,
        group_by: tuple[str, ...],
        limit: int = 10,
        filters: dict[str, object] | None = None,
    ) -> LedgerAggregationReport:
        canonical_frame = self._load_canonical_frame(file_path, sheet_name)
        safe_filters = _safe_query_filters(filters or {})
        dataframe = _filter_frame(canonical_frame, safe_filters)
        amount_column = _calculation_amount_column(canonical_frame)
        aggregations = tuple(
            _aggregate_field(
                dataframe=dataframe,
                canonical_field=canonical_field,
                source_column=canonical_frame.fields[canonical_field],
                amount_column=amount_column,
                raw_amount_column=canonical_frame.fields["amount"],
                limit=limit,
            )
            for canonical_field in group_by
            if canonical_field in LEDGER_AGGREGATION_FIELDS
            and canonical_field in canonical_frame.fields
        )
        return LedgerAggregationReport(
            sheet_name=sheet_name,
            row_count=len(dataframe),
            amount_field=canonical_frame.fields["amount"],
            aggregations=aggregations,
            sign_convention=_sign_convention(canonical_frame),
            filters=safe_filters,
        )

    def query_entries(
        self,
        file_path: Path,
        sheet_name: str,
        filters: dict[str, object],
        page: int = 1,
        page_size: int = 20,
    ) -> LedgerQueryReport:
        canonical_frame = self._load_canonical_frame(file_path, sheet_name)
        dataframe = _filter_frame(canonical_frame, filters)
        safe_page = max(1, page)
        safe_page_size = min(max(1, page_size), 50)
        start_index = (safe_page - 1) * safe_page_size
        end_index = start_index + safe_page_size
        entries = tuple(
            _serialize_query_row(
                row,
                canonical_frame.fields,
                amount_column=_calculation_amount_column(canonical_frame),
            )
            for _, row in dataframe.iloc[start_index:end_index].iterrows()
        )
        return LedgerQueryReport(
            sheet_name=sheet_name,
            total_matches=len(dataframe),
            page=safe_page,
            page_size=safe_page_size,
            filters=_safe_query_filters(filters),
            returned_columns=_returned_query_columns(canonical_frame.fields),
            message=_query_message(len(dataframe)),
            entries=entries,
            sign_convention=_sign_convention(canonical_frame),
        )

    def calculate_metrics(
        self,
        file_path: Path,
        sheet_name: str,
        filters: dict[str, object],
        metrics: tuple[str, ...],
        top_by: str | None = None,
        top_limit: int = 10,
    ) -> LedgerMetricsReport:
        canonical_frame = self._load_canonical_frame(file_path, sheet_name)
        dataframe = _filter_frame(canonical_frame, filters)
        amount_column = _calculation_amount_column(canonical_frame)
        amount_series = dataframe[amount_column].fillna(0)
        balance_series = None
        if "balance" in metrics:
            if canonical_frame.signed_amount_column is None:
                raise LedgerSchemaValidationError(
                    "posting key column is required to calculate balance",
                )
            balance_series = amount_series
        calculated_metrics = _calculate_metrics(
            amount_series,
            metrics,
            balance_series=balance_series,
        )
        metrics_by_currency = _calculate_metrics_by_currency(
            dataframe=dataframe,
            currency_column=canonical_frame.fields.get("currency"),
            amount_column=amount_column,
            metrics=metrics,
        )
        balance_interpretation = None
        balance_reconciliation = None
        if balance_series is not None:
            balance_interpretation = _interpret_account_balance(
                dataframe=dataframe,
                account_column=canonical_frame.fields["account"],
                signed_amounts=balance_series,
                rules=self._account_balance_rules,
            )
            balance_reconciliation = _build_balance_reconciliation(
                dataframe=dataframe,
                fields=canonical_frame.fields,
                signed_amount_column=amount_column,
                posting_key_rules=self._posting_key_rules,
            )
        top = None
        if top_by is not None and top_by in canonical_frame.fields:
            top = _aggregate_field(
                dataframe=dataframe,
                canonical_field=top_by,
                source_column=canonical_frame.fields[top_by],
                amount_column=amount_column,
                raw_amount_column=canonical_frame.fields["amount"],
                limit=top_limit,
            )
        return LedgerMetricsReport(
            sheet_name=sheet_name,
            total_matches=len(dataframe),
            amount_field=canonical_frame.fields["amount"],
            metrics=calculated_metrics,
            top=top,
            sign_convention=(
                _sign_convention(canonical_frame)
            ),
            balance_interpretation=balance_interpretation,
            metrics_by_currency=metrics_by_currency,
            filters=_safe_query_filters(filters),
            balance_reconciliation=balance_reconciliation,
        )

    def detect_data_quality_issues(
        self,
        file_path: Path,
        sheet_name: str,
    ) -> LedgerDataQualityReport:
        canonical_frame = self._load_canonical_frame(file_path, sheet_name)
        issues = _detect_quality_issues(canonical_frame)
        severity_counts = _count_issue_severities(issues)
        return LedgerDataQualityReport(
            sheet_name=sheet_name,
            row_count=canonical_frame.row_count,
            issue_count=len(issues),
            severity_counts=severity_counts,
            issues=issues,
        )

    def detect_tax_candidates(
        self,
        file_path: Path,
        sheet_name: str,
        limit: int = LEDGER_TAX_CANDIDATE_LIMIT,
    ) -> LedgerTaxCandidateReport:
        canonical_frame = self._load_canonical_frame(file_path, sheet_name)
        candidates = _detect_tax_candidates(
            canonical_frame=canonical_frame,
            rules=self._tax_candidate_rules,
            limit=limit,
        )
        return LedgerTaxCandidateReport(
            sheet_name=sheet_name,
            row_count=canonical_frame.row_count,
            decision_status="review_required",
            candidates=candidates,
            sign_convention=_sign_convention(canonical_frame),
        )

    def _load_canonical_frame(
        self,
        file_path: Path,
        sheet_name: str,
    ) -> "_CanonicalLedgerFrame":
        cache_key = (str(file_path.resolve()), sheet_name)
        cached_frame = self._canonical_frame_cache.get(cache_key)
        if cached_frame is not None:
            return cached_frame
        sheet_profile = self._sheet_profile_cache.get(cache_key)
        if sheet_profile is None:
            sheet_profile = self._excel_tools.profile_sheet(file_path, sheet_name)
            self._sheet_profile_cache[cache_key] = sheet_profile
        resolved_path = sheet_profile.file_path
        classification = self._schema_classifier.classify(sheet_profile.columns)
        if not classification.is_usable:
            missing_fields = tuple(
                mapping.canonical_field
                for mapping in classification.mappings
                if mapping.canonical_field in {"account", "amount", "text"}
                and mapping.status != "mapped"
            )
            raise LedgerSchemaValidationError(
                f"canonical ledger schema is not usable: {', '.join(missing_fields)}",
            )
        fields = {
            mapping.canonical_field: mapping.source_column
            for mapping in classification.mappings
            if mapping.status == "mapped" and mapping.source_column is not None
        }
        dataframe = pd.read_excel(
            resolved_path,
            sheet_name=sheet_name,
            usecols=sorted(set(fields.values())),
            engine="openpyxl",
        )
        signed_amount_column = None
        if "posting_key" in fields:
            dataframe[SIGNED_AMOUNT_COLUMN] = _signed_amount_series(
                dataframe=dataframe,
                fields=fields,
                posting_key_rules=self._posting_key_rules,
            )
            signed_amount_column = SIGNED_AMOUNT_COLUMN
        canonical_frame = _CanonicalLedgerFrame(
            dataframe=dataframe,
            fields=fields,
            row_count=sheet_profile.row_count,
            columns=sheet_profile.columns,
            signed_amount_column=signed_amount_column,
        )
        self._canonical_frame_cache[cache_key] = canonical_frame
        return canonical_frame


def _canonical_schema_report(
    column_names: tuple[str, ...],
    classification: LedgerSchemaClassification,
) -> LedgerSchemaReport:
    missing_required_columns = tuple(
        mapping.canonical_field
        for mapping in classification.mappings
        if mapping.canonical_field in {"account", "amount", "text"}
        and mapping.status != "mapped"
    )
    return LedgerSchemaReport(
        is_valid=classification.is_usable,
        present_columns=column_names,
        missing_required_columns=missing_required_columns,
        optional_columns=tuple(
            mapping.source_column
            for mapping in classification.mappings
            if mapping.status == "mapped"
            and mapping.canonical_field not in {"account", "amount", "text"}
            and mapping.source_column is not None
        ),
    )


@dataclass(frozen=True)
class _CanonicalLedgerFrame:
    dataframe: pd.DataFrame
    fields: dict[str, str]
    row_count: int
    columns: tuple[ExcelColumnProfile, ...]
    signed_amount_column: str | None


def _calculation_amount_column(canonical_frame: _CanonicalLedgerFrame) -> str:
    return canonical_frame.signed_amount_column or canonical_frame.fields["amount"]


def _sign_convention(canonical_frame: _CanonicalLedgerFrame) -> str | None:
    if canonical_frame.signed_amount_column is None:
        return None
    return "debit_positive_credit_negative"


def _aggregate_field(
    dataframe: pd.DataFrame,
    canonical_field: str,
    source_column: str,
    amount_column: str,
    raw_amount_column: str,
    limit: int,
) -> LedgerFieldAggregation:
    currency_column = _currency_column(dataframe, source_column)
    group_columns = [source_column]
    prepared_frame = dataframe.assign(
        **{source_column: dataframe[source_column].fillna("Sans valeur")},
    )
    if currency_column is not None:
        prepared_frame = prepared_frame.assign(
            **{currency_column: dataframe[currency_column].fillna("Sans devise")},
        )
        group_columns.append(currency_column)
    raw_amounts = pd.to_numeric(prepared_frame[raw_amount_column], errors="coerce")
    prepared_frame = prepared_frame.assign(__raw_aggregation_amount=raw_amounts)
    groups_list: list[LedgerAggregationGroup] = []
    grouped = prepared_frame.groupby(group_columns, dropna=False)
    for index, group in grouped:
        signed_amounts = group[amount_column]
        entry_count = len(group)
        used_entry_count = int(signed_amounts.notna().sum())
        balance = round(float(signed_amounts.sum()), 2)
        groups_list.append(
            LedgerAggregationGroup(
                key=str(index[0] if isinstance(index, tuple) else index),
                entry_count=entry_count,
                amount_sum=balance,
                currency=(
                    str(index[1])
                    if isinstance(index, tuple) and len(index) > 1
                    else None
                ),
                used_entry_count=used_entry_count,
                excluded_entry_count=entry_count - used_entry_count,
                raw_amount_sum=round(
                    float(group["__raw_aggregation_amount"].sum()),
                    2,
                ),
                debit_total=round(float(signed_amounts.clip(lower=0).sum()), 2),
                credit_total=round(
                    float((-signed_amounts.clip(upper=0)).sum()),
                    2,
                ),
                balance=balance,
            ),
        )
    groups_list.sort(
        key=lambda group: (group.balance, group.entry_count),
        reverse=True,
    )
    groups = tuple(groups_list[: max(1, limit)])
    return LedgerFieldAggregation(
        canonical_field=canonical_field,
        source_column=source_column,
        total_groups=len(groups_list),
        groups=groups,
    )


def _currency_column(dataframe: pd.DataFrame, grouped_column: str) -> str | None:
    candidates = tuple(
        column
        for column in dataframe.columns
        if column != grouped_column and _normalize_for_search(column) in {
            "devise du document",
            "devise document",
            "devise de la piece",
            "devise piece",
            "devise interne",
            "devise",
            "currency",
        }
    )
    return candidates[0] if candidates else None


def _filter_frame(
    canonical_frame: _CanonicalLedgerFrame,
    filters: dict[str, object],
) -> pd.DataFrame:
    dataframe = canonical_frame.dataframe
    mask = pd.Series(True, index=dataframe.index)
    for canonical_field in (
        "account",
        "period",
        "fiscal_year",
        "tax_code",
        "vendor",
        "customer",
    ):
        raw_value = filters.get(canonical_field)
        source_column = canonical_frame.fields.get(canonical_field)
        if raw_value is None or source_column is None:
            continue
        mask &= dataframe[source_column].map(_stable_cell_value) == str(raw_value)
    amount_column = _calculation_amount_column(canonical_frame)
    amount_min = filters.get("amount_min")
    if isinstance(amount_min, int | float):
        mask &= dataframe[amount_column].fillna(0) >= amount_min
    amount_max = filters.get("amount_max")
    if isinstance(amount_max, int | float):
        mask &= dataframe[amount_column].fillna(0) <= amount_max
    return dataframe.loc[mask].copy()


def _serialize_query_row(
    row: pd.Series,
    fields: dict[str, str],
    amount_column: str,
) -> dict[str, object]:
    serialized_row: dict[str, object] = {}
    for canonical_field in LEDGER_QUERY_OUTPUT_FIELDS:
        source_column = (
            amount_column
            if canonical_field == "amount"
            else fields.get(canonical_field)
        )
        if source_column is None:
            continue
        value = row[source_column]
        serialized_row[canonical_field] = (
            _normalize_posting_key(value)
            if canonical_field == "posting_key"
            else _stable_cell_value(value)
        )
    return serialized_row


def _returned_query_columns(fields: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        canonical_field
        for canonical_field in LEDGER_QUERY_OUTPUT_FIELDS
        if canonical_field in fields
    )


def _safe_query_filters(filters: dict[str, object]) -> dict[str, object]:
    allowed_filter_names = {
        "account",
        "period",
        "fiscal_year",
        "tax_code",
        "vendor",
        "customer",
        "amount_min",
        "amount_max",
    }
    return {
        filter_name: filter_value
        for filter_name, filter_value in filters.items()
        if filter_name in allowed_filter_names and filter_value is not None
    }


def _query_message(total_matches: int) -> str:
    if total_matches == 0:
        return "Aucune écriture ne correspond aux filtres fournis."
    return "Écritures trouvées pour les filtres fournis."


def _calculate_metrics(
    amount_series: pd.Series,
    metrics: tuple[str, ...],
    balance_series: pd.Series | None = None,
) -> dict[str, float | int]:
    requested_metrics = metrics or ("sum", "count", "average", "min", "max")
    output: dict[str, float | int] = {}
    if "balance" in requested_metrics:
        if balance_series is None:
            raise LedgerSchemaValidationError(
                "posting key rules are required to calculate balance",
            )
        output["balance"] = round(float(balance_series.sum()), 2)
    if "sum" in requested_metrics:
        output["sum"] = round(float(amount_series.sum()), 2)
    if "count" in requested_metrics:
        output["count"] = int(amount_series.count())
    if "average" in requested_metrics:
        output["average"] = (
            round(float(amount_series.mean()), 2) if len(amount_series) else 0.0
        )
    if "min" in requested_metrics:
        output["min"] = (
            round(float(amount_series.min()), 2) if len(amount_series) else 0.0
        )
    if "max" in requested_metrics:
        output["max"] = (
            round(float(amount_series.max()), 2) if len(amount_series) else 0.0
        )
    return output


def _calculate_metrics_by_currency(
    dataframe: pd.DataFrame,
    currency_column: str | None,
    amount_column: str,
    metrics: tuple[str, ...],
) -> dict[str, dict[str, float | int]] | None:
    if currency_column is None:
        return None
    output: dict[str, dict[str, float | int]] = {}
    currencies = dataframe[currency_column].fillna("Sans devise")
    for currency in sorted(currencies.astype(str).unique()):
        currency_amounts = dataframe.loc[
            currencies.astype(str) == currency,
            amount_column,
        ].fillna(0)
        output[currency] = _calculate_metrics(
            currency_amounts,
            metrics,
            balance_series=(currency_amounts if "balance" in metrics else None),
        )
    return output


def _build_balance_reconciliation(
    dataframe: pd.DataFrame,
    fields: dict[str, str],
    signed_amount_column: str,
    posting_key_rules: dict[str, PostingKeyRule],
) -> dict[str, object]:
    raw_amounts = pd.to_numeric(dataframe[fields["amount"]], errors="coerce")
    signed_amounts = dataframe[signed_amount_column]
    included_mask = signed_amounts.notna()
    posting_keys = dataframe[fields["posting_key"]].map(_normalize_posting_key)
    currencies = (
        dataframe[fields["currency"]].fillna("Sans devise").astype(str)
        if "currency" in fields
        else pd.Series("Sans devise", index=dataframe.index)
    )

    def totals(mask: pd.Series) -> dict[str, float | int]:
        scoped_signed = signed_amounts.loc[mask]
        scoped_raw = raw_amounts.loc[mask]
        scoped_included = scoped_signed.notna()
        return {
            "entry_count": int(mask.sum()),
            "used_entry_count": int(scoped_included.sum()),
            "excluded_entry_count": int((~scoped_included).sum()),
            "raw_amount_sum": round(float(scoped_raw.sum()), 2),
            "debit_total": round(float(scoped_signed.clip(lower=0).sum()), 2),
            "credit_total": round(float((-scoped_signed.clip(upper=0)).sum()), 2),
            "balance": round(float(scoped_signed.sum()), 2),
        }

    by_currency = {
        currency: totals(currencies == currency)
        for currency in sorted(currencies.unique())
    }
    by_posting_key: list[dict[str, object]] = []
    for posting_key in sorted(posting_keys.unique()):
        mask = posting_keys == posting_key
        rule = posting_key_rules.get(posting_key)
        key_totals = totals(mask)
        by_posting_key.append(
            {
                "posting_key": posting_key or "Sans clé",
                "side": rule.side if rule is not None else "unknown",
                **key_totals,
            },
        )

    return {
        **totals(pd.Series(True, index=dataframe.index)),
        "formula": "balance = debit_total - credit_total",
        "currency_count": len(by_currency),
        "by_currency": by_currency,
        "by_posting_key": by_posting_key,
        "excluded_reasons": {
            "missing_or_unknown_posting_key": int(
                ((~included_mask) & raw_amounts.notna()).sum(),
            ),
            "missing_or_invalid_amount": int(raw_amounts.isna().sum()),
        },
    }


def _interpret_account_balance(
    dataframe: pd.DataFrame,
    account_column: str,
    signed_amounts: pd.Series,
    rules: tuple[AccountBalanceRule, ...],
) -> dict[str, object]:
    technical_balance = round(float(signed_amounts.sum()), 2)
    debit_total = round(float(signed_amounts.clip(lower=0).sum()), 2)
    credit_total = round(float((-signed_amounts.clip(upper=0)).sum()), 2)
    if technical_balance > 0:
        balance_side = "debit"
    elif technical_balance < 0:
        balance_side = "credit"
    else:
        balance_side = "balanced"
    accounts = tuple(
        sorted(
            {
                str(_stable_cell_value(value))
                for value in dataframe[account_column].dropna()
            },
        ),
    )
    interpretation: dict[str, object] = {
        "debit_total": debit_total,
        "credit_total": credit_total,
        "technical_balance": technical_balance,
        "balance_side": balance_side,
        "account": accounts[0] if len(accounts) == 1 else None,
        "normal_side": "unknown",
        "nature": "unknown",
        "status": "not_interpretable",
        "natural_balance": None,
        "matched_prefix": None,
    }
    if len(accounts) != 1:
        return interpretation
    rule = find_account_balance_rule(accounts[0], rules)
    if rule is None:
        return interpretation
    interpretation.update(
        normal_side=rule.normal_side,
        nature=rule.nature,
        matched_prefix=rule.account_prefix,
    )
    if rule.normal_side == "variable":
        interpretation["status"] = "variable"
        return interpretation
    interpretation["natural_balance"] = round(
        technical_balance if rule.normal_side == "debit" else -technical_balance,
        2,
    )
    interpretation["status"] = (
        "normal"
        if balance_side in {rule.normal_side, "balanced"}
        else "unusual"
    )
    return interpretation


def _signed_amount_series(
    dataframe: pd.DataFrame,
    fields: dict[str, str],
    posting_key_rules: dict[str, PostingKeyRule],
) -> pd.Series:
    posting_key_column = fields.get("posting_key")
    if posting_key_column is None:
        raise LedgerSchemaValidationError(
            "posting key column is required to calculate balance",
        )
    if not posting_key_rules:
        raise LedgerSchemaValidationError(
            "posting key rules are required to calculate balance",
        )

    posting_keys = dataframe[posting_key_column].map(_normalize_posting_key)
    amount_column = fields["amount"]
    amounts = pd.to_numeric(dataframe[amount_column], errors="coerce")
    signs = posting_keys.map(
        lambda key: (
            1
            if key in posting_key_rules and posting_key_rules[key].side == "debit"
            else -1
            if key in posting_key_rules
            else float("nan")
        ),
    )
    return amounts.abs() * signs


def _normalize_posting_key(value: object) -> str:
    stable_value = str(_stable_cell_value(value))
    return stable_value.zfill(2) if stable_value.isdigit() else stable_value


def _detect_quality_issues(
    canonical_frame: _CanonicalLedgerFrame,
) -> tuple[LedgerDataQualityIssue, ...]:
    issues: list[LedgerDataQualityIssue] = []
    issues.extend(_empty_column_issues(canonical_frame))
    issues.extend(_missing_critical_field_issues(canonical_frame))
    issues.extend(_amount_quality_issues(canonical_frame))
    posting_key_issue = _posting_key_quality_issue(canonical_frame)
    if posting_key_issue is not None:
        issues.append(posting_key_issue)
    currency_issue = _multiple_currency_issue(canonical_frame)
    if currency_issue is not None:
        issues.append(currency_issue)
    counterparty_issue = _missing_counterparty_issue(canonical_frame)
    if counterparty_issue is not None:
        issues.append(counterparty_issue)
    period_issue = _period_range_issue(canonical_frame)
    if period_issue is not None:
        issues.append(period_issue)
    return tuple(issues)


def _empty_column_issues(
    canonical_frame: _CanonicalLedgerFrame,
) -> tuple[LedgerDataQualityIssue, ...]:
    return tuple(
        _quality_issue(
            issue_type="empty_column",
            severity="warning",
            canonical_field=None,
            source_column=column.name,
            affected_count=canonical_frame.row_count,
            row_count=canonical_frame.row_count,
            message="Colonne totalement vide détectée.",
        )
        for column in canonical_frame.columns
        if column.non_empty_count == 0
    )


def _missing_critical_field_issues(
    canonical_frame: _CanonicalLedgerFrame,
) -> tuple[LedgerDataQualityIssue, ...]:
    issues: list[LedgerDataQualityIssue] = []
    for canonical_field in LEDGER_QUALITY_CRITICAL_FIELDS:
        source_column = canonical_frame.fields.get(canonical_field)
        if source_column is None:
            continue
        missing_count = int(canonical_frame.dataframe[source_column].isna().sum())
        if missing_count <= 0:
            continue
        issues.append(
            _quality_issue(
                issue_type="missing_critical_value",
                severity="error",
                canonical_field=canonical_field,
                source_column=source_column,
                affected_count=missing_count,
                row_count=canonical_frame.row_count,
                message="Valeur critique manquante.",
            ),
        )
    return tuple(issues)


def _amount_quality_issues(
    canonical_frame: _CanonicalLedgerFrame,
) -> tuple[LedgerDataQualityIssue, ...]:
    amount_column = canonical_frame.fields["amount"]
    numeric_amount = pd.to_numeric(
        canonical_frame.dataframe[amount_column],
        errors="coerce",
    )
    invalid_count = int(numeric_amount.isna().sum())
    if invalid_count <= 0:
        return ()
    return (
        _quality_issue(
            issue_type="invalid_amount",
            severity="error",
            canonical_field="amount",
            source_column=amount_column,
            affected_count=invalid_count,
            row_count=canonical_frame.row_count,
            message="Montant manquant ou non numérique.",
        ),
    )


def _multiple_currency_issue(
    canonical_frame: _CanonicalLedgerFrame,
) -> LedgerDataQualityIssue | None:
    currency_column = canonical_frame.fields.get("currency")
    if currency_column is None:
        return None
    currency_count = int(canonical_frame.dataframe[currency_column].dropna().nunique())
    if currency_count <= 1:
        return None
    return _quality_issue(
        issue_type="multiple_currencies",
        severity="warning",
        canonical_field="currency",
        source_column=currency_column,
        affected_count=currency_count,
        row_count=canonical_frame.row_count,
        message="Plusieurs devises détectées.",
    )


def _posting_key_quality_issue(
    canonical_frame: _CanonicalLedgerFrame,
) -> LedgerDataQualityIssue | None:
    posting_key_column = canonical_frame.fields.get("posting_key")
    if posting_key_column is None:
        return None
    if canonical_frame.signed_amount_column is None:
        return None
    invalid_mask = canonical_frame.dataframe[
        canonical_frame.signed_amount_column
    ].isna()
    raw_amounts = pd.to_numeric(
        canonical_frame.dataframe[canonical_frame.fields["amount"]],
        errors="coerce",
    )
    invalid_mask &= raw_amounts.notna()
    invalid_count = int(invalid_mask.sum())
    if invalid_count <= 0:
        return None
    return LedgerDataQualityIssue(
        issue_type="missing_or_unknown_posting_key",
        severity="warning",
        canonical_field="posting_key",
        source_column=posting_key_column,
        affected_count=invalid_count,
        affected_ratio=_ratio(invalid_count, canonical_frame.row_count),
        message=(
            "Certaines écritures sont exclues des calculs signés car leur clé "
            "de comptabilisation est absente ou inconnue."
        ),
        affected_accounts=_affected_warning_accounts(canonical_frame, invalid_mask),
    )


def _affected_warning_accounts(
    canonical_frame: _CanonicalLedgerFrame,
    invalid_mask: pd.Series,
) -> tuple[LedgerQualityAffectedAccount, ...]:
    account_column = canonical_frame.fields["account"]
    affected_frame = canonical_frame.dataframe.loc[
        invalid_mask & canonical_frame.dataframe[account_column].notna(),
    ]
    account_counts = (
        affected_frame[account_column].map(_stable_cell_value).value_counts()
    )
    return tuple(
        LedgerQualityAffectedAccount(
            account=str(account),
            affected_count=int(count),
        )
        for account, count in account_counts.head(50).items()
    )


def _missing_counterparty_issue(
    canonical_frame: _CanonicalLedgerFrame,
) -> LedgerDataQualityIssue | None:
    source_columns = [
        canonical_frame.fields[canonical_field]
        for canonical_field in LEDGER_COUNTERPARTY_FIELDS
        if canonical_field in canonical_frame.fields
    ]
    if len(source_columns) < 2:
        return None
    missing_mask = canonical_frame.dataframe[source_columns].isna().all(axis=1)
    missing_count = int(missing_mask.sum())
    if missing_count <= 0:
        return None
    return _quality_issue(
        issue_type="missing_counterparty",
        severity="warning",
        canonical_field="vendor_customer",
        source_column=", ".join(source_columns),
        affected_count=missing_count,
        row_count=canonical_frame.row_count,
        message="Aucun tiers fournisseur ou client détecté sur certaines écritures.",
    )


def _period_range_issue(
    canonical_frame: _CanonicalLedgerFrame,
) -> LedgerDataQualityIssue | None:
    period_column = canonical_frame.fields.get("period")
    if period_column is None:
        return None
    numeric_period = pd.to_numeric(
        canonical_frame.dataframe[period_column],
        errors="coerce",
    )
    invalid_mask = numeric_period.isna() | ~numeric_period.between(1, 12)
    invalid_count = int(invalid_mask.sum())
    if invalid_count <= 0:
        return None
    return _quality_issue(
        issue_type="invalid_period",
        severity="warning",
        canonical_field="period",
        source_column=period_column,
        affected_count=invalid_count,
        row_count=canonical_frame.row_count,
        message="Période comptable hors plage attendue 1-12.",
    )


def _quality_issue(
    issue_type: str,
    severity: str,
    canonical_field: str | None,
    source_column: str | None,
    affected_count: int,
    row_count: int,
    message: str,
) -> LedgerDataQualityIssue:
    return LedgerDataQualityIssue(
        issue_type=issue_type,
        severity=severity,
        canonical_field=canonical_field,
        source_column=source_column,
        affected_count=affected_count,
        affected_ratio=_ratio(affected_count, row_count),
        message=message,
    )


def _count_issue_severities(
    issues: tuple[LedgerDataQualityIssue, ...],
) -> dict[str, int]:
    severity_counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
    return severity_counts


def _detect_tax_candidates(
    canonical_frame: _CanonicalLedgerFrame,
    rules: tuple[ClassificationRule, ...],
    limit: int,
) -> tuple[LedgerTaxCandidate, ...]:
    if not rules:
        return ()
    text_column = canonical_frame.fields["text"]
    amount_column = _calculation_amount_column(canonical_frame)
    account_column = canonical_frame.fields["account"]
    searchable_text = canonical_frame.dataframe[text_column].map(_normalize_for_search)
    candidates: list[LedgerTaxCandidate] = []
    for rule in rules:
        if rule.category is RasCategory.OUT_OF_SCOPE:
            continue
        mask = searchable_text.map(
            lambda value, keywords=rule.keywords: _contains_any(value, keywords),
        )
        candidate_frame = canonical_frame.dataframe.loc[mask].copy()
        if candidate_frame.empty:
            continue
        top_accounts = _aggregate_field(
            dataframe=candidate_frame,
            canonical_field="account",
            source_column=account_column,
            amount_column=amount_column,
            raw_amount_column=canonical_frame.fields["amount"],
            limit=limit,
        ).groups
        candidates.append(
            LedgerTaxCandidate(
                category=rule.category.value,
                confidence=rule.confidence,
                entry_count=len(candidate_frame),
                amount_sum=round(
                    float(candidate_frame[amount_column].fillna(0).sum()),
                    2,
                ),
                matched_keywords=_matched_keywords(
                    searchable_text=searchable_text.loc[mask],
                    keywords=rule.keywords,
                ),
                top_accounts=top_accounts,
                action_required=rule.action_required,
                amounts_by_currency=_sum_by_currency(
                    dataframe=candidate_frame,
                    currency_column=canonical_frame.fields.get("currency"),
                    amount_column=amount_column,
                ),
            ),
        )
    return tuple(
        sorted(
            candidates,
            key=lambda candidate: (candidate.amount_sum, candidate.entry_count),
            reverse=True,
        )[: max(1, limit)]
    )


def _normalize_for_search(value: object) -> str:
    without_accents = normalize("NFKD", str(value))
    ascii_value = without_accents.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_value.lower().split())


def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)


def _matched_keywords(
    searchable_text: pd.Series,
    keywords: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        keyword
        for keyword in keywords
        if searchable_text.map(lambda value, keyword=keyword: keyword in value).any()
    )


def _sum_by_currency(
    dataframe: pd.DataFrame,
    currency_column: str | None,
    amount_column: str,
) -> dict[str, float]:
    if currency_column is None:
        return {}
    prepared_frame = dataframe.assign(
        **{currency_column: dataframe[currency_column].fillna("Sans devise")},
    )
    grouped = prepared_frame.groupby(currency_column)[amount_column].sum()
    return {
        str(currency): round(float(amount), 2)
        for currency, amount in grouped.items()
    }


def _ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def _stable_cell_value(value: object) -> object:
    if pd.isna(value):
        return "Sans valeur"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return value
