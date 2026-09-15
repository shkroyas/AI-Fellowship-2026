"""Tool Registry for the agentic loop."""
import asyncio
import inspect
import logging
from typing import Any, Callable
from ..llm.provider import ToolDefinition

logger = logging.getLogger(__name__)


def validate_arguments(definition, arguments):
    if definition is None:
        return "Unknown tool"
    if not isinstance(arguments, dict):
        return "Arguments must be an object"
    schema = definition.parameters
    props = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in arguments:
            return f"Missing argument: {key}"
    for key, value in arguments.items():
        if key not in props:
            return f"Unexpected argument: {key}"
    return None


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: dict[str, Any], executor: Callable):
        self._tools[name] = {"definition": ToolDefinition(name=name, description=description, parameters=parameters), "executor": executor}

    def get_definitions(self) -> list[ToolDefinition]:
        return [tool["definition"] for tool in self._tools.values()]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if tool_name not in self._tools:
            return f"Error: Unknown tool: {tool_name}"
        invalid = validate_arguments(self._tools[tool_name]["definition"], arguments)
        if invalid:
            return f"Error: {invalid}"
        try:
            executor = self._tools[tool_name]["executor"]
            result = await executor(**arguments) if inspect.iscoroutinefunction(executor) else await asyncio.to_thread(executor, **arguments)
            return str(result)
        except Exception as e:
            return f"Error: Tool '{tool_name}' failed: {e}"

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


tool_registry = ToolRegistry()
