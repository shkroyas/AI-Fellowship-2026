"""
Local vLLM Provider.

Implements the LLMProvider interface for locally served models
via vLLM's OpenAI-compatible API endpoint.
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


class LocalVLLMProvider(LLMProvider):
    """
    Local vLLM provider.

    Connects to a locally running vLLM server that exposes an
    OpenAI-compatible API. This allows serving open-source models
    like Llama 3, Mistral, etc.

    Start vLLM server with:
        vllm serve mistralai/Mistral-7B-Instruct-v0.3 --port 8000
    """

    def __init__(
        self,
        model: str = "mistralai/Mistral-7B-Instruct-v0.3",
        base_url: str = "http://localhost:8000/v1",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
    ):
        super().__init__(model, temperature, top_p, max_tokens)
        self.base_url = base_url
        # vLLM uses an OpenAI-compatible API, so we use the OpenAI client
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="not-needed",  # vLLM doesn't require an API key locally
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[ToolDefinition]] = None,
        structured_output: Optional[StructuredOutputSchema] = None,
    ) -> LLMResponse:
        """Send a chat request to the local vLLM server."""
        try:
            # Build messages
            vllm_messages = []
            for msg in messages:
                m = {"role": msg.role, "content": msg.content}
                if msg.tool_call_id:
                    m["tool_call_id"] = msg.tool_call_id
                vllm_messages.append(m)

            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": vllm_messages,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
            }

            # vLLM supports tool calling for some models
            if tools:
                kwargs["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.parameters,
                        },
                    }
                    for t in tools
                ]
                kwargs["tool_choice"] = "auto"

            # For structured output, try guided decoding
            if structured_output:
                kwargs["response_format"] = {"type": "json_object"}
                # Add schema instruction
                schema_instruction = (
                    f"\n\nRespond ONLY with valid JSON matching this schema:\n"
                    f"{json.dumps(structured_output.schema_dict, indent=2)}"
                )
                if vllm_messages and vllm_messages[0]["role"] == "system":
                    vllm_messages[0]["content"] += schema_instruction
                else:
                    vllm_messages.insert(0, {
                        "role": "system",
                        "content": f"You are a helpful assistant. {schema_instruction}",
                    })

            response = await self.client.chat.completions.create(**kwargs)

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
            logger.error(f"vLLM API error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if the local vLLM server is running."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception as e:
            logger.warning(f"vLLM health check failed (server may not be running): {e}")
            return False
