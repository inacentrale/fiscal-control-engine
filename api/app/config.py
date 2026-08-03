from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    vat_validation_rules_path: str = (
        "../docs/reference/bf-vat-validation-rules.csv"
    )
    withholding_validation_rules_path: str = (
        "../docs/reference/bf-withholding-validation-rules.csv"
    )
    withholding_deadline_rules_path: str = (
        "../docs/reference/bf-withholding-deadline-rules.csv"
    )
    payroll_tax_validation_rules_path: str = (
        "../docs/reference/bf-iuts-validation-rules.csv"
    )
    tax_assurance_policy_path: str = (
        "../docs/reference/bf-tax-assurance-policy.csv"
    )
    account_mapping_ledger_accounts_path: str = (
        "app/account_mapping/tests/fixtures/ledger_accounts.csv"
    )
    account_mapping_plan_accounts_path: str = (
        "app/account_mapping/tests/fixtures/plan_accounts.csv"
    )
    rag_embedding_provider: str = "deterministic"
    rag_embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
