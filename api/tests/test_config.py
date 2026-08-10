from app.config import Settings


def test_optional_secret_env_values_treat_blank_strings_as_unconfigured() -> None:
    settings = Settings.model_validate(
        {
            "ras_fact_context_signing_key": "   ",
            "llm_openai_compatible_api_key": "",
            "llm_gemini_api_key": "",
            "llm_groq_api_key": "",
        }
    )

    assert settings.ras_fact_context_signing_key is None
    assert settings.llm_openai_compatible_api_key is None
    assert settings.llm_gemini_api_key is None
    assert settings.llm_groq_api_key is None


def test_optional_secret_env_values_keep_non_blank_values() -> None:
    settings = Settings.model_validate(
        {"ras_fact_context_signing_key": "k" * 32}
    )

    assert settings.ras_fact_context_signing_key is not None
    assert settings.ras_fact_context_signing_key.get_secret_value() == "k" * 32
