import pytest

from app.llm.audited_model import ModelAuditEvent
from app.llm.domain import ModelMessage, ModelRequest
from app.llm.fallback_model import FallbackModelProvider
from app.llm.model_provider_factory import create_model_provider


def test_factory_creates_internal_controlled_provider() -> None:
    audit_events: list[ModelAuditEvent] = []
    provider = create_model_provider(
        "internal:controlled-response",
        audit_sink=audit_events.append,
    )

    response = provider.generate(_request())

    assert response.provider_name == "internal"
    assert response.model_name == "controlled-response"
    assert "contrôles déterministes" in response.text
    assert audit_events[0].provider_name == "internal"
    assert audit_events[0].model_name == "controlled-response"
    assert audit_events[0].status == "success"


def test_factory_creates_fallback_chain() -> None:
    provider = create_model_provider(
        "internal:controlled-response,internal:controlled-response",
    )

    assert isinstance(provider, FallbackModelProvider)


def test_factory_creates_openai_compatible_provider_with_internal_fallback() -> None:
    provider = create_model_provider(
        "openai-compatible:gpt-test,internal:controlled-response",
        openai_compatible_api_key="secret-key",
        openai_compatible_base_url="https://llm.example.test/v1",
    )

    assert isinstance(provider, FallbackModelProvider)


def test_factory_creates_gemini_groq_internal_fallback_chain() -> None:
    provider = create_model_provider(
        "gemini:gemini-test,groq:llama-test,internal:controlled-response",
        gemini_api_key="gemini-api-key",
        groq_api_key="groq-api-key",
    )

    assert isinstance(provider, FallbackModelProvider)


def test_factory_rejects_openai_compatible_provider_without_api_key() -> None:
    with pytest.raises(ValueError, match="api key is required"):
        create_model_provider("openai-compatible:gpt-test")


def test_factory_rejects_gemini_provider_without_api_key() -> None:
    with pytest.raises(ValueError, match="gemini api key is required"):
        create_model_provider("gemini:gemini-test")


def test_factory_rejects_groq_provider_without_api_key() -> None:
    with pytest.raises(ValueError, match="groq api key is required"):
        create_model_provider("groq:llama-test")


def test_factory_rejects_unknown_external_provider() -> None:
    with pytest.raises(ValueError, match="unsupported model provider"):
        create_model_provider("unknown:gpt-test")


def _request() -> ModelRequest:
    return ModelRequest(
        messages=(ModelMessage(role="user", content="Analyse"),),
        allowed_tools=("profile_sheet",),
        temperature=0.0,
        max_output_tokens=300,
        timeout_seconds=10.0,
    )
