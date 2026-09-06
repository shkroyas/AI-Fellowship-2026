"""
LLM Provider Abstraction Layer.

Defines the base interface for all LLM providers and a factory function
to instantiate the correct provider based on configuration.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Represents a single message in a conversation."""
    role: str = Field(..., description="Role: system, user, assistant, or tool")
    content: str = Field(..., description="Message content")
    tool_call_id: Optional[str] = Field(default=None, description="Tool call ID for tool responses")


class ToolDefinition(BaseModel):
    """Defines a tool that the LLM can call."""
    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    """Represents a tool call made by the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    raw_response: Optional[Any] = Field(default=None, exclude=True)
    usage: dict[str, int] = Field(default_factory=dict)
    model: str = ""


class StructuredOutputSchema(BaseModel):
    """Schema definition for structured JSON output."""
    name: str
    description: str
    schema_dict: dict[str, Any]


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, temperature: float = 0.7, top_p: float = 0.9, max_tokens: int = 2048):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[ToolDefinition]] = None,
        structured_output: Optional[StructuredOutputSchema] = None,
    ) -> LLMResponse:
        """Send a chat completion request to the LLM provider."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available."""
        ...

    def _validate_json_output(self, content: str) -> dict:
        """Validate and parse JSON from LLM output."""
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON output: {e}")
            raise ValueError(f"LLM did not produce valid JSON: {e}")


def get_provider(provider_name: str = None) -> LLMProvider:
    """Factory function to create the appropriate LLM provider.

    Args:
        provider_name: Name of the provider ('gemini', 'openai', 'local_vllm').
                       If None, uses the configured default.

    Returns:
        An instance of the appropriate LLMProvider subclass.
    """
    from ..config import settings

    provider_name = provider_name or settings.llm_provider

    if provider_name == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(
            model=settings.gemini_model,
            api_key=settings.google_api_key,
            temperature=settings.temperature,
            top_p=settings.top_p,
            max_tokens=settings.max_tokens,
        )
    elif provider_name == "openai":
        from .openai_client import OpenAIProvider
        return OpenAIProvider(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=settings.temperature,
            top_p=settings.top_p,
            max_tokens=settings.max_tokens,
        )
    elif provider_name == "local_vllm":
        from .local_vllm import LocalVLLMProvider
        return LocalVLLMProvider(
            model=settings.vllm_model,
            base_url=settings.vllm_base_url,
            temperature=settings.temperature,
            top_p=settings.top_p,
            max_tokens=settings.max_tokens,
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
