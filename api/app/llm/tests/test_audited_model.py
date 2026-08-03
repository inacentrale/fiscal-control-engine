from contextlib import suppress

from app.llm.audited_model import AuditedModelProvider, ModelAuditEvent
from app.llm.domain import (
    ModelMessage,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ModelTimeoutError,
)


def test_audited_provider_records_success_metadata_without_sensitive_content() -> None:
    audit_events: list[ModelAuditEvent] = []
    provider = AuditedModelProvider(
        provider=FakeTimedModelProvider(
            response=_response("Texte sensible a ne pas journaliser"),
        ),
        monotonic=FakeClock((10.0, 10.2)),
        audit_sink=audit_events.append,
    )

    response = provider.generate(_request(content="Prompt confidentiel"))

    assert response.text == "Texte sensible a ne pas journaliser"
    assert audit_events == [
        ModelAuditEvent(
            provider_name="fake",
            model_name="fake-model",
            status="success",
            duration_ms=199,
            finish_reason="stop",
            error_type=None,
        ),
    ]
    assert "Prompt confidentiel" not in repr(audit_events)
    assert "Texte sensible" not in repr(audit_events)


def test_audited_provider_records_error_metadata_without_sensitive_content() -> None:
    audit_events: list[ModelAuditEvent] = []
    provider = AuditedModelProvider(
        provider=FakeTimedModelProvider(error=ModelProviderError("secret failure")),
        monotonic=FakeClock((20.0, 20.1)),
        audit_sink=audit_events.append,
    )

    with suppress(ModelProviderError):
        provider.generate(_request(content="Prompt confidentiel"))

    assert audit_events == [
        ModelAuditEvent(
            provider_name="fake",
            model_name=None,
            status="error",
            duration_ms=100,
            finish_reason=None,
            error_type="ModelProviderError",
        ),
    ]
    assert "Prompt confidentiel" not in repr(audit_events)
    assert "secret failure" not in repr(audit_events)


def test_audited_provider_raises_timeout_when_elapsed_time_exceeds_limit() -> None:
    audit_events: list[ModelAuditEvent] = []
    provider = AuditedModelProvider(
        provider=FakeTimedModelProvider(response=_response("late")),
        monotonic=FakeClock((30.0, 32.5)),
        audit_sink=audit_events.append,
    )

    with suppress(ModelTimeoutError):
        provider.generate(_request(timeout_seconds=1.0))

    assert audit_events == [
        ModelAuditEvent(
            provider_name="fake",
            model_name="fake-model",
            status="timeout",
            duration_ms=2500,
            finish_reason="stop",
            error_type="ModelTimeoutError",
        ),
    ]


def _request(
    content: str = "Analyse",
    timeout_seconds: float = 10.0,
) -> ModelRequest:
    return ModelRequest(
        messages=(ModelMessage(role="user", content=content),),
        allowed_tools=("profile_sheet",),
        temperature=0.0,
        max_output_tokens=300,
        timeout_seconds=timeout_seconds,
    )


def _response(text: str) -> ModelResponse:
    return ModelResponse(
        text=text,
        provider_name="fake",
        model_name="fake-model",
        finish_reason="stop",
        tool_calls=(),
    )


class FakeClock:
    def __init__(self, values: tuple[float, ...]) -> None:
        self._values = list(values)

    def __call__(self) -> float:
        return self._values.pop(0)


class FakeTimedModelProvider:
    provider_name = "fake"

    def __init__(
        self,
        response: ModelResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error

    def generate(self, request: ModelRequest) -> ModelResponse:
        if self._error is not None:
            raise self._error
        if self._response is None:
            raise AssertionError("fake response is required")
        return self._response
