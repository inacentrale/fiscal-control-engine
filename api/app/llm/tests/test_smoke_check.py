from app.llm.domain import ModelMessage, ModelRequest, ModelResponse
from app.llm.smoke_check import LLMProviderSmokeCheck


def test_smoke_check_returns_provider_metadata_without_model_text() -> None:
    provider = FakeModelProvider(
        response=ModelResponse(
            text="Contenu modele a ne pas afficher",
            provider_name="openai-compatible",
            model_name="gpt-test",
            finish_reason="stop",
            tool_calls=(),
        ),
    )
    smoke_check = LLMProviderSmokeCheck(provider=provider)

    result = smoke_check.run()

    assert result.ok is True
    assert result.provider_name == "openai-compatible"
    assert result.model_name == "gpt-test"
    assert result.finish_reason == "stop"
    assert "Contenu modele" not in repr(result)
    assert provider.last_request is not None
    assert provider.last_request.messages == (
        ModelMessage(role="user", content="Reponds uniquement: ok"),
    )
    assert provider.last_request.allowed_tools == ()
    assert provider.last_request.max_output_tokens == 300


class FakeModelProvider:
    provider_name = "fake"

    def __init__(self, response: ModelResponse) -> None:
        self._response = response
        self.last_request: ModelRequest | None = None

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        return self._response
