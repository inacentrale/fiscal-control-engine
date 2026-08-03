from types import MappingProxyType
from typing import Any

from app.excel_agent.domain import ValidatedToolCall
from app.excel_agent.tool_registry import AgentToolDefinition, AgentToolRegistry
from app.llm.domain import ToolCall


class ToolCallValidationError(ValueError):
    pass


class UnknownToolError(ToolCallValidationError):
    pass


class InvalidToolArgumentsError(ToolCallValidationError):
    pass


class ToolCallValidator:
    def __init__(self, registry: AgentToolRegistry) -> None:
        self._registry = registry

    def get_tool_definition(self, tool_name: str) -> AgentToolDefinition | None:
        return self._registry.get(tool_name)

    def validate(self, tool_call: ToolCall) -> ValidatedToolCall:
        definition = self._registry.get(tool_call.name)
        if definition is None:
            raise UnknownToolError(f"unknown tool: {tool_call.name}")
        _validate_arguments(
            tool_name=tool_call.name,
            arguments=tool_call.arguments,
            input_schema=definition.input_schema,
        )
        return ValidatedToolCall(
            name=tool_call.name,
            arguments=MappingProxyType(dict(tool_call.arguments)),
        )


def _validate_arguments(
    tool_name: str,
    arguments: dict[str, object],
    input_schema: dict[str, Any],
) -> None:
    required_arguments = tuple(input_schema.get("required", ()))
    properties = input_schema.get("properties", {})
    if not isinstance(properties, dict):
        raise InvalidToolArgumentsError(f"invalid schema for tool: {tool_name}")

    for argument_name in required_arguments:
        if argument_name not in arguments:
            raise InvalidToolArgumentsError(
                f"missing required argument for {tool_name}: {argument_name}",
            )

    for argument_name, argument_value in arguments.items():
        expected_definition = properties.get(argument_name)
        if expected_definition is None:
            raise InvalidToolArgumentsError(
                f"unexpected argument for {tool_name}: {argument_name}",
            )
        if _expects_string(expected_definition) and not isinstance(
            argument_value,
            str,
        ):
            raise InvalidToolArgumentsError(
                f"argument must be a string for {tool_name}: {argument_name}",
            )


def _expects_string(property_definition: object) -> bool:
    return (
        isinstance(property_definition, dict)
        and property_definition.get("type") == "string"
    )
