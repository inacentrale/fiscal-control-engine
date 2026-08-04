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
                        "sheets": {"type": "array"},
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
                    "additionalProperties": False,
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
            AgentToolDefinition(
                name="normalize_gl",
                description=(
                    "Normalise un Grand Livre selon un mapping explicite et "
                    "retourne uniquement provenance, compteurs, anomalies et "
                    "readiness, sans exposer les ecritures au modele."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "additionalProperties": False,
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "column_mapping": {"type": "object"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "content_sha256": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "normalized_count": {"type": "integer"},
                        "rejected_count": {"type": "integer"},
                        "issue_counts": {"type": "object"},
                        "mapped_fields": {"type": "object"},
                        "readiness": {"type": "array"},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "explicit_column_mapping",
                    "summary_only",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="assess_gl_readiness",
                description=(
                    "Evalue les capacites RAS disponibles a partir du schema et "
                    "de la qualite du Grand Livre, sans exposer ses cellules."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "additionalProperties": False,
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "column_mapping": {"type": "object"},
                        "source_scope_complete": {"type": "boolean"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "issue_counts": {"type": "object"},
                        "mapped_fields": {"type": "object"},
                        "readiness": {"type": "array"},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "summary_only",
                    "no_firm_finding",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="reconstruct_accounting_entry",
                description=(
                    "Reconstruit les pieces par societe, exercice, journal et "
                    "numero de piece, puis controle debit et credit par devise."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "additionalProperties": False,
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "column_mapping": {"type": "object"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "entry_count": {"type": "integer"},
                        "balanced_count": {"type": "integer"},
                        "unbalanced_count": {"type": "integer"},
                        "ungrouped_line_count": {"type": "integer"},
                        "issue_counts": {"type": "object"},
                        "currencies": {"type": "array"},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "explicit_accounting_key",
                    "no_amount_based_grouping",
                    "summary_only",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="find_ras_counterpart",
                description=(
                    "Recherche les lignes de RAS dans la piece candidate puis "
                    "les regularisations potentielles, sans confirmer un lien "
                    "documentaire absent."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "additionalProperties": False,
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "column_mapping": {"type": "object"},
                        "related_window_days": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 366,
                        },
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "candidate_piece_count": {"type": "integer"},
                        "status_counts": {"type": "object"},
                        "confirmed_amounts_by_currency": {"type": "object"},
                        "potential_related_amounts_by_currency": {"type": "object"},
                        "potential_adjustments_by_currency": {"type": "object"},
                        "missing_fact_counts": {"type": "object"},
                        "issue_counts": {"type": "object"},
                        "source_scope_complete": {"type": "boolean"},
                        "source_scope_blockers": {"type": "array"},
                        "source_scope_policy_version": {"type": "string"},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "configured_account_mapping_only",
                    "same_entry_first",
                    "scope_completeness_never_inferred",
                    "potential_related_not_confirmed",
                    "summary_only",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="detect_ras_candidates",
                description=(
                    "Repere au niveau de la piece les depenses potentiellement "
                    "concernees par la RAS en combinant le mapping comptable "
                    "de l'organisation et un referentiel de signaux textuels. "
                    "Produit une liste de revue, jamais une decision fiscale."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "additionalProperties": False,
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "column_mapping": {"type": "object"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "evaluated_piece_count": {"type": "integer"},
                        "candidate_piece_count": {"type": "integer"},
                        "excluded_piece_count": {"type": "integer"},
                        "status_counts": {"type": "object"},
                        "signal_counts": {"type": "object"},
                        "operation_hint_counts": {"type": "object"},
                        "candidate_amounts_by_currency": {"type": "object"},
                        "missing_fact_counts": {"type": "object"},
                        "issue_counts": {"type": "object"},
                        "decision_status": {"type": "string"},
                        "semantic_model": {"type": ["object", "null"]},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "configured_account_mapping_only",
                    "versioned_text_signals",
                    "review_only",
                    "no_tax_decision",
                    "piece_level_deduplication",
                    "summary_only",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="classify_transaction_semantics",
                description=(
                    "Rapproche semantiquement les libelles d'une taxonomie RAS "
                    "avec un modele local configure. Retourne seulement des "
                    "suggestions agregees de revue, leurs scores et la version "
                    "du modele; aucune decision fiscale."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "additionalProperties": False,
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "column_mapping": {"type": "object"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "classified_piece_count": {"type": "integer"},
                        "status_counts": {"type": "object"},
                        "signal_counts": {"type": "object"},
                        "missing_fact_counts": {"type": "object"},
                        "score_summary": {"type": "object"},
                        "provider_name": {"type": "string"},
                        "model_name": {"type": "string"},
                        "policy_version": {"type": "string"},
                        "calibration_status": {"type": "string"},
                        "decision_status": {"type": "string"},
                    },
                },
                safeguards=(
                    "allowed_file_only",
                    "semantic_model_must_be_configured",
                    "hash_embeddings_forbidden",
                    "review_only",
                    "no_tax_decision",
                    "summary_only",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="resolve_applicable_ras_rule",
                description=(
                    "Selectionne une regle RAS datee a partir de faits explicites "
                    "et traces. Retourne les faits manquants ou les lacunes de "
                    "source au lieu de deviner une residence, un IFU, une "
                    "exemption ou une convention."
                ),
                input_schema={
                    "type": "object",
                    "required": ["transaction_date"],
                    "additionalProperties": False,
                    "properties": {
                        "transaction_date": {"type": "string"},
                        "jurisdiction": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "rule_id": {"type": ["string", "null"]},
                        "rule_version": {"type": ["string", "null"]},
                        "calculation_method": {"type": ["string", "null"]},
                        "rate_percent": {"type": ["string", "null"]},
                        "missing_facts": {"type": "array"},
                        "alternative_rule_ids": {"type": "array"},
                        "sources": {"type": "array"},
                        "source_assurance": {"type": ["string", "null"]},
                        "fact_sources": {"type": "array"},
                        "fact_attestation": {"type": "object"},
                        "decision_status": {"type": "string"},
                    },
                },
                safeguards=(
                    "dated_rules_only",
                    "source_hash_verified",
                    "scope_and_rate_evidence_separated",
                    "tax_event_rule_versioned_and_sourced",
                    "tax_event_date_attested",
                    "missing_facts_never_guessed",
                    "blocked_rule_never_activated",
                    "provisional_only",
                    "server_fact_attestation_required",
                ),
            ),
            AgentToolDefinition(
                name="calculate_theoretical_ras",
                description=(
                    "Resout la regle datee puis calcule la RAS avec Decimal et "
                    "des parametres juridiques versionnes. Refuse tout calcul "
                    "si un fait, une source, une devise ou une regle manque."
                ),
                input_schema={
                    "type": "object",
                    "required": ["transaction_date"],
                    "additionalProperties": False,
                    "properties": {
                        "transaction_date": {"type": "string"},
                        "jurisdiction": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "legal_resolution_status": {"type": "string"},
                        "calculation_status": {"type": "string"},
                        "rule_id": {"type": ["string", "null"]},
                        "rule_version": {"type": ["string", "null"]},
                        "base_fact_name": {"type": ["string", "null"]},
                        "base_amount": {"type": ["string", "null"]},
                        "expected_amount": {"type": ["string", "null"]},
                        "currency": {"type": ["string", "null"]},
                        "calculation_method": {"type": ["string", "null"]},
                        "rate_percent": {"type": ["string", "null"]},
                        "steps": {"type": "array"},
                        "parameter_versions": {"type": "array"},
                        "legal_sources": {"type": "array"},
                        "missing_facts": {"type": "array"},
                        "rounding_policy": {"type": "string"},
                        "reason": {"type": ["string", "null"]},
                        "decision_status": {"type": "string"},
                        "fact_attestation": {"type": "object"},
                    },
                },
                safeguards=(
                    "decimal_only",
                    "dated_rules_only",
                    "source_hash_verified",
                    "tax_event_rule_versioned_and_sourced",
                    "tax_event_date_attested",
                    "no_currency_conversion",
                    "no_implicit_rounding",
                    "missing_facts_never_guessed",
                    "server_fact_attestation_required",
                ),
            ),
            AgentToolDefinition(
                name="run_ras_audit_batch",
                description=(
                    "Detecte et persiste tous les candidats RAS d'un GL dans "
                    "un audit unique. Sans faits juridiques par candidat, les "
                    "cas restent potentiels ou indetermines."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "additionalProperties": False,
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "column_mapping": {"type": "object"},
                        "related_window_days": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 366,
                        },
                        "max_candidates": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 20_000,
                        },
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "audit_id": {"type": "string"},
                        "candidate_count": {"type": "integer"},
                        "potential_count": {"type": "integer"},
                        "indeterminate_count": {"type": "integer"},
                        "status_counts": {"type": "object"},
                        "review_candidate_ids": {"type": "array"},
                        "remaining_candidate_count": {"type": "integer"},
                        "source_scope_complete": {"type": "boolean"},
                        "source_scope_blockers": {"type": "array"},
                        "decision_status": {"type": "string"},
                    },
                },
                safeguards=(
                    "gl_only",
                    "persisted_candidates_only",
                    "no_global_user_facts_applied",
                    "scope_completeness_never_inferred",
                    "no_tax_decision_without_candidate_facts",
                    "candidate_limit_fails_closed",
                    "server_fact_attestation_required",
                    "never_return_cell_values",
                ),
            ),
            AgentToolDefinition(
                name="query_tax_rag",
                description=(
                    "Recherche des passages fiscaux valides et retourne leurs "
                    "citations. Ce tool informe; il ne decide ni taux ni conformite."
                ),
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "additionalProperties": False,
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 5},
                        "as_of_date": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "as_of_date": {"type": ["string", "null"]},
                        "citations": {"type": "array"},
                        "indexed_source_count": {"type": "integer"},
                        "retrieval_mode": {"type": "string"},
                        "retrieval_policy_version": {"type": "string"},
                        "decision_status": {"type": "string"},
                    },
                },
                safeguards=(
                    "validated_sources_only",
                    "citation_required",
                    "retrieval_only",
                    "no_tax_decision",
                    "max_five_passages",
                ),
            ),
            AgentToolDefinition(
                name="generate_ras_audit_report",
                description=(
                    "Genere la synthese d'un audit RAS deja persiste. "
                    "N'accepte jamais de cas ou de montants fournis par le LLM."
                ),
                input_schema={
                    "type": "object",
                    "required": ["audit_id"],
                    "additionalProperties": False,
                    "properties": {
                        "audit_id": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "report_id": {"type": "string"},
                        "source_sha256": {"type": "string"},
                        "generated_at": {"type": "string"},
                        "case_count": {"type": "integer"},
                        "status_counts": {"type": "object"},
                        "certainty_counts": {"type": "object"},
                        "amount_summaries": {"type": "array"},
                        "details": {"type": "array"},
                        "reference_versions": {"type": "array"},
                        "decision_status": {"type": "string"},
                    },
                },
                safeguards=(
                    "persisted_cases_only",
                    "active_session_and_file_only",
                    "source_hash_required",
                    "reference_versions_required",
                    "no_cross_currency_total",
                    "never_accept_llm_case_payload",
                ),
            ),
            AgentToolDefinition(
                name="assess_ras_accounting",
                description=(
                    "Pour une piece explicitement selectionnee, enchaine "
                    "resolution juridique, calcul theorique et rapprochement "
                    "de la RAS comptabilisee. La date fiscale vient du fait "
                    "generateur atteste; la devise vient du GL."
                ),
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "additionalProperties": False,
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "column_mapping": {"type": "object"},
                        "accounting_entry": {"type": "object"},
                        "candidate_id": {"type": "string"},
                        "base_audit_id": {"type": "string"},
                        "related_window_days": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 366,
                        },
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "row_count": {"type": "integer"},
                        "status": {"type": "string"},
                        "legal_resolution_status": {"type": "string"},
                        "calculation_status": {"type": "string"},
                        "rule_id": {"type": ["string", "null"]},
                        "rule_version": {"type": ["string", "null"]},
                        "expected_amount": {"type": ["string", "null"]},
                        "recorded_amount": {"type": ["string", "null"]},
                        "difference": {"type": ["string", "null"]},
                        "currency": {"type": ["string", "null"]},
                        "tolerance": {"type": ["string", "null"]},
                        "missing_facts": {"type": "array"},
                        "issues": {"type": "array"},
                        "basis_is_complete": {"type": "boolean"},
                        "legal_sources": {"type": "array"},
                        "decision_status": {"type": "string"},
                        "audit_id": {"type": "string"},
                        "fact_attestation": {"type": "object"},
                    },
                },
                safeguards=(
                    "explicit_accounting_entry_selector",
                    "tax_rule_date_derived_from_attested_event",
                    "currency_derived_from_gl",
                    "same_entry_first",
                    "scope_completeness_never_inferred",
                    "potential_adjustment_not_applied",
                    "no_currency_conversion",
                    "provisional_only",
                    "server_fact_attestation_required",
                    "active_session_and_file_only",
                    "never_return_cell_values",
                ),
            ),
        ),
    )
