from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic

from app.llm.domain import (
    ModelProvider,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ModelTimeoutError,
)


@dataclass(frozen=True)
class ModelAuditEvent:
    provider_name: str
    model_name: str | None
    status: str
    duration_ms: int
    finish_reason: str | None
    error_type: str | None


class AuditedModelProvider:
    def __init__(
        self,
        provider: ModelProvider,
        monotonic: Callable[[], float] = monotonic,
        audit_sink: Callable[[ModelAuditEvent], None] | None = None,
    ) -> None:
        self.provider_name = provider.provider_name
        self._provider = provider
        self._monotonic = monotonic
        self._audit_sink = audit_sink or (lambda event: None)

    def generate(self, request: ModelRequest) -> ModelResponse:
        started_at = self._monotonic()
        try:
            response = self._provider.generate(request)
        except ModelProviderError as exc:
            self._record_error(started_at, exc)
            raise

        duration_ms = _duration_ms(started_at, self._monotonic())
        if duration_ms > request.timeout_seconds * 1000:
            timeout_error = ModelTimeoutError("model provider exceeded timeout")
            self._record(
                ModelAuditEvent(
                    provider_name=self.provider_name,
                    model_name=response.model_name,
                    status="timeout",
                    duration_ms=duration_ms,
                    finish_reason=response.finish_reason,
                    error_type=type(timeout_error).__name__,
                ),
            )
            raise timeout_error

        self._record(
            ModelAuditEvent(
                provider_name=response.provider_name,
                model_name=response.model_name,
                status="success",
                duration_ms=duration_ms,
                finish_reason=response.finish_reason,
                error_type=None,
            ),
        )
        return response

    def _record_error(self, started_at: float, error: ModelProviderError) -> None:
        self._record(
            ModelAuditEvent(
                provider_name=self.provider_name,
                model_name=None,
                status="error",
                duration_ms=_duration_ms(started_at, self._monotonic()),
                finish_reason=None,
                error_type=type(error).__name__,
            ),
        )

    def _record(self, event: ModelAuditEvent) -> None:
        self._audit_sink(event)


def _duration_ms(started_at: float, ended_at: float) -> int:
    return int((ended_at - started_at) * 1000)
