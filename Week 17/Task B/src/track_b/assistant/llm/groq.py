"""Async Groq REST provider with multi-key rotation and exponential backoff."""
import asyncio
import json
import logging
import re
import time
import uuid
from collections import deque
from typing import Optional
import httpx
from .provider import ChatMessage, LLMProvider, LLMResponse, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class GroqRequestError(RuntimeError):
    def __init__(self, status):
        self.status_code = status
        if status == 429:
            super().__init__("Groq HTTP 429; rate limit or quota exhausted")
        else:
            super().__init__(f"Groq HTTP {status}")


class GroqProvider(LLMProvider):
    BACKOFF_SEQUENCE = [2, 4, 8]

    def __init__(self, model="openai/gpt-oss-20b", temperature=0.7,
                 top_p=0.9, max_tokens=2048, api_keys=None, active_key=1,
                 tokens_per_minute=8000, clock=None, sleep=None):
        super().__init__(model, temperature, top_p, max_tokens)
        if api_keys is None:
            raise ValueError("At least one Groq API key is required")
        keys = [k.strip() for k in api_keys if k and k.strip()]
        if not keys:
            raise ValueError("No non-empty Groq API keys provided")
        self._keys = tuple(keys)
        self._active = active_key - 1
        self._cooldown_until = 0.0
        self._lock = asyncio.Lock()
        self._base_url = "https://api.groq.com/openai/v1/chat/completions"
        self._budget = tokens_per_minute
        self._reservations = deque()
        self._clock = clock or time.monotonic
        self._sleep = sleep or asyncio.sleep

    def _parse_retry_after(self, retry_after_str, rate_limit_reset_str):
        delay = None
        if retry_after_str:
            try:
                delay = max(1, float(retry_after_str))
            except ValueError:
                m = re.match(r"(?:(\d+)m)?(\d+(?:\.\d+)?)s?", retry_after_str)
                if m:
                    minutes = int(m.group(1) or 0)
                    seconds = float(m.group(2))
                    delay = max(1, minutes * 60 + seconds)
        if delay is None and rate_limit_reset_str:
            try:
                reset_val = float(rate_limit_reset_str)
                if reset_val > 1000000:
                    delay = max(1, reset_val - time.time())
                else:
                    delay = max(1, reset_val)
            except ValueError:
                pass
        return delay

    async def _pace(self, payload, actual_tokens=0):
        cost = actual_tokens if actual_tokens > 0 else (len(json.dumps(payload).encode("utf-8")) + 2) // 3 + self.max_tokens + 100
        while True:
            now = self._clock()
            while self._reservations and self._reservations[0][0] <= now - 61:
                self._reservations.popleft()
            reserved = sum(c for _, c in self._reservations)
            if reserved + cost <= self._budget:
                self._reservations.append((now, cost))
                return now
            delay = min(30.0, max(0.01, self._reservations[0][0] + 61 - now)) if self._reservations else 1.0
            await self._sleep(delay)

    def _build_payload(self, messages, tools, structured_output):
        api_messages = []
        for msg in messages:
            m = {"role": msg.role, "content": msg.content}
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls and msg.role == "assistant":
                m["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                    for tc in msg.tool_calls
                ]
            api_messages.append(m)

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        if self.model in ("openai/gpt-oss-20b", "openai/gpt-oss-120b"):
            payload["reasoning_effort"] = "low"
        if tools:
            payload["tools"] = [
                {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
                for t in tools
            ]
            payload["tool_choice"] = "auto"
        if structured_output:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _parse_response(self, data):
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        finish_reason = choice.get("finish_reason", "")
        tool_calls = []
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(id=tc.get("id", str(uuid.uuid4())), name=func.get("name", ""), arguments=args))
        usage_data = data.get("usage", {})
        usage = {"prompt_tokens": usage_data.get("prompt_tokens", 0), "completion_tokens": usage_data.get("completion_tokens", 0)}
        response = LLMResponse(content=content, tool_calls=tool_calls, model=self.model, usage=usage)
        response.finish_reason = finish_reason
        return response

    async def chat(self, messages, tools=None, structured_output=None):
        payload = self._build_payload(messages, tools, structured_output)
        async with self._lock:
            async with httpx.AsyncClient(timeout=60) as client:
                num_keys = len(self._keys)
                for offset in range(num_keys):
                    slot = (self._active + offset) % num_keys
                    backoff = self.BACKOFF_SEQUENCE[min(max(0, offset - 1), len(self.BACKOFF_SEQUENCE) - 1)]
                    if offset > 0:
                        await self._sleep(backoff)

                    try:
                        reservation_key = await self._pace(payload)
                        response = await client.post(self._base_url, json=payload, headers={
                            "Authorization": f"Bearer {self._keys[slot]}", "Content-Type": "application/json"})
                    except httpx.TransportError:
                        if offset + 1 < num_keys:
                            continue
                        raise GroqRequestError(0) from None

                    if response.status_code == 429:
                        retry_after = response.headers.get("retry-after", "")
                        rate_limit_reset = response.headers.get("x-ratelimit-reset-tokens", "")
                        delay = self._parse_retry_after(retry_after, rate_limit_reset) or 60
                        self._cooldown_until = self._clock() + delay
                        if delay > 65:
                            raise GroqRequestError(429)
                        await self._sleep(delay)
                        continue

                    if response.status_code == 400:
                        try:
                            err_body = response.json()
                            err_code = err_body.get("error", {}).get("code")
                        except (ValueError, AttributeError):
                            err_code = None
                        if payload.get("tools") and err_code == "tool_use_failed":
                            text_payload = dict(payload)
                            text_payload.pop("tools", None)
                            text_payload.pop("tool_choice", None)
                            text_payload["messages"] = payload["messages"] + [{"role": "system", "content":
                                "Native tool serialization failed. Return only ACTION: tool_name followed by JSON arguments, "
                                "ANSWER: final answer, or CLARIFY: question."}]
                            response = await client.post(self._base_url, json=text_payload, headers={
                                "Authorization": f"Bearer {self._keys[slot]}", "Content-Type": "application/json"})
                        elif payload.get("tools"):
                            text_payload = {k: v for k, v in payload.items() if k not in ("tools", "tool_choice")}
                            response = await client.post(self._base_url, json=text_payload, headers={
                                "Authorization": f"Bearer {self._keys[slot]}", "Content-Type": "application/json"})
                        else:
                            raise GroqRequestError(400)

                    if response.status_code in (500, 502, 503, 504):
                        if offset + 1 < num_keys:
                            continue
                        raise GroqRequestError(response.status_code)

                    if response.status_code in (401, 403):
                        raise GroqRequestError(response.status_code)

                    if response.is_error:
                        raise GroqRequestError(response.status_code)

                    data = response.json()
                    result = self._parse_response(data)

                    total_tokens = result.usage.get("prompt_tokens", 0) + result.usage.get("completion_tokens", 0)
                    if total_tokens > 0:
                        self._reservations.append((self._clock(), total_tokens))

                    if getattr(result, "finish_reason", "") == "length":
                        if result.tool_calls:
                            result.tool_calls = []
                            result.content = (result.content or "").strip()
                            if not result.content:
                                result.content = "Verification incomplete: the model's response was truncated."
                        elif result.content:
                            result.content = result.content.strip() + "\n\n[Note: response was truncated by token limit]"

                    if result.content and not result.tool_calls and tools:
                        if any(t.name == "answer" for t in tools):
                            if not result.content.lstrip().upper().startswith(("ACTION:", "ANSWER:", "CLARIFY:")):
                                result.tool_calls = [ToolCall(id=str(uuid.uuid4()), name="answer", arguments={"answer": result.content})]

                    return result

    async def health_check(self):
        try:
            await self.chat([ChatMessage(role="user", content="Say ok")])
            return True
        except Exception:
            return False
