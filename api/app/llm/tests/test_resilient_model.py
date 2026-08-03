import pytest

from app.llm.domain import (
    ModelMessage,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ModelTimeoutError,
)
from app.llm.resilient_model import CircuitBreakerOpenError, ResilientModelProvider


def test_resilient_provider_retries_once_then_returns_success() -> None:
    provider = FlakyModelProvider(
        failures=(ModelTimeoutError(),),
        response=_response("ok after retry"),
    )
    resilient = ResilientModelProvider(provider=provider, max_attempts=2)

    response = resilient.generate(_request())

    assert response.text == "ok after retry"
    assert provider.calls == 2


def test_resilient_provider_stops_after_max_attempts() -> None:
    provider = FlakyModelProvider(
        failures=(ModelProviderError(), ModelProviderError()),
        response=_response("should not happen"),
    )
    resilient = ResilientModelProvider(provider=provider, max_attempts=2)

    with pytest.raises(ModelProviderError):
        resilient.generate(_request())

    assert provider.calls == 2


def test_resilient_provider_opens_circuit_after_threshold() -> None:
    provider = FlakyModelProvider(
        failures=(ModelProviderError(), ModelProviderError()),
        response=_response("should not happen"),
    )
    resilient = ResilientModelProvider(
        provider=provider,
        max_attempts=1,
        failure_threshold=2,
    )

    with pytest.raises(ModelProviderError):
        resilient.generate(_request())
    with pytest.raises(ModelProviderError):
        resilient.generate(_request())
    with pytest.raises(CircuitBreakerOpenError):
        resilient.generate(_request())

    assert provider.calls == 2


def test_resilient_provider_resets_failures_after_success() -> None:
    provider = FlakyModelProvider(
        failures=(ModelProviderError(),),
        response=_response("ok"),
    )
    resilient = ResilientModelProvider(
        provider=provider,
        max_attempts=2,
        failure_threshold=2,
    )

    response = resilient.generate(_request())

    assert response.text == "ok"
    assert resilient.consecutive_failures == 0


def _request() -> ModelRequest:
    return ModelRequest(
        messages=(ModelMessage(role="user", content="Analyse"),),
        allowed_tools=(),
        temperature=0.0,
        max_output_tokens=300,
        timeout_seconds=10.0,
    )


def _response(text: str) -> ModelResponse:
    return ModelResponse(
        text=text,
        provider_name="fake",
        model_name="fake-model",
        finish_reason="stop",
        tool_calls=(),
    )


class FlakyModelProvider:
    provider_name = "fake"

    def __init__(
        self,
        failures: tuple[Exception, ...],
        response: ModelResponse,
    ) -> None:
        self._failures = list(failures)
        self._response = response
        self.calls = 0

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        if self._failures:
            raise self._failures.pop(0)
        return self._response
