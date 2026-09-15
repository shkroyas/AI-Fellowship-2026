"""LLM Provider abstraction layer."""
import json
import logging
from functools import lru_cache
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: system, user, assistant, or tool")
    content: str = Field(..., description="Message content")
    tool_call_id: Optional[str] = Field(default=None)
    tool_calls: Optional[list[ToolCall]] = Field(default=None)


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    raw_response: Optional[Any] = Field(default=None, exclude=True)
    usage: dict[str, int] = Field(default_factory=dict)
    model: str = ""
    finish_reason: str = ""


class LLMProvider(ABC):
    def __init__(self, model: str, temperature: float = 0.7, top_p: float = 0.9, max_tokens: int = 2048):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens

    @abstractmethod
    async def chat(self, messages: list[ChatMessage], tools=None, structured_output=None) -> LLMResponse:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    def _validate_json_output(self, content: str) -> dict:
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM did not produce valid JSON: {e}")


def get_provider(provider_name: str = None) -> LLMProvider:
    from ..config import settings
    return _create_provider(provider_name or settings.llm_provider)


@lru_cache(maxsize=3)
def _create_provider(provider_name: str) -> LLMProvider:
    from ..config import settings
    provider_name = provider_name or settings.llm_provider

    if provider_name == "groq":
        from .groq import GroqProvider
        return GroqProvider(
            model=settings.groq_model,
            api_keys=settings.groq_keys(),
            active_key=settings.groq_active_key,
            tokens_per_minute=settings.groq_tokens_per_minute,
            temperature=settings.temperature,
            top_p=settings.top_p,
            max_tokens=settings.max_tokens,
        )
    elif provider_name == "openrouter":
        from .openrouter import OpenRouterProvider
        return OpenRouterProvider(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            temperature=settings.temperature,
            top_p=settings.top_p,
            max_tokens=settings.max_tokens,
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
