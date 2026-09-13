"""
Tool Registry Module.

Manages registration and execution of tools that the AI assistant
can call during conversations. Implements the function calling pattern.
"""

import asyncio
import inspect
import logging
from typing import Any, Callable

from ..llm.provider import ToolDefinition

logger = logging.getLogger(__name__)


def validate_arguments(definition, arguments):
    """Validate the flat JSON schemas used by this project's tools."""
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
        if props[key].get("type") == "string" and (not isinstance(value, str) or not value.strip()):
            return f"Argument {key} must be a nonempty string"
    return None


class ToolRegistry:
    """
    Registry for AI assistant tools/functions.

    Tools are registered with their definitions (name, description, parameters)
    and executor functions. The registry provides a centralized way to:
    - Register new tools
    - Get tool definitions for LLM function calling
    - Execute tool calls and return results
    """

    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        executor: Callable,
    ):
        """Register a new tool."""
        self._tools[name] = {
            "definition": ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
            ),
            "executor": executor,
        }
        logger.info(f"Registered tool: {name}")

    def get_definitions(self) -> list[ToolDefinition]:
        """Get all tool definitions for LLM function calling."""
        return [tool["definition"] for tool in self._tools.values()]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name with the given arguments."""
        if tool_name not in self._tools:
            error_msg = f"Unknown tool: {tool_name}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

        invalid = validate_arguments(self._tools[tool_name]["definition"], arguments)
        if invalid:
            return f"Error: {invalid}"
        try:
            executor = self._tools[tool_name]["executor"]
            result = await executor(**arguments) if inspect.iscoroutinefunction(executor) else await asyncio.to_thread(executor, **arguments)
            logger.info(f"Executed tool '{tool_name}' successfully")
            return str(result)
        except Exception as e:
            error_msg = f"Tool '{tool_name}' failed: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())


# Global tool registry instance
tool_registry = ToolRegistry()
