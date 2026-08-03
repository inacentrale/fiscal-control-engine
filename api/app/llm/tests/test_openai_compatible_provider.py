import json
from typing import Any

import pytest

from app.llm.domain import (
    ModelMessage,
    ModelProviderError,
    ModelRequest,
    ModelToolDefinition,
    ToolCall,
)
from app.llm.openai_compatible_provider import OpenAICompatibleChatModelProvider


def test_openai_compatible_provider_sends_chat_completion_payload() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(
            status_code=200,
            payload={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "Analyse disponible."},
                    },
                ],
            },
        ),
    )
    provider = OpenAICompatibleChatModelProvider(
        provider_name="openai-compatible",
        model_name="gpt-test",
        api_key="secret-key",
        base_url="https://llm.example.test/v1",
        http_client=client,
    )

    response = provider.generate(_request())

    assert response.text == "Analyse disponible."
    assert response.provider_name == "openai-compatible"
    assert response.model_name == "gpt-test"
    assert response.finish_reason == "stop"
    assert client.last_url == "https://llm.example.test/v1/chat/completions"
    assert client.last_headers == {
        "Authorization": "Bearer secret-key",
        "Content-Type": "application/json",
    }
    assert client.last_timeout == 8.0
    assert client.last_payload == {
        "model": "gpt-test",
        "messages": [{"role": "user", "content": "Analyse le fichier."}],
        "temperature": 0.0,
        "max_tokens": 300,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "profile_sheet",
                    "description": "Profile une feuille.",
                    "parameters": {
                        "type": "object",
                        "required": ["file_path", "sheet_name"],
                        "properties": {
                            "file_path": {"type": "string"},
                            "sheet_name": {"type": "string"},
                        },
                    },
                },
            },
        ],
    }


def test_openai_compatible_provider_uses_gpt5_chat_parameters() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(
            status_code=200,
            payload={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "Analyse disponible."},
                    },
                ],
            },
        ),
    )
    provider = OpenAICompatibleChatModelProvider(
        provider_name="openai-compatible",
        model_name="gpt-5-mini",
        api_key="secret-key",
        base_url="https://api.openai.com/v1",
        http_client=client,
    )

    provider.generate(_request())

    assert client.last_payload is not None
    assert client.last_payload["max_completion_tokens"] == 300
    assert "max_tokens" not in client.last_payload
    assert "temperature" not in client.last_payload


def test_openai_compatible_provider_parses_tool_calls() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(
            status_code=200,
            payload={
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "function": {
                                        "name": "profile_sheet",
                                        "arguments": json.dumps(
                                            {
                                                "file_path": "grand_livre.xlsx",
                                                "sheet_name": "Grand Livre",
                                            },
                                        ),
                                    },
                                },
                            ],
                        },
                    },
                ],
            },
        ),
    )
    provider = OpenAICompatibleChatModelProvider(
        provider_name="openai-compatible",
        model_name="gpt-test",
        api_key="secret-key",
        base_url="https://llm.example.test/v1",
        http_client=client,
    )

    response = provider.generate(_request())

    assert response.text == ""
    assert response.tool_calls == (
        ToolCall(
            name="profile_sheet",
            arguments={
                "file_path": "grand_livre.xlsx",
                "sheet_name": "Grand Livre",
            },
        ),
    )


def test_openai_compatible_provider_rejects_invalid_tool_arguments_json() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(
            status_code=200,
            payload={
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "function": {
                                        "name": "profile_sheet",
                                        "arguments": "{invalid-json",
                                    },
                                },
                            ],
                        },
                    },
                ],
            },
        ),
    )
    provider = OpenAICompatibleChatModelProvider(
        provider_name="openai-compatible",
        model_name="gpt-test",
        api_key="secret-key",
        base_url="https://llm.example.test/v1",
        http_client=client,
    )

    with pytest.raises(ModelProviderError, match="invalid tool arguments"):
        provider.generate(_request())


def test_openai_compatible_provider_sanitizes_http_errors() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(
            status_code=401,
            payload={"error": {"message": "secret provider message"}},
        ),
    )
    provider = OpenAICompatibleChatModelProvider(
        provider_name="openai-compatible",
        model_name="gpt-test",
        api_key="secret-key",
        base_url="https://llm.example.test/v1",
        http_client=client,
    )

    with pytest.raises(ModelProviderError, match="provider request failed: 401") as exc:
        provider.generate(_request())

    assert "secret provider message" not in str(exc.value)
    assert "secret-key" not in str(exc.value)


def _request() -> ModelRequest:
    return ModelRequest(
        messages=(ModelMessage(role="user", content="Analyse le fichier."),),
        allowed_tools=("profile_sheet",),
        temperature=0.0,
        max_output_tokens=300,
        timeout_seconds=8.0,
        tool_definitions=(
            ModelToolDefinition(
                name="profile_sheet",
                description="Profile une feuille.",
                input_schema={
                    "type": "object",
                    "required": ["file_path", "sheet_name"],
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                    },
                },
            ),
        ),
    )


class FakeHttpClient:
    def __init__(self, response: "FakeHttpResponse") -> None:
        self._response = response
        self.last_url: str | None = None
        self.last_payload: dict[str, Any] | None = None
        self.last_headers: dict[str, str] | None = None
        self.last_timeout: float | None = None

    def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> "FakeHttpResponse":
        self.last_url = url
        self.last_payload = json
        self.last_headers = headers
        self.last_timeout = timeout
        return self._response


class FakeHttpResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload
