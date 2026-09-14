import json
import unittest
from unittest.mock import patch, AsyncMock
import httpx
from app.llm.groq import GroqProvider, GroqRequestError
from app.llm.provider import ChatMessage, ToolDefinition


class GroqKeysTests(unittest.IsolatedAsyncioTestCase):
    def success(self):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        })

    async def test_selected_key_and_token_accounting(self):
        seen = []
        def handle(req):
            auth = req.headers.get("authorization", "")
            seen.append(auth.replace("Bearer ", ""))
            self.assertNotIn("gsk_", str(req.url))
            return self.success()
        p = GroqProvider(api_keys=["key1", "key2"], active_key=2, transport=httpx.MockTransport(handle))
        result = await p.chat([ChatMessage(role="user", content="hello")])
        self.assertEqual(seen, ["key2"])
        self.assertEqual(result.usage, {"prompt_tokens": 10, "completion_tokens": 2})

    async def test_503_failover_is_bounded(self):
        seen = []
        def handle(req):
            auth = req.headers.get("authorization", "").replace("Bearer ", "")
            seen.append(auth)
            return httpx.Response(503) if len(seen) == 1 else self.success()
        with patch("app.llm.groq.asyncio.sleep", new_callable=AsyncMock):
            p = GroqProvider(api_keys=["one", "two"], transport=httpx.MockTransport(handle))
            self.assertEqual((await p.chat([])).content, "ok")
        self.assertEqual(seen, ["one", "two"])

    async def test_quota_never_rotates_and_cools_down(self):
        seen = []
        def handle(req):
            auth = req.headers.get("authorization", "").replace("Bearer ", "")
            seen.append(auth)
            return httpx.Response(429, headers={"retry-after": "120"}, json={"error": "rate limited"})
        p = GroqProvider(api_keys=["secret1", "secret2"], transport=httpx.MockTransport(handle))
        for _ in range(2):
            with self.assertRaises(GroqRequestError) as caught:
                await p.chat([])
            self.assertNotIn("secret", str(caught.exception))
        self.assertEqual(seen, ["secret1"])

    async def test_auth_does_not_rotate(self):
        seen = []
        def handle(req):
            auth = req.headers.get("authorization", "").replace("Bearer ", "")
            seen.append(auth)
            return httpx.Response(403)
        with self.assertRaises(GroqRequestError):
            await GroqProvider(api_keys=["one", "two"], transport=httpx.MockTransport(handle)).chat([])
        self.assertEqual(seen, ["one"])

    async def test_separate_clients_do_not_share_credentials(self):
        seen = []
        def handle(req):
            auth = req.headers.get("authorization", "").replace("Bearer ", "")
            seen.append(auth)
            return self.success()
        transport = httpx.MockTransport(handle)
        a = GroqProvider(api_keys=["a"], transport=transport)
        b = GroqProvider(api_keys=["b"], transport=transport)
        await a.chat([])
        await b.chat([])
        await a.chat([])
        self.assertEqual(seen, ["a", "b", "a"])

    async def test_native_tool_and_role_serialization(self):
        def handle(req):
            body = json.loads(req.content)
            self.assertEqual(body["messages"][0]["role"], "user")
            return httpx.Response(200, json={
                "choices": [{"message": {
                    "tool_calls": [{"id": "tc1", "function": {"name": "calculator", "arguments": json.dumps({"expression": "1+1"})}}]
                }}]
            })
        result = await GroqProvider(api_key="a", transport=httpx.MockTransport(handle)).chat([
            ChatMessage(role="user", content="question"), ChatMessage(role="tool", content="evidence")])
        self.assertEqual(result.tool_calls[0].arguments, {"expression": "1+1"})

    async def test_invalid_pool(self):
        for keys in [[], ["a"] * 6, ["a", "a"], [""]]:
            with self.assertRaises(ValueError):
                GroqProvider(api_keys=keys)

    async def test_native_final_text_becomes_agent_answer(self):
        provider = GroqProvider(api_key="a", transport=httpx.MockTransport(lambda req: self.success()))
        terminal = ToolDefinition(name="answer", description="Final answer",
                                  parameters={"properties": {"answer": {"type": "string"}}, "required": ["answer"]})
        result = await provider.chat([ChatMessage(role="user", content="question")], tools=[terminal])
        self.assertEqual(result.tool_calls[0].name, "answer")
        self.assertEqual(result.tool_calls[0].arguments, {"answer": "ok"})
