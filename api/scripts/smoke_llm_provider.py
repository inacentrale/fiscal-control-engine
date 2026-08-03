from app.config import get_settings
from app.llm.model_provider_factory import create_model_provider
from app.llm.smoke_check import LLMProviderSmokeCheck


def main() -> int:
    settings = get_settings()
    openai_compatible_api_key = (
        settings.llm_openai_compatible_api_key.get_secret_value()
        if settings.llm_openai_compatible_api_key is not None
        else None
    )
    gemini_api_key = (
        settings.llm_gemini_api_key.get_secret_value()
        if settings.llm_gemini_api_key is not None
        else None
    )
    groq_api_key = (
        settings.llm_groq_api_key.get_secret_value()
        if settings.llm_groq_api_key is not None
        else None
    )
    uses_openai_compatible = "openai-compatible:" in settings.llm_provider_chain
    if uses_openai_compatible and not openai_compatible_api_key:
        print("LLM smoke check skipped: missing LLM_OPENAI_COMPATIBLE_API_KEY")
        return 2
    if "gemini:" in settings.llm_provider_chain and not gemini_api_key:
        print("LLM smoke check skipped: missing LLM_GEMINI_API_KEY")
        return 2
    if "groq:" in settings.llm_provider_chain and not groq_api_key:
        print("LLM smoke check skipped: missing LLM_GROQ_API_KEY")
        return 2

    provider = create_model_provider(
        provider_chain=settings.llm_provider_chain,
        openai_compatible_api_key=openai_compatible_api_key,
        openai_compatible_base_url=settings.llm_openai_compatible_base_url,
        gemini_api_key=gemini_api_key,
        gemini_base_url=settings.llm_gemini_base_url,
        groq_api_key=groq_api_key,
        groq_base_url=settings.llm_groq_base_url,
    )
    result = LLMProviderSmokeCheck(provider=provider).run()
    print(
        "LLM smoke check ok: "
        f"provider={result.provider_name} "
        f"model={result.model_name} "
        f"finish_reason={result.finish_reason}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
