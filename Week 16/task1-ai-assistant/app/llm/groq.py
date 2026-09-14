"""Async Groq REST provider with multi-key rotation and exponential backoff.

Uses the OpenAI-compatible /chat/completions endpoint. Keys are sent in
Authorization headers only. Quota (429) never triggers credential rotation;
exponential backoff (2s/4s/8s) is applied before each key rotation on
transient errors. 5xx errors trigger key rotation with backoff.
"""
import asyncio
import json
import logging
import time
import uuid
from collections import deque
from typing import Optional

import httpx

from .provider import ChatMessage, LLMProvider, LLMResponse, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class GroqRequestError(RuntimeError):
    """Sanitized provider error safe for reports (never contains raw keys)."""
    def __init__(self, status):
        self.status_code = status
        if status == 429:
            super().__init__("Groq HTTP 429; rate limit or quota exhausted")
        elif status in (500, 502, 503, 504):
            super().__init__(f"Groq HTTP {status}; transient server error")
        else:
            super().__init__(f"Groq HTTP {status}")


class GroqProvider(LLMProvider):
    """Groq API provider with multi-key rotation and exponential backoff.

    Rotation strategy:
    - On 429: enter cooldown (read retry-after or default 60s), do NOT rotate keys
    - On 5xx/transport: backoff (2s/4s/8s) then try next key
    - On 4xx auth: stop immediately, do not rotate
    - Keys are distinct credentials; rotation is operational failover, not quota evasion
    """

    BACKOFF_SEQUENCE = [2, 4, 8]  # seconds between rotations

    def __init__(self, model="llama-3.3-70b-versatile", temperature=0.7,
                 top_p=0.9, max_tokens=2048, api_keys=None, active_key=1,
                 api_key=None, transport=None, tokens_per_minute=6000,
                 max_rate_retries=2, max_rate_wait=65, clock=None, sleep=None):
        super().__init__(model, temperature, top_p, max_tokens)
        # Support single api_key for convenience (wraps as list)
        if api_keys is None and api_key:
            api_keys = [api_key]
        if not api_keys:
            raise ValueError("At least one Groq API key is required")
        keys = [k.strip() for k in api_keys if k and k.strip()]
        if not keys:
            raise ValueError("No non-empty Groq API keys provided")
        if len(keys) > 5:
            raise ValueError("At most five Groq keys are supported")
        if len(set(keys)) != len(keys):
            raise ValueError("Groq key slots must contain distinct credentials")
        if not 1 <= active_key <= len(keys):
            raise ValueError("GROQ_ACTIVE_KEY must select a configured key")
        self._keys = tuple(keys)
        self._active = active_key - 1
        self._cooldown_until = 0.0
        self._lock = asyncio.Lock()
        self._base_url = "https://api.groq.com/openai/v1/chat/completions"
        self._transport = transport
        self._budget = tokens_per_minute
        self._reservations = deque()
        self._clock = clock or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._max_rate_retries = max_rate_retries
        self._max_rate_wait = max_rate_wait

    async def _pace(self, payload, actual_tokens=0):
        """Token-aware pacing using actual usage when available, estimate otherwise.

        Enforces the token budget strictly but caps wait at 30s to avoid hanging.
        """
        if actual_tokens > 0:
            cost = actual_tokens
        else:
            # Estimate: input bytes / 3 + max output tokens + overhead
            cost = (len(json.dumps(payload).encode("utf-8")) + 2) // 3 + self.max_tokens + 100
        while True:
            now = self._clock()
            # Purge reservations older than 61 seconds
            while self._reservations and self._reservations[0][0] <= now - 61:
                self._reservations.popleft()
            if sum(c for _, c in self._reservations) + cost <= self._budget:
                self._reservations.append((now, cost))
                return
            # Wait for the oldest reservation to expire, capped at 30s
            delay = min(30.0, max(0.01, self._reservations[0][0] + 61 - now))
            logger.info("Groq pacing: waiting %.1fs (reserved=%d, cost=%d, budget=%d)",
                        delay, sum(c for _, c in self._reservations), cost, self._budget)
            await self._sleep(delay)

    def _record_usage(self, usage):
        """Record actual token usage for better future pacing."""
        total = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        if total > 0:
            now = self._clock()
            self._reservations.append((now, total))

    async def _post_with_rate_retry(self, client, payload, slot):
        for attempt in range(self._max_rate_retries + 1):
            delay = max(0, self._cooldown_until - self._clock())
            if delay > self._max_rate_wait:
                raise GroqRequestError(429)
            if delay:
                await self._sleep(delay)
            await self._pace(payload)
            response = await client.post(self._base_url, json=payload, headers={
                "Authorization": f"Bearer {self._keys[slot]}", "Content-Type": "application/json"})
            if response.status_code != 429:
                return response
            # Log all rate-limit headers for diagnostics
            retry_after = response.headers.get("retry-after", "")
            rate_limit_reset = response.headers.get("x-ratelimit-reset-tokens", "")
            rate_limit_reset_requests = response.headers.get("x-ratelimit-reset-requests", "")
            logger.warning("Groq HTTP 429 headers: retry-after=%s reset-tokens=%s reset-requests=%s",
                           retry_after, rate_limit_reset, rate_limit_reset_requests)

            # Evidence-based delay: prefer retry-after, then reset-tokens, then default 60s
            try:
                delay = max(1, float(retry_after)) if retry_after else None
            except ValueError:
                delay = None
            if delay is None and rate_limit_reset:
                # x-ratelimit-reset-tokens is often a Unix timestamp or seconds
                try:
                    reset_val = float(rate_limit_reset)
                    # If it's a large number, it's a Unix timestamp; compute relative delay
                    if reset_val > 1000000:
                        delay = max(1, reset_val - self._clock())
                    else:
                        delay = max(1, reset_val)
                except ValueError:
                    delay = None
            if delay is None:
                delay = 60  # Conservative default
            # If the API says to wait longer than our max, give up immediately
            if delay > self._max_rate_wait:
                self._cooldown_until = self._clock() + delay
                raise GroqRequestError(429)
            self._cooldown_until = self._clock() + delay
            if attempt == self._max_rate_retries:
                raise GroqRequestError(429)
            logger.warning("Groq HTTP 429: cooling down %.1fs (attempt %d/%d)", delay, attempt + 1, self._max_rate_retries + 1)
        raise GroqRequestError(429)

    def _build_payload(self, messages, tools, structured_output):
        """Build OpenAI-compatible chat completion payload."""
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

        if self.model in ("openai/gpt-oss-20b", "openai/gpt-oss-120b"):
            payload["reasoning_effort"] = "low"

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

        if structured_output:
            payload["response_format"] = {"type": "json_object"}

        return payload

    def _parse_response(self, data):
        """Parse OpenAI-compatible response into LLMResponse."""
        choice = data.get("choices", [{}])[0]
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

            async with httpx.AsyncClient(timeout=60, transport=self._transport) as client:
                num_keys = len(self._keys)
                for offset in range(num_keys):
                    slot = (self._active + offset) % num_keys
                    backoff = self.BACKOFF_SEQUENCE[min(max(0, offset - 1), len(self.BACKOFF_SEQUENCE) - 1)]

                    if offset > 0:
                        logger.info(f"Groq: backing off {backoff}s before key slot {slot + 1}")
                        await self._sleep(backoff)

                    try:
                        response = await self._post_with_rate_retry(client, payload, slot)
                    except httpx.TransportError:
                        if offset + 1 < num_keys:
                            logger.warning(f"Groq: transport error on key slot {slot + 1}, rotating")
                            continue
                        raise GroqRequestError(0) from None

                    if response.status_code == 400:
                        # Diagnostic logging for400 errors
                        try:
                            err_body = response.json()
                            err_code = err_body.get("error", {}).get("code")
                            err_msg = err_body.get("error", {}).get("message", "")
                        except (ValueError, AttributeError):
                            err_body = {"raw": response.text[:500]}
                            err_code = None
                            err_msg = ""
                        logger.error("Groq HTTP 400 on key slot %d: code=%s msg=%s payload_keys=%s",
                                     slot + 1, err_code, err_msg[:200], list(payload.keys()))

                        if payload.get("tools") and err_code == "tool_use_failed":
                            logger.warning("Groq tool_use_failed: retrying text decision protocol once")
                            text_payload = dict(payload)
                            definitions = text_payload.pop("tools")
                            text_payload.pop("tool_choice", None)
                            text_payload["messages"] = payload["messages"] + [{"role": "system", "content":
                                "Native tool serialization failed. Return only ACTION: tool_name followed by JSON arguments, "
                                "ANSWER: final answer, or CLARIFY: question. Valid tool definitions: " + json.dumps(definitions)}]
                            response = await self._post_with_rate_retry(client, text_payload, slot)
                        elif payload.get("tools"):
                            # Other400 with tools: try without tools (text-only)
                            logger.warning("Groq HTTP400 with tools: retrying without tools")
                            text_payload = {k: v for k, v in payload.items() if k not in ("tools", "tool_choice")}
                            response = await self._post_with_rate_retry(client, text_payload, slot)
                        else:
                            raise GroqRequestError(400)

                    if response.status_code in (500, 502, 503, 504):
                        if offset + 1 < num_keys:
                            logger.warning(f"Groq: HTTP {response.status_code} on key slot {slot + 1}, rotating")
                            continue
                        raise GroqRequestError(response.status_code)

                    if response.status_code in (401, 403):
                        raise GroqRequestError(response.status_code)

                    if response.is_error:
                        raise GroqRequestError(response.status_code)

                    data = response.json()
                    result = self._parse_response(data)

                    # Record actual usage for better future pacing
                    total_tokens = result.usage.get("prompt_tokens", 0) + result.usage.get("completion_tokens", 0)
                    if total_tokens > 0:
                        self._record_usage(result.usage)
                        logger.debug("Groq actual tokens: prompt=%d completion=%d total=%d",
                                     result.usage.get("prompt_tokens", 0),
                                     result.usage.get("completion_tokens", 0), total_tokens)

                    # Adapt final text response to terminal action if tools available
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

    async def health_check(self):
        try:
            await self.chat([ChatMessage(role="user", content="Say ok")])
            return True
        except Exception:
            return False
