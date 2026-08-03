from typing import Any

import pytest

from app.llm.domain import (
    ModelMessage,
    ModelProviderError,
    ModelRequest,
    ModelToolDefinition,
    ToolCall,
)
from app.llm.gemini_provider import GeminiModelProvider


def test_gemini_provider_sends_generate_content_payload() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(
            status_code=200,
            payload={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {
                            "parts": [
                                {"text": "Analyse disponible."},
                            ],
                        },
                    },
                ],
                "modelVersion": "gemini-test-version",
            },
        ),
    )
    provider = GeminiModelProvider(
        model_name="gemini-test",
        api_key="api-key",
        base_url="https://gemini.example.test/v1beta",
        http_client=client,
    )

    response = provider.generate(_request())

    assert response.text == "Analyse disponible."
    assert response.provider_name == "gemini"
    assert response.model_name == "gemini-test-version"
    assert response.finish_reason == "STOP"
    assert response.tool_calls == ()
    assert (
        client.last_url
        == "https://gemini.example.test/v1beta/models/gemini-test:generateContent"
    )
    assert client.last_headers == {
        "Content-Type": "application/json",
        "x-goog-api-key": "api-key",
    }
    assert client.last_timeout == 8.0
    assert client.last_payload == {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "[system]\nRespecte les tools autorises.\n\n"
                            "[user]\nAnalyse le fichier."
                        ),
                    },
                ],
            },
        ],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 300,
        },
    }


def test_gemini_provider_ignores_thought_signatures() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(
            status_code=200,
            payload={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {
                            "parts": [
                                {
                                    "text": "Reponse utile.",
                                    "thoughtSignature": "hidden",
                                },
                            ],
                        },
                    },
                ],
            },
        ),
    )
    provider = GeminiModelProvider(
        model_name="gemini-test",
        api_key="api-key",
        base_url="https://gemini.example.test/v1beta",
        http_client=client,
    )

    response = provider.generate(_request())

    assert response.text == "Reponse utile."
    assert "hidden" not in response.text


def test_gemini_provider_sends_and_parses_function_calls() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(
            status_code=200,
            payload={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {
                            "parts": [
                                {
                                    "functionCall": {
                                        "name": "profile_sheet",
                                        "args": {
                                            "file_path": "grand_livre.xlsx",
                                            "sheet_name": "Grand Livre",
                                        },
                                    },
                                },
                            ],
                        },
                    },
                ],
            },
        ),
    )
    provider = GeminiModelProvider(
        model_name="gemini-test",
        api_key="api-key",
        base_url="https://gemini.example.test/v1beta",
        http_client=client,
    )

    response = provider.generate(_request_with_tool())

    assert client.last_payload is not None
    assert client.last_payload["tools"] == [
        {
            "functionDeclarations": [
                {
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
            ],
        },
    ]
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


def test_gemini_provider_sanitizes_http_errors() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(
            status_code=403,
            payload={"error": {"message": "provider leaked secret detail"}},
        ),
    )
    provider = GeminiModelProvider(
        model_name="gemini-test",
        api_key="api-key",
        base_url="https://gemini.example.test/v1beta",
        http_client=client,
    )

    with pytest.raises(ModelProviderError, match="provider request failed: 403") as exc:
        provider.generate(_request())

    assert "provider leaked secret detail" not in str(exc.value)
    assert "api-key" not in str(exc.value)


def test_gemini_provider_rejects_invalid_response() -> None:
    client = FakeHttpClient(
        response=FakeHttpResponse(status_code=200, payload={"candidates": []}),
    )
    provider = GeminiModelProvider(
        model_name="gemini-test",
        api_key="api-key",
        base_url="https://gemini.example.test/v1beta",
        http_client=client,
    )

    with pytest.raises(ModelProviderError, match="invalid provider response"):
        provider.generate(_request())


def _request() -> ModelRequest:
    return ModelRequest(
        messages=(
            ModelMessage(role="system", content="Respecte les tools autorises."),
            ModelMessage(role="user", content="Analyse le fichier."),
        ),
        allowed_tools=(),
        temperature=0.0,
        max_output_tokens=300,
        timeout_seconds=8.0,
    )


def _request_with_tool() -> ModelRequest:
    return ModelRequest(
        messages=(ModelMessage(role="user", content="Profile ce fichier."),),
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
