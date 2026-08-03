from pathlib import Path

from app.agent.tool_router import (
    DeterministicToolRouteRequest,
    route_deterministic_tool_calls,
)


def test_tool_router_selects_data_quality_tool_for_quality_intent() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message="Vérifie les anomalies et la qualité du fichier.",
            file_path=Path("ledger.xlsx"),
            sheet_name="Grand Livre",
            allowed_tools=("detect_data_quality_issues", "detect_tax_candidates"),
        ),
    )

    assert [tool_call.name for tool_call in tool_calls] == [
        "detect_data_quality_issues",
    ]


def test_tool_router_selects_tax_candidates_tool_for_tax_intent() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message="Trouve les candidats RAS à revoir.",
            file_path=Path("ledger.xlsx"),
            sheet_name="Grand Livre",
            allowed_tools=("detect_data_quality_issues", "detect_tax_candidates"),
        ),
    )

    assert [tool_call.name for tool_call in tool_calls] == [
        "detect_tax_candidates",
    ]


def test_tool_router_selects_global_excel_analysis_for_explanation_intent() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message="Explique-moi cet Excel.",
            file_path=Path("ledger.xlsx"),
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

    assert [tool_call.name for tool_call in tool_calls] == [
        "analyze_ledger",
        "calculate_ledger_metrics",
        "aggregate_ledger",
        "detect_data_quality_issues",
        "detect_tax_candidates",
    ]
    assert tool_calls[1].arguments["metrics"] == [
        "sum",
        "count",
        "average",
        "min",
        "max",
    ]
    assert tool_calls[2].arguments["group_by"] == [
        "account",
        "period",
        "document_type",
        "tax_code",
    ]


def test_tool_router_builds_query_filter_for_account_question() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message="Montre-moi toutes les écritures du compte 44585100.",
            file_path=Path("ledger.xlsx"),
            sheet_name="Grand Livre",
            allowed_tools=("query_ledger_entries",),
        ),
    )

    assert len(tool_calls) == 1
    assert tool_calls[0].name == "query_ledger_entries"
    assert tool_calls[0].arguments == {
        "file_path": "ledger.xlsx",
        "sheet_name": "Grand Livre",
        "filters": {"account": "44585100"},
        "page": 1,
        "page_size": 20,
    }


def test_tool_router_selects_signed_metrics_for_account_balance() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message="Quel est le solde actuel du compte 345520 ?",
            file_path=Path("ledger.xlsx"),
            sheet_name="Grand Livre",
            allowed_tools=("query_ledger_entries", "calculate_ledger_metrics"),
        ),
    )

    assert len(tool_calls) == 1
    assert tool_calls[0].name == "calculate_ledger_metrics"
    assert tool_calls[0].arguments == {
        "file_path": "ledger.xlsx",
        "sheet_name": "Grand Livre",
        "filters": {"account": "345520"},
        "metrics": ["balance", "count"],
    }


def test_tool_router_applies_fiscal_year_to_account_balance() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message=(
                "Calcule le solde du compte 61365000 pour l'exercice 2024."
            ),
            file_path=Path("ledger.xlsx"),
            sheet_name="Grand Livre",
            allowed_tools=("calculate_ledger_metrics",),
        ),
    )

    assert tool_calls[0].arguments["filters"] == {
        "account": "61365000",
        "fiscal_year": "2024",
    }


def test_tool_router_routes_filtered_period_aggregation() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message=(
                "Regroupe les montants du compte 61365000 par période "
                "pour l'exercice 2024, en affichant la somme brute, le débit, "
                "le crédit et le solde."
            ),
            file_path=Path("ledger.xlsx"),
            sheet_name="Grand Livre",
            allowed_tools=("aggregate_ledger", "query_ledger_entries"),
        ),
    )

    assert tool_calls[0].name == "aggregate_ledger"
    assert tool_calls[0].arguments["filters"] == {
        "account": "61365000",
        "fiscal_year": "2024",
    }
    assert tool_calls[0].arguments["group_by"] == ["period"]


def test_tool_router_builds_query_filters_for_account_and_period() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message="Montre le compte 44585100 sur la période 12.",
            file_path=Path("ledger.xlsx"),
            sheet_name="Grand Livre",
            allowed_tools=("query_ledger_entries",),
        ),
    )

    assert tool_calls[0].arguments["filters"] == {
        "account": "44585100",
        "period": "12",
    }


def test_tool_router_builds_query_filters_for_tax_vendor_and_amounts() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message=(
                "Liste les écritures TVA V1 fournisseur 40190006 "
                "avec montant entre 10000 et 50000."
            ),
            file_path=Path("ledger.xlsx"),
            sheet_name="Grand Livre",
            allowed_tools=("query_ledger_entries",),
        ),
    )

    assert tool_calls[0].arguments["filters"] == {
        "tax_code": "V1",
        "vendor": "40190006",
        "amount_min": 10000.0,
        "amount_max": 50000.0,
    }


def test_tool_router_requires_file_and_sheet() -> None:
    tool_calls = route_deterministic_tool_calls(
        DeterministicToolRouteRequest(
            user_message="Vérifie la qualité.",
            file_path=Path("ledger.xlsx"),
            sheet_name=None,
            allowed_tools=("detect_data_quality_issues",),
        ),
    )

    assert tool_calls == ()
