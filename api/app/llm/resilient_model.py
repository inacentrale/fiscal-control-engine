from app.llm.domain import (
    ModelProvider,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
)


class CircuitBreakerOpenError(ModelProviderError):
    pass


class ResilientModelProvider:
    def __init__(
        self,
        provider: ModelProvider,
        max_attempts: int = 2,
        failure_threshold: int = 3,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be positive")
        self.provider_name = provider.provider_name
        self._provider = provider
        self._max_attempts = max_attempts
        self._failure_threshold = failure_threshold
        self._consecutive_failures = 0

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def generate(self, request: ModelRequest) -> ModelResponse:
        if self._consecutive_failures >= self._failure_threshold:
            raise CircuitBreakerOpenError(
                f"model provider circuit is open: {self.provider_name}",
            )

        last_error: ModelProviderError | None = None
        for _ in range(self._max_attempts):
            try:
                response = self._provider.generate(request)
            except ModelProviderError as exc:
                self._consecutive_failures += 1
                last_error = exc
                if self._consecutive_failures >= self._failure_threshold:
                    break
                continue
            self._consecutive_failures = 0
            return response

        if last_error is not None:
            raise last_error
        raise ModelProviderError(f"model provider failed: {self.provider_name}")
