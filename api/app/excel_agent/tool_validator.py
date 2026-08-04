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
        if not _matches_declared_type(argument_value, expected_definition):
            raise InvalidToolArgumentsError(
                f"argument has an invalid type for {tool_name}: {argument_name}",
            )
        _validate_numeric_bounds(
            tool_name,
            argument_name,
            argument_value,
            expected_definition,
        )
        _validate_enum(tool_name, argument_name, argument_value, expected_definition)


def _matches_declared_type(value: object, definition: object) -> bool:
    if not isinstance(definition, dict):
        return False
    declared = definition.get("type")
    types = (declared,) if isinstance(declared, str) else tuple(declared or ())
    return any(_matches_type(value, type_name) for type_name in types)


def _matches_type(value: object, type_name: object) -> bool:
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    return type_name == "null" and value is None


def _validate_numeric_bounds(
    tool_name: str,
    argument_name: str,
    value: object,
    definition: object,
) -> None:
    if not isinstance(definition, dict) or not isinstance(value, int | float):
        return
    if isinstance(value, bool):
        return
    minimum = definition.get("minimum")
    maximum = definition.get("maximum")
    if isinstance(minimum, int | float) and value < minimum:
        raise InvalidToolArgumentsError(
            f"argument is below minimum for {tool_name}: {argument_name}"
        )
    if isinstance(maximum, int | float) and value > maximum:
        raise InvalidToolArgumentsError(
            f"argument exceeds maximum for {tool_name}: {argument_name}"
        )


def _validate_enum(
    tool_name: str,
    argument_name: str,
    value: object,
    definition: object,
) -> None:
    if not isinstance(definition, dict):
        return
    allowed = definition.get("enum")
    if isinstance(allowed, list) and value not in allowed:
        raise InvalidToolArgumentsError(
            f"argument is outside enum for {tool_name}: {argument_name}"
        )
