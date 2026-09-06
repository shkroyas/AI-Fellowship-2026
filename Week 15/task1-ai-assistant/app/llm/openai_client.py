"""
OpenAI LLM Provider.

Implements the LLMProvider interface for OpenAI's API
with support for function calling and structured output.
"""

import json
import logging
from typing import Any, Optional

from openai import AsyncOpenAI

from .provider import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    StructuredOutputSchema,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
    ):
        super().__init__(model, temperature, top_p, max_tokens)
        if not api_key:
            raise ValueError("OpenAI API key is required")

        self.client = AsyncOpenAI(api_key=api_key)

    def _convert_tools_to_openai(self, tools: list[ToolDefinition]) -> list[dict]:
        """Convert our tool definitions to OpenAI's function format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[ToolDefinition]] = None,
        structured_output: Optional[StructuredOutputSchema] = None,
    ) -> LLMResponse:
        """Send a chat request to OpenAI."""
        try:
            # Build messages
            openai_messages = []
            for msg in messages:
                m = {"role": msg.role, "content": msg.content}
                if msg.tool_call_id:
                    m["tool_call_id"] = msg.tool_call_id
                openai_messages.append(m)

            # Build request kwargs
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": openai_messages,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
            }

            # Add tools if provided
            if tools:
                kwargs["tools"] = self._convert_tools_to_openai(tools)
                kwargs["tool_choice"] = "auto"

            # Add structured output format
            if structured_output:
                kwargs["response_format"] = {"type": "json_object"}
                # Append schema instruction to system message
                schema_instruction = (
                    f"\n\nYou MUST respond with a valid JSON object matching this schema:\n"
                    f"{json.dumps(structured_output.schema_dict, indent=2)}"
                )
                if openai_messages and openai_messages[0]["role"] == "system":
                    openai_messages[0]["content"] += schema_instruction
                else:
                    openai_messages.insert(0, {
                        "role": "system",
                        "content": f"Respond only with valid JSON. {schema_instruction}",
                    })

            response = await self.client.chat.completions.create(**kwargs)

            # Parse response
            choice = response.choices[0]
            content = choice.message.content or ""
            tool_calls = []

            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    ))

            # Validate structured output
            if structured_output and content:
                self._validate_json_output(content)

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                model=self.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
