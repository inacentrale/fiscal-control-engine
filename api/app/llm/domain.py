from dataclasses import dataclass
from typing import Any, Protocol


class ModelProviderError(RuntimeError):
    pass


class ModelTimeoutError(ModelProviderError):
    pass


@dataclass(frozen=True)
class ModelMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class ModelToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ModelRequest:
    messages: tuple[ModelMessage, ...]
    allowed_tools: tuple[str, ...]
    temperature: float
    max_output_tokens: int
    timeout_seconds: float
    tool_definitions: tuple[ModelToolDefinition, ...] = ()


@dataclass(frozen=True)
class ModelResponse:
    text: str
    provider_name: str
    model_name: str
    finish_reason: str
    tool_calls: tuple[ToolCall, ...]


class ModelProvider(Protocol):
    provider_name: str

    def generate(self, request: ModelRequest) -> ModelResponse:
        pass
