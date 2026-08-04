import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from unicodedata import normalize

from app.llm.domain import ToolCall


@dataclass(frozen=True)
class DeterministicToolRouteRequest:
    user_message: str
    file_path: Path | None
    sheet_name: str | None
    allowed_tools: tuple[str, ...]


def route_deterministic_tool_calls(
    request: DeterministicToolRouteRequest,
) -> tuple[ToolCall, ...]:
    message = _normalize_for_intent(request.user_message)
    if (
        _mentions_tax_legal_research(message)
        and "query_tax_rag" in request.allowed_tools
    ):
        return (
            ToolCall(
                name="query_tax_rag",
                arguments={"query": request.user_message, "limit": 5},
            ),
        )
    tax_event_date = _extract_tax_event_date(request.user_message)
    if (
        _mentions_ras_calculation(message)
        and tax_event_date is not None
        and "calculate_theoretical_ras" in request.allowed_tools
    ):
        return (
            ToolCall(
                name="calculate_theoretical_ras",
                arguments={"transaction_date": tax_event_date.isoformat()},
            ),
        )
    if (
        _mentions_ras_rule_resolution(message)
        and tax_event_date is not None
        and "resolve_applicable_ras_rule" in request.allowed_tools
    ):
        return (
            ToolCall(
                name="resolve_applicable_ras_rule",
                arguments={"transaction_date": tax_event_date.isoformat()},
            ),
        )
    if request.file_path is None:
        return ()

    if _mentions_sheet_list(message) and "list_sheets" in request.allowed_tools:
        return (
            ToolCall(
                name="list_sheets",
                arguments={"file_path": str(request.file_path)},
            ),
        )
    if request.sheet_name is None:
        return ()
    if _mentions_column_list(message) and "get_columns" in request.allowed_tools:
        return (
            ToolCall(
                name="get_columns",
                arguments={
                    "file_path": str(request.file_path),
                    "sheet_name": request.sheet_name,
                },
            ),
        )
    if _mentions_sheet_profile(message) and "profile_sheet" in request.allowed_tools:
        return (
            ToolCall(
                name="profile_sheet",
                arguments={
                    "file_path": str(request.file_path),
                    "sheet_name": request.sheet_name,
                },
            ),
        )
    if (
        _mentions_ledger_schema(message)
        and "classify_ledger_schema" in request.allowed_tools
    ):
        return (
            ToolCall(
                name="classify_ledger_schema",
                arguments={
                    "file_path": str(request.file_path),
                    "sheet_name": request.sheet_name,
                },
            ),
        )

    requested_tools: list[str] = []
    query_filters = _ledger_query_filters(message)
    if _mentions_ras_audit(message) and "run_ras_audit_batch" in request.allowed_tools:
        return (
            ToolCall(
                name="run_ras_audit_batch",
                arguments={
                    "file_path": str(request.file_path),
                    "sheet_name": request.sheet_name,
                },
            ),
        )
    if _mentions_aggregation(message) and "aggregate_ledger" in request.allowed_tools:
        return (
            ToolCall(
                name="aggregate_ledger",
                arguments={
                    "file_path": str(request.file_path),
                    "sheet_name": request.sheet_name,
                    "filters": query_filters,
                    "group_by": list(_aggregation_group_by(message)),
                    "limit": 20,
                },
            ),
        )
    if (
        query_filters
        and _mentions_account_balance(message)
        and "calculate_ledger_metrics" in request.allowed_tools
    ):
        return (
            ToolCall(
                name="calculate_ledger_metrics",
                arguments={
                    "file_path": str(request.file_path),
                    "sheet_name": request.sheet_name,
                    "filters": query_filters,
                    "metrics": ["balance", "count"],
                },
            ),
        )
    if query_filters and "query_ledger_entries" in request.allowed_tools:
        return (
            ToolCall(
                name="query_ledger_entries",
                arguments={
                    "file_path": str(request.file_path),
                    "sheet_name": request.sheet_name,
                    "filters": query_filters,
                    "page": 1,
                    "page_size": 20,
                },
            ),
        )
    if _mentions_data_quality(message):
        requested_tools.append("detect_data_quality_issues")
    if _mentions_ras_candidates(message):
        requested_tools.append(
            "detect_ras_candidates"
            if "detect_ras_candidates" in request.allowed_tools
            else "detect_tax_candidates"
        )
    elif _mentions_tax_candidates(message):
        requested_tools.append("detect_tax_candidates")
    if _mentions_global_excel_explanation(message):
        return _global_excel_analysis_tool_calls(request)

    return tuple(
        ToolCall(
            name=tool_name,
            arguments={
                "file_path": str(request.file_path),
                "sheet_name": request.sheet_name,
            },
        )
        for tool_name in requested_tools
        if tool_name in request.allowed_tools
    )


