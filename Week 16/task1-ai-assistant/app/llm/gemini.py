"""Async Gemini REST provider with isolated credentials and bounded failover.

Uses the documented generateContent API. Keys are sent in headers only.
Quota/authentication errors never trigger automatic credential rotation.
"""
import asyncio
import time
import uuid
from typing import Optional
from urllib.parse import quote

import httpx

from .provider import ChatMessage, LLMProvider, LLMResponse, ToolCall


class GeminiRequestError(RuntimeError):
    """Sanitized provider error safe for reports (never contains raw response/key)."""
    def __init__(self, status):
        self.status_code = status
        super().__init__(f"Gemini HTTP {status}; check project quota or configuration" if status == 429 else f"Gemini HTTP {status}")


class GeminiProvider(LLMProvider):
    def __init__(self, model='gemini-3.6-flash', api_key=None, temperature=0.7,
                 top_p=0.9, max_tokens=2048, api_keys=None, active_key=1,
                 transport=None):
        super().__init__(model, temperature, top_p, max_tokens)
        # A supplied list takes precedence over the backward-compatible single key.
        keys = list(api_keys) if api_keys is not None else [api_key]
        if not 1 <= len(keys) <= 5 or any(not isinstance(k, str) or not k.strip() for k in keys):
            raise ValueError('Configure between one and five nonempty Gemini keys')
        if len(set(keys)) != len(keys):
            raise ValueError('Gemini key slots must contain distinct credentials')
        if not 1 <= active_key <= len(keys):
            raise ValueError('GEMINI_ACTIVE_KEY must select a configured key')
        self._keys = tuple(k.strip() for k in keys)
        self._active = active_key - 1
        self._transport = transport
        self._cooldown_until = 0.0
        self._lock = asyncio.Lock()

    @staticmethod
    def _payload(messages, tools, structured_output, generation):
        contents, system = [], []
        for message in messages:
            if message.role == 'system':
                system.append({'text': message.content})
                continue
            role = 'model' if message.role == 'assistant' else 'user'
            # Existing W15 interfaces do not retain native function-call messages;
            # send labeled tool data as user text instead of invalid function roles.
            text = ('Untrusted tool result: ' if message.role == 'tool' else '') + message.content
            if contents and contents[-1]['role'] == role:
                contents[-1]['parts'].append({'text': text})
            else:
                contents.append({'role': role, 'parts': [{'text': text}]})
        payload = {'contents': contents, 'generationConfig': generation}
        if system:
            payload['systemInstruction'] = {'parts': system}
        if tools:
            payload['tools'] = [{'functionDeclarations': [
                {'name': t.name, 'description': t.description, 'parameters': t.parameters}
                for t in tools]}]
        if structured_output:
            payload['generationConfig']['responseMimeType'] = 'application/json'
        return payload

    async def chat(self, messages, tools=None, structured_output=None):
        payload = self._payload(messages, tools, structured_output, {
            'temperature': self.temperature, 'topP': self.top_p, 'maxOutputTokens': self.max_tokens})
        url = 'https://generativelanguage.googleapis.com/v1beta/models/' + quote(self.model.removeprefix('models/'), safe='') + ':generateContent'
        async with self._lock:
            if time.monotonic() < self._cooldown_until:
                raise GeminiRequestError(429)
            async with httpx.AsyncClient(timeout=60, transport=self._transport) as client:
                for offset in range(len(self._keys)):
                    slot = (self._active + offset) % len(self._keys)
                    try:
                        response = await client.post(url, json=payload, headers={'x-goog-api-key': self._keys[slot]})
                    except httpx.TransportError:
                        if offset + 1 < len(self._keys):
                            await asyncio.sleep(1)
                            continue
                        raise RuntimeError('Gemini network request failed') from None
                    if response.status_code == 429:
                        # Respect rate limits; do not try another key on quota errors.
                        try:
                            cooldown = max(60, float(response.headers.get('retry-after', '60')))
                        except ValueError:
                            cooldown = 60
                        self._cooldown_until = time.monotonic() + cooldown
                        raise GeminiRequestError(429)
                    if response.status_code in (500, 502, 503, 504) and offset + 1 < len(self._keys):
                        await asyncio.sleep(1)
                        continue
                    if response.is_error:
                        raise GeminiRequestError(response.status_code)
                    data = response.json()
                    candidates = data.get('candidates') or []
                    if not candidates:
                        raise RuntimeError('Gemini returned no candidate (possibly blocked)')
                    parts = candidates[0].get('content', {}).get('parts', [])
                    text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
                    calls = [ToolCall(id=str(uuid.uuid4()), name=p['functionCall']['name'],
                                      arguments=p['functionCall'].get('args', {}))
                             for p in parts if 'functionCall' in p]
                    if not text and not calls:
                        raise RuntimeError('Gemini returned no usable answer or tool call')
                    # Native tool APIs ordinarily finish with plain assistant text.
                    # Adapt that final message to the agent's terminal action while
                    # preserving explicit ACTION/CLARIFY text for text-mode parsing.
                    if text and not calls and tools and any(t.name == 'answer' for t in tools):
                        if not text.lstrip().upper().startswith(('ACTION:', 'ANSWER:', 'CLARIFY:')):
                            calls = [ToolCall(id=str(uuid.uuid4()), name='answer', arguments={'answer': text})]
                    if structured_output and text:
                        self._validate_json_output(text)
                    metadata = data.get('usageMetadata', {})
                    return LLMResponse(content=text, tool_calls=calls, model=self.model, usage={
                        'prompt_tokens': metadata.get('promptTokenCount', 0),
                        'completion_tokens': metadata.get('candidatesTokenCount', 0) + metadata.get('thoughtsTokenCount', 0),
                    })

    async def health_check(self):
        try:
            await self.chat([ChatMessage(role='user', content='Say ok')])
            return True
        except Exception:
            return False
