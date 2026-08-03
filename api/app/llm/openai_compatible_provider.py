import json
from typing import Any, Protocol

import httpx

from app.llm.domain import (
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ToolCall,
)


class HttpResponse(Protocol):
    status_code: int

    def json(self) -> dict[str, Any]:
        pass


class HttpClient(Protocol):
    def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> HttpResponse:
        pass


class OpenAICompatibleChatModelProvider:
    provider_name: str

    def __init__(
        self,
        provider_name: str,
        model_name: str,
        api_key: str,
        base_url: str,
        http_client: HttpClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.provider_name = provider_name
        self.model_name = model_name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client or httpx.Client()

    def generate(self, request: ModelRequest) -> ModelResponse:
        try:
            response = self._http_client.post(
                url=f"{self._base_url}/chat/completions",
                json=_to_payload(self.model_name, request),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
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
            provider_name=self.provider_name,
            model_name=self.model_name,
            payload=response.json(),
        )


def _to_payload(model_name: str, request: ModelRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_name,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ],
    }
    if _uses_gpt5_chat_parameters(model_name):
        payload["max_completion_tokens"] = request.max_output_tokens
    else:
        payload["temperature"] = request.temperature
        payload["max_tokens"] = request.max_output_tokens
    tools = [
        {
            "type": "function",
            "function": {
                "name": definition.name,
                "description": definition.description,
                "parameters": definition.input_schema,
            },
        }
        for definition in request.tool_definitions
        if definition.name in request.allowed_tools
    ]
    if tools:
        payload["tools"] = tools
    return payload


def _uses_gpt5_chat_parameters(model_name: str) -> bool:
    return model_name.casefold().startswith("gpt-5")


def _parse_response(
    provider_name: str,
    model_name: str,
    payload: dict[str, Any],
) -> ModelResponse:
    try:
        choice = payload["choices"][0]
        message = choice["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelProviderError("invalid provider response") from exc

    return ModelResponse(
        text=_content_to_text(message.get("content")),
        provider_name=provider_name,
        model_name=model_name,
        finish_reason=str(choice.get("finish_reason", "unknown")),
        tool_calls=_parse_tool_calls(message),
    )


def _content_to_text(content: object) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def _parse_tool_calls(message: dict[str, Any]) -> tuple[ToolCall, ...]:
    tool_calls: list[ToolCall] = []
    for raw_tool_call in message.get("tool_calls") or ():
        try:
            raw_function = raw_tool_call["function"]
            name = str(raw_function["name"])
            arguments = json.loads(str(raw_function.get("arguments", "{}")))
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ModelProviderError("invalid tool arguments") from exc
        if not isinstance(arguments, dict):
            raise ModelProviderError("invalid tool arguments")
        tool_calls.append(ToolCall(name=name, arguments=arguments))
    return tuple(tool_calls)