def _mentions_tax_legal_research(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "que dit le cgi",
            "selon le cgi",
            "quel article",
            "quelle source juridique",
            "source juridique",
            "loi de finances",
            "texte fiscal",
            "regle fiscale applicable",
        )
    )


def _mentions_ras_audit(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "audit ras",
            "audite la ras",
            "auditer la ras",
            "controle ras",
            "controle de la ras",
            "analyse ras",
            "analyse de la ras",
        )
    )


def _mentions_ras_calculation(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "calcule la ras",
            "calcul de la ras",
            "montant de la ras",
            "ras theorique",
        )
    )


def _mentions_ras_rule_resolution(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "quelle regle ras",
            "regle ras applicable",
            "quel taux ras",
            "taux ras applicable",
        )
    )


def _extract_tax_event_date(message: str) -> date | None:
    without_accents = normalize("NFKD", message)
    searchable = without_accents.encode("ascii", "ignore").decode("ascii").lower()
    match = re.search(
        r"\b(?:paiement effectue le|mise en paiement le|loyer acquis au)\s+"
        r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b",
        searchable,
    )
    if match is None:
        return None
    raw_date = match.group(1)
    normalized = (
        raw_date
        if "-" in raw_date
        else f"{raw_date[6:10]}-{raw_date[3:5]}-{raw_date[0:2]}"
    )
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _mentions_global_excel_explanation(message: str) -> bool:
    return any(
        keyword in message
        for keyword in (
            "explique moi cet excel",
            "explique cet excel",
            "explique le fichier",
            "decris cet excel",
            "decris le fichier",
            "analyse cet excel",
            "analyse ce fichier",
            "que contient cet excel",
            "que contient le fichier",
            "resume cet excel",
            "resume le fichier",
        )
    )


def _mentions_sheet_list(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "liste les feuilles",
            "liste des feuilles",
            "quelles feuilles",
            "quels onglets",
            "liste les onglets",
        )
    )


def _mentions_column_list(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "liste les colonnes",
            "liste des colonnes",
            "quelles colonnes",
            "quels champs",
            "en tetes",
        )
    )


def _mentions_sheet_profile(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "profile la feuille",
            "profil de la feuille",
            "profil du fichier",
            "statistiques de la feuille",
        )
    )


def _mentions_ledger_schema(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "classifie le schema",
            "schema du grand livre",
            "structure du grand livre",
            "mapping des colonnes",
        )
    )


def _mentions_aggregation(message: str) -> bool:
    return any(
        keyword in message
        for keyword in (
            "regroupe",
            "regroupement",
            "total par",
            "totaux par",
            "repartition par",
        )
    )


def _aggregation_group_by(message: str) -> tuple[str, ...]:
    dimensions = (
        ("account", ("par compte",)),
        ("period", ("par periode",)),
        ("currency", ("par devise",)),
        ("document_type", ("par type de piece", "par type document")),
        ("tax_code", ("par code tva", "par taxe")),
        ("vendor", ("par fournisseur",)),
        ("customer", ("par client",)),
    )
    selected = tuple(
        field
        for field, keywords in dimensions
        if any(keyword in message for keyword in keywords)
    )
    return selected or ("account",)


def _global_excel_analysis_tool_calls(
    request: DeterministicToolRouteRequest,
) -> tuple[ToolCall, ...]:
    tool_calls = (
        ToolCall(
            name="analyze_ledger",
            arguments={
                "file_path": str(request.file_path),
                "sheet_name": request.sheet_name,
            },
        ),
        ToolCall(
            name="calculate_ledger_metrics",
            arguments={
                "file_path": str(request.file_path),
                "sheet_name": request.sheet_name,
                "metrics": ["sum", "count", "average", "min", "max"],
                "top_by": "account",
                "top_limit": 8,
            },
        ),
        ToolCall(
            name="aggregate_ledger",
            arguments={
                "file_path": str(request.file_path),
                "sheet_name": request.sheet_name,
                "group_by": ["account", "period", "document_type", "tax_code"],
                "limit": 10,
            },
        ),
        ToolCall(
            name="detect_data_quality_issues",
            arguments={
                "file_path": str(request.file_path),
                "sheet_name": request.sheet_name,
            },
        ),
        ToolCall(
            name="detect_tax_candidates",
            arguments={
                "file_path": str(request.file_path),
                "sheet_name": request.sheet_name,
                "limit": 8,
            },
        ),
    )
    return tuple(
        tool_call for tool_call in tool_calls if tool_call.name in request.allowed_tools
    )


