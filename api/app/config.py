from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = API_ROOT.parent


class Settings(BaseSettings):
    app_name: str = "Bank Files Harmonizer API"
    environment: str = "development"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3002"])
    ras_classification_rules_path: str = (
        "../docs/reference/ras-classification-rules.csv"
    )
    posting_key_rules_path: str = "../docs/reference/sap-posting-key-rules.csv"
    account_balance_rules_path: str = (
        "../docs/reference/syscohada-account-balance-rules.csv"
    )
    ras_gl_column_aliases_path: str = "../docs/reference/ras-gl-column-aliases.csv"
    ras_candidate_signals_path: str = "../docs/reference/ras-candidate-signals.csv"
    ras_semantic_policy_path: str = (
        "../docs/reference/ras-semantic-classification-policy.csv"
    )
    ras_semantic_embedding_provider: str = "disabled"
    ras_semantic_embedding_model_name: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    ras_legal_rules_path: str = "../docs/reference/bf-ras-legal-rules.csv"
    ras_legal_repository_root_path: str = ".."
    ras_tax_event_rules_path: str = "../docs/reference/bf-ras-tax-event-rules.csv"
    ras_calculation_parameters_path: str = (
        "../docs/reference/bf-ras-calculation-parameters.csv"
    )
    ras_accounting_assessment_policy_path: str = (
        "../docs/reference/ras-accounting-assessment-policy.csv"
    )
    ras_user_fact_patterns_path: str = "../docs/reference/ras-user-fact-patterns.csv"
    ras_fact_context_signing_key: SecretStr | None = None
    ras_ledger_account_mapping_path: str | None = None
    ras_default_company_code: str | None = None
    ras_batch_max_candidates: int = Field(default=5_000, ge=1, le=20_000)
    vat_validation_rules_path: str = "../docs/reference/bf-vat-validation-rules.csv"
    withholding_validation_rules_path: str = (
        "../docs/reference/bf-withholding-validation-rules.csv"
    )
    withholding_deadline_rules_path: str = (
        "../docs/reference/bf-withholding-deadline-rules.csv"
    )
    payroll_tax_validation_rules_path: str = (
        "../docs/reference/bf-iuts-validation-rules.csv"
    )
    corporate_income_tax_validation_rules_path: str = (
        "../docs/reference/bf-is-validation-rules.csv"
    )
    tax_assurance_policy_path: str = "../docs/reference/bf-tax-assurance-policy.csv"
    account_mapping_ledger_accounts_path: str = (
        "app/account_mapping/tests/fixtures/ledger_accounts.csv"
    )
    account_mapping_plan_accounts_path: str = (
        "app/account_mapping/tests/fixtures/plan_accounts.csv"
    )
    rag_embedding_provider: Literal[
        "disabled", "deterministic", "sentence-transformers"
    ] = "disabled"
    rag_embedding_model_name: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    tax_rag_source_root_path: str = "../docs/source-corpus/fiscal"
    llm_provider_chain: str = "internal:controlled-response"
    llm_openai_compatible_api_key: SecretStr | None = None
    llm_openai_compatible_base_url: str = "https://api.openai.com/v1"
    llm_gemini_api_key: SecretStr | None = None
    llm_gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    llm_groq_api_key: SecretStr | None = None
    llm_groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_default_timeout_seconds: float = 30.0
    llm_max_output_tokens: int = 1200
    excel_agent_allowed_root_path: str = "../docs"
    agent_max_answer_characters: int = 4_000
    agent_file_storage_root_path: str = "../.local/agent-files"
    agent_file_ttl_seconds: int = 86_400
    agent_file_max_upload_bytes: int = 20_000_000
    database_url: str | None = None

    @field_validator(
        "ras_fact_context_signing_key",
        "llm_openai_compatible_api_key",
        "llm_gemini_api_key",
        "llm_groq_api_key",
        mode="before",
    )
    @classmethod
    def _empty_secret_as_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator(
        "ras_ledger_account_mapping_path",
        "ras_default_company_code",
        mode="before",
    )
    @classmethod
    def _empty_optional_string_as_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    model_config = SettingsConfigDict(
        env_file=(
            API_ROOT / ".env",
            PROJECT_ROOT / ".env",
            PROJECT_ROOT / "env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
