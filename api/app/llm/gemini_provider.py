from typing import Any

import httpx

from app.llm.domain import ModelProviderError, ModelRequest, ModelResponse, ToolCall
from app.llm.openai_compatible_provider import HttpClient


class GeminiModelProvider:
    provider_name = "gemini"

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str,
        http_client: HttpClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.model_name = model_name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client or httpx.Client()

    def generate(self, request: ModelRequest) -> ModelResponse:
        try:
            response = self._http_client.post(
                url=(
                    f"{self._base_url}/models/{self.model_name}:generateContent"
                ),
                json=_to_payload(request),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self._api_key,
                },
                timeout=request.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ModelProviderError("provider request timed out") from exc
        except httpx.HTTPError as exc:
            raise ModelProviderError("provider request failed") from exc

        if response.status_code >= 400:
            raise ModelProviderError(
                f"provider request failed: {response.status_code}",
            )
        return _parse_response(
            requested_model_name=self.model_name,
            payload=response.json(),
        )


def _to_payload(request: ModelRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": _messages_to_prompt(request)}],
            },
        ],
        "generationConfig": {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_output_tokens,
        },
    }
    function_declarations = [
        {
            "name": definition.name,
            "description": definition.description,
            "parameters": definition.input_schema,
        }
        for definition in request.tool_definitions
        if definition.name in request.allowed_tools
    ]
    if function_declarations:
        payload["tools"] = [
            {"functionDeclarations": function_declarations},
        ]
    return payload


def _messages_to_prompt(request: ModelRequest) -> str:
    return "\n\n".join(
        f"[{message.role}]\n{message.content}" for message in request.messages
    )


def _parse_response(
    requested_model_name: str,
    payload: dict[str, Any],
) -> ModelResponse:
    try:
        candidate = payload["candidates"][0]
        raw_parts = candidate["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelProviderError("invalid provider response") from exc

    if not isinstance(raw_parts, list):
        raise ModelProviderError("invalid provider response")

    text_parts = [
        raw_part["text"]
        for raw_part in raw_parts
        if isinstance(raw_part, dict) and isinstance(raw_part.get("text"), str)
    ]
    tool_calls = _parse_tool_calls(raw_parts)
    if not text_parts and not tool_calls:
        raise ModelProviderError("invalid provider response")

    return ModelResponse(
        text="".join(text_parts),
        provider_name="gemini",
        model_name=str(payload.get("modelVersion") or requested_model_name),
        finish_reason=str(candidate.get("finishReason", "unknown")),
        tool_calls=tool_calls,
    )


def _parse_tool_calls(raw_parts: list[object]) -> tuple[ToolCall, ...]:
    tool_calls: list[ToolCall] = []
    for raw_part in raw_parts:
        if not isinstance(raw_part, dict):
            continue
        raw_function_call = raw_part.get("functionCall")
        if raw_function_call is None:
            continue
        if not isinstance(raw_function_call, dict):
            raise ModelProviderError("invalid tool arguments")
        raw_arguments = raw_function_call.get("args") or {}
        if not isinstance(raw_arguments, dict):
            raise ModelProviderError("invalid tool arguments")
        try:
            name = str(raw_function_call["name"])
        except KeyError as exc:
            raise ModelProviderError("invalid tool arguments") from exc
        tool_calls.append(ToolCall(name=name, arguments=raw_arguments))
    return tuple(tool_calls)
