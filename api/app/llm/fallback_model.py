from app.llm.domain import (
    ModelProvider,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ModelTimeoutError,
)


class FallbackModelProvider:
    provider_name = "fallback"

    def __init__(self, providers: tuple[ModelProvider, ...]) -> None:
        if not providers:
            raise ValueError("at least one model provider is required")
        self._providers = providers

    def generate(self, request: ModelRequest) -> ModelResponse:
        for provider in self._providers:
            try:
                return provider.generate(request)
            except (ModelProviderError, ModelTimeoutError):
                continue
        return ModelResponse(
            text=(
                "Le service LLM est momentanement indisponible. "
                "Les controles deterministes restent disponibles."
            ),
            provider_name="internal-fallback",
            model_name="controlled-response",
            finish_reason="provider_failure",
            tool_calls=(),
        )
