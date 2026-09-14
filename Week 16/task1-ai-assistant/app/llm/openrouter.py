"""Async OpenRouter REST provider for free-tier fallback.

Uses the OpenAI-compatible /chat/completions endpoint. Serves as fallback
when the primary Groq provider is exhausted or unavailable.
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Optional

import httpx

from .provider import ChatMessage, LLMProvider, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class OpenRouterRequestError(RuntimeError):
    """Sanitized provider error."""
    def __init__(self, status):
        self.status_code = status
        super().__init__(f"OpenRouter HTTP {status}")


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider using free-tier models.

    Uses OpenAI-compatible format with a single API key.
    Free-tier models have rate limits; pacing is enforced between requests.
    """

    def __init__(self, model="meta-llama/llama-3.1-8b-instruct:free",
                 api_key=None, temperature=0.7, top_p=0.9, max_tokens=2048,
                 transport=None, clock=None, sleep=None):
        super().__init__(model, temperature, top_p, max_tokens)
        if not api_key:
            raise ValueError("OpenRouter API key is required")
        self._api_key = api_key.strip()
        self._transport = transport
        self._base_url = "https://openrouter.ai/api/v1/chat/completions"
        self._clock = clock or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._last_request_time = 0.0
        self._min_interval = 30.0  # Minimum 30s between requests for free tier
        self._lock = asyncio.Lock()

    def _build_payload(self, messages, tools, structured_output):
        api_messages = []
        for msg in messages:
            m = {"role": msg.role, "content": msg.content}
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            api_messages.append(m)

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }

        if tools:
            payload["tools"] = [
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
            payload["tool_choice"] = "auto"
            payload["provider"] = {"require_parameters": True}

        if structured_output:
            payload["response_format"] = {"type": "json_object"}

        return payload

    def _parse_response(self, data):
        if data.get("error") or not data.get("choices"):
            raise OpenRouterRequestError(502)
        choice = data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        tool_calls = []

        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.get("id", str(uuid.uuid4())),
                    name=func.get("name", ""),
                    arguments=args,
                ))

        usage_data = data.get("usage", {})
        usage = {
            "prompt_tokens": usage_data.get("prompt_tokens", 0),
            "completion_tokens": usage_data.get("completion_tokens", 0),
        }

        return LLMResponse(content=content, tool_calls=tool_calls,
                           model=self.model, usage=usage)

    async def chat(self, messages, tools=None, structured_output=None):
        payload = self._build_payload(messages, tools, structured_output)

        async with self._lock:
            # Pace requests to avoid429
            now = self._clock()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                wait_time = self._min_interval - elapsed
                logger.info("OpenRouter pacing: waiting %.1fs", wait_time)
                await self._sleep(wait_time)

            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15), transport=self._transport) as client:
                    response = await client.post(
                        self._base_url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://ai-assistant.local",
                            "X-Title": "AI Assistant",
                        },
                    )
                    self._last_request_time = self._clock()

                    if response.status_code == 429:
                        # Read retry-after header
                        retry_after = response.headers.get("retry-after", "30")
                        try:
                            delay = max(10, float(retry_after))
                        except ValueError:
                            delay = 30
                        logger.warning("OpenRouter429: cooling down %.1fs", delay)
                        await self._sleep(delay)
                        self._last_request_time = self._clock()
                        raise OpenRouterRequestError(429)

                    if response.status_code in (500, 502, 503, 504):
                        raise OpenRouterRequestError(response.status_code)

                    if response.status_code == 400:
                        # Some models don't support tool calling - retry without tools
                        logger.warning("OpenRouter HTTP400: retrying without tools")
                        text_payload = {k: v for k, v in payload.items() if k not in ("tools", "tool_choice", "provider")}
                        async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15), transport=self._transport) as retry_client:
                            retry_response = await retry_client.post(
                                self._base_url, json=text_payload,
                                headers={"Authorization": f"Bearer {self._api_key}",
                                         "Content-Type": "application/json",
                                         "HTTP-Referer": "https://ai-assistant.local",
                                         "X-Title": "AI Assistant"})
                            if retry_response.is_error:
                                raise OpenRouterRequestError(retry_response.status_code)
                            data = retry_response.json()
                            result = self._parse_response(data)
                            if result.content and not result.tool_calls and tools:
                                if any(t.name == "answer" for t in tools):
                                    result.tool_calls = [ToolCall(id=str(uuid.uuid4()), name="answer",
                                                                 arguments={"answer": result.content})]
                            return result

                    if response.is_error:
                        raise OpenRouterRequestError(response.status_code)

                    data = response.json()
                    result = self._parse_response(data)

                    if result.content and not result.tool_calls and tools:
                        if any(t.name == "answer" for t in tools):
                            if not result.content.lstrip().upper().startswith(("ACTION:", "ANSWER:", "CLARIFY:")):
                                result.tool_calls = [ToolCall(
                                    id=str(uuid.uuid4()),
                                    name="answer",
                                    arguments={"answer": result.content},
                                )]

                    if structured_output and result.content:
                        self._validate_json_output(result.content)

                    return result

            except httpx.TransportError:
                raise OpenRouterRequestError(0) from None

    async def health_check(self):
        try:
            await self.chat([ChatMessage(role="user", content="Say ok")])
            return True
        except Exception:
            return False