def _mentions_data_quality(message: str) -> bool:
    return any(
        keyword in message
        for keyword in (
            "qualite",
            "anomalie",
            "colonnes vides",
            "valeurs manquantes",
            "donnees incoherentes",
            "periode suspecte",
            "tiers absent",
        )
    )


def _mentions_account_balance(message: str) -> bool:
    return any(
        keyword in message
        for keyword in (
            "solde",
            "balance du compte",
            "balance compte",
        )
    )


def _ledger_query_filters(message: str) -> dict[str, object]:
    filters: dict[str, object] = {}
    account = _extract_number_after_label(message, ("compte", "account"))
    if account is not None:
        filters["account"] = account
    period = _extract_number_after_label(message, ("periode", "period"))
    if period is not None:
        filters["period"] = period
    fiscal_year = _extract_number_after_label(
        message,
        ("exercice", "annee", "fiscal year", "year"),
    )
    if fiscal_year is not None:
        filters["fiscal_year"] = fiscal_year
    tax_code = _extract_tax_code(message)
    if tax_code is not None:
        filters["tax_code"] = tax_code
    vendor = _extract_number_after_label(message, ("fournisseur", "vendor"))
    if vendor is not None:
        filters["vendor"] = vendor
    customer = _extract_number_after_label(message, ("client", "customer"))
    if customer is not None:
        filters["customer"] = customer
    filters.update(_extract_amount_range(message))
    return filters


def _extract_number_after_label(
    message: str,
    labels: tuple[str, ...],
) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"\b(?:{label_pattern})\s+([0-9]{{1,12}})\b", message)
    if match is not None:
        return match.group(1)
    return None


def _extract_tax_code(message: str) -> str | None:
    match = re.search(r"\b(?:tva|taxe|tax)\s+([a-zA-Z][a-zA-Z0-9_-]{0,10})\b", message)
    if match is None:
        return None
    return match.group(1).upper()


def _extract_amount_range(message: str) -> dict[str, object]:
    between_match = re.search(
        r"\bmontant\s+(?:entre|de)\s+([0-9][0-9 .,_]*)\s+"
        r"(?:et|a|à|-)\s+([0-9][0-9 .,_]*)\b",
        message,
    )
    if between_match is not None:
        return {
            "amount_min": _to_float(between_match.group(1)),
            "amount_max": _to_float(between_match.group(2)),
        }
    filters: dict[str, object] = {}
    min_match = re.search(
        r"\bmontant\s+(?:min|minimum|superieur a|supérieur à)\s+([0-9][0-9 .,_]*)",
        message,
    )
    if min_match is not None:
        filters["amount_min"] = _to_float(min_match.group(1))
    max_match = re.search(
        r"\bmontant\s+(?:max|maximum|inferieur a|inférieur à)\s+([0-9][0-9 .,_]*)",
        message,
    )
    if max_match is not None:
        filters["amount_max"] = _to_float(max_match.group(1))
    return filters


def _to_float(value: str) -> float:
    return float(value.replace(" ", "").replace("_", "").replace(",", "."))


def _mentions_tax_candidates(message: str) -> bool:
    return any(
        keyword in message
        for keyword in (
            "candidat fiscal",
            "candidats fiscaux",
            "tva",
            "fiscal",
        )
    )


def _mentions_ras_candidates(message: str) -> bool:
    return any(
        keyword in message
        for keyword in (
            "candidat ras",
            "candidats ras",
            "retenue a la source",
            "retenues a la source",
            "ras",
        )
    )


def _normalize_for_intent(value: str) -> str:
    without_accents = normalize("NFKD", value)
    ascii_value = without_accents.encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^a-zA-Z0-9]+", " ", ascii_value.lower()).split())
