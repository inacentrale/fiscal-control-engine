from app.llm.domain import (
    ModelMessage,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ModelTimeoutError,
)
from app.llm.fallback_model import FallbackModelProvider


def test_fallback_provider_uses_primary_model_when_successful() -> None:
    primary = FakeModelProvider(
        provider_name="primary",
        response=ModelResponse(
            text="analyse",
            provider_name="primary",
            model_name="model-a",
            finish_reason="stop",
            tool_calls=(),
        ),
    )
    fallback = FallbackModelProvider((primary,))

    response = fallback.generate(_request())

    assert response.text == "analyse"
    assert response.provider_name == "primary"
    assert primary.calls == 1


def test_fallback_provider_uses_secondary_model_after_timeout() -> None:
    primary = FakeModelProvider(provider_name="primary", error=ModelTimeoutError())
    secondary = FakeModelProvider(
        provider_name="secondary",
        response=ModelResponse(
            text="analyse fallback",
            provider_name="secondary",
            model_name="model-b",
            finish_reason="stop",
            tool_calls=(),
        ),
    )
    fallback = FallbackModelProvider((primary, secondary))

    response = fallback.generate(_request())

    assert response.text == "analyse fallback"
    assert response.provider_name == "secondary"
    assert primary.calls == 1
    assert secondary.calls == 1


def test_fallback_provider_returns_controlled_response_when_all_models_fail() -> None:
    fallback = FallbackModelProvider(
        (
            FakeModelProvider(provider_name="primary", error=ModelProviderError()),
            FakeModelProvider(provider_name="secondary", error=ModelTimeoutError()),
        ),
    )

    response = fallback.generate(_request())

    assert response.provider_name == "internal-fallback"
    assert response.model_name == "controlled-response"
    assert response.finish_reason == "provider_failure"
    assert "indisponible" in response.text


def _request() -> ModelRequest:
    return ModelRequest(
        messages=(ModelMessage(role="user", content="Profile ce fichier Excel"),),
        allowed_tools=("profile_sheet",),
        temperature=0.0,
        max_output_tokens=500,
        timeout_seconds=10.0,
    )


class FakeModelProvider:
    def __init__(
        self,
        provider_name: str,
        response: ModelResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.provider_name = provider_name
        self._response = response
        self._error = error
        self.calls = 0

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        if self._error is not None:
            raise self._error
        if self._response is None:
            raise AssertionError("fake response is required when no error is set")
        return self._response
