from dataclasses import dataclass

from app.llm.domain import ModelMessage, ModelProvider, ModelRequest


@dataclass(frozen=True)
class LLMProviderSmokeCheckResult:
    ok: bool
    provider_name: str
    model_name: str
    finish_reason: str


class LLMProviderSmokeCheck:
    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider

    def run(self) -> LLMProviderSmokeCheckResult:
        response = self._provider.generate(
            ModelRequest(
                messages=(ModelMessage(role="user", content="Reponds uniquement: ok"),),
                allowed_tools=(),
                temperature=0.0,
                max_output_tokens=300,
                timeout_seconds=10.0,
            ),
        )
        return LLMProviderSmokeCheckResult(
            ok=True,
            provider_name=response.provider_name,
            model_name=response.model_name,
            finish_reason=response.finish_reason,
        )
