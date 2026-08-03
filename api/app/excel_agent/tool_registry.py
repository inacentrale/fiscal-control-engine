from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class AgentToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    safeguards: tuple[str, ...]


class AgentToolRegistry:
    def __init__(self, tools: tuple[AgentToolDefinition, ...]) -> None:
        self._tools = MappingProxyType({tool.name: tool for tool in tools})

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools.keys())

    def get(self, name: str) -> AgentToolDefinition | None:
        return self._tools.get(name)


def create_excel_tool_registry() -> AgentToolRegistry:
    return AgentToolRegistry(
        (
            AgentToolDefinition(
                name="list_sheets",
                description=(
                    "Liste les feuilles disponibles dans un fichier Excel autorise."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path"],
                    "properties": {"file_path": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_names": {"type": "array", "items": {"type": "string"}},
                    },
                },
                safeguards=("allowed_file_only", "metadata_only"),
            ),
            AgentToolDefinition(
                name="get_columns",
                description="Retourne les colonnes d'une feuille Excel autorisee.",
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "columns": {"type": "array", "items": {"type": "string"}},
                    },
                },
                safeguards=("allowed_file_only", "metadata_only"),
            ),
            AgentToolDefinition(
                name="profile_sheet",
                description=(
                    "Produit un profil statistique d'une feuille Excel sans exposer "
                    "les valeurs des cellules."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "column_count": {"type": "integer"},
                        "columns": {"type": "array"},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "metadata_only",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="classify_ledger_schema",
                description=(
                    "Detecte le sens des colonnes d'une feuille Grand Livre "
                    "et les mappe vers un schema canonique sans exposer "
                    "les valeurs des cellules."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "column_count": {"type": "integer"},
                        "schema": {"type": "object"},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "metadata_only",
                    "ledger_schema_mapping",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="analyze_ledger",
                description=(
                    "Analyse le schema et le profil d'une feuille Grand Livre "
                    "sans exposer les valeurs des cellules."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "column_count": {"type": "integer"},
                        "schema": {"type": "object"},
                        "columns": {"type": "array"},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "metadata_only",
                    "ledger_schema_reporting",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="aggregate_ledger",
                description=(
                    "Calcule par groupe la somme brute, les debits, les credits, "
                    "le solde et les lignes exclues du Grand Livre."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "group_by": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "limit": {"type": "integer"},
                        "filters": {"type": "object"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "amount_field": {"type": "string"},
                        "aggregations": {"type": "object"},
                        "sign_convention": {"type": ["string", "null"]},
                        "filters": {"type": ["object", "null"]},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "metadata_only",
                    "ledger_aggregation",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="query_ledger_entries",
                description=(
                    "Filtre les ecritures du Grand Livre avec pagination stricte "
                    "et colonnes de sortie autorisees uniquement."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "filters": {"type": "object"},
                        "page": {"type": "integer"},
                        "page_size": {"type": "integer"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "total_matches": {"type": "integer"},
                        "page": {"type": "integer"},
                        "page_size": {"type": "integer"},
                        "entries": {"type": "array"},
                        "sign_convention": {"type": ["string", "null"]},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "paginated_output",
                    "allowed_columns_only",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="calculate_ledger_metrics",
                description=(
                    "Calcule des metriques explicites sur le Grand Livre: somme, "
                    "solde signe par cle de comptabilisation, nombre, moyenne, "
                    "min, max et top groupes."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "filters": {"type": "object"},
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "top_by": {"type": "string"},
                        "top_limit": {"type": "integer"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "total_matches": {"type": "integer"},
                        "amount_field": {"type": "string"},
                        "metrics": {"type": "object"},
                        "top": {"type": "object"},
                        "sign_convention": {"type": ["string", "null"]},
                        "balance_interpretation": {
                            "type": ["object", "null"],
                        },
                        "metrics_by_currency": {
                            "type": ["object", "null"],
                        },
                        "filters": {"type": ["object", "null"]},
                        "balance_reconciliation": {
                            "type": ["object", "null"],
                        },
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "metadata_only",
                    "ledger_metrics",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="detect_data_quality_issues",
                description=(
                    "Detecte les anomalies de qualite du Grand Livre: colonnes "
                    "vides, valeurs critiques manquantes, montants invalides, "
                    "devises multiples, tiers absents et periodes suspectes."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "issue_count": {"type": "integer"},
                        "severity_counts": {"type": "object"},
                        "issues": {"type": "array"},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "metadata_only",
                    "ledger_data_quality",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="detect_tax_candidates",
                description=(
                    "Detecte des candidats fiscaux a revoir par le metier a "
                    "partir du referentiel versionne, sans decision fiscale finale."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "decision_status": {"type": "string"},
                        "candidates": {"type": "array"},
                        "sign_convention": {"type": ["string", "null"]},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "metadata_only",
                    "review_only",
                    "no_tax_decision",
                    "never_return_cell_values",
                ),
            ),
        ),
    )
