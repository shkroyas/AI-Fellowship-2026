import json
import unittest
from unittest.mock import patch, AsyncMock
import httpx
from app.llm.gemini import GeminiProvider, GeminiRequestError
from app.llm.provider import ChatMessage, ToolDefinition


class GeminiKeysTests(unittest.IsolatedAsyncioTestCase):
    def success(self):
        return httpx.Response(200, json={'candidates':[{'content':{'parts':[{'text':'ok'}]}}],
                                        'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':2,'thoughtsTokenCount':3}})

    async def test_selected_key_and_token_accounting(self):
        seen=[]
        def handle(req):
            seen.append(req.headers['x-goog-api-key'])
            self.assertNotIn('secret', str(req.url))
            return self.success()
        p=GeminiProvider(api_keys=['secret1','secret2'], active_key=2, transport=httpx.MockTransport(handle))
        result=await p.chat([ChatMessage(role='user',content='hello')])
        self.assertEqual(seen,['secret2'])
        self.assertEqual(result.usage,{'prompt_tokens':10,'completion_tokens':5})

    async def test_503_failover_is_bounded(self):
        seen=[]
        def handle(req):
            seen.append(req.headers['x-goog-api-key'])
            return httpx.Response(503) if len(seen)==1 else self.success()
        with patch('app.llm.gemini.asyncio.sleep',new_callable=AsyncMock):
            p=GeminiProvider(api_keys=['one','two'],transport=httpx.MockTransport(handle))
            self.assertEqual((await p.chat([])).content,'ok')
        self.assertEqual(seen,['one','two'])

    async def test_quota_never_rotates_and_cools_down(self):
        seen=[]
        def handle(req):
            seen.append(req.headers['x-goog-api-key'])
            return httpx.Response(429,headers={'retry-after':'120'},json={'error':'secret1'})
        p=GeminiProvider(api_keys=['secret1','secret2'],transport=httpx.MockTransport(handle))
        for _ in range(2):
            with self.assertRaises(GeminiRequestError) as caught:
                await p.chat([])
            self.assertNotIn('secret',str(caught.exception))
        self.assertEqual(seen,['secret1'])

    async def test_auth_does_not_rotate(self):
        seen=[]
        def handle(req):
            seen.append(req.headers['x-goog-api-key'])
            return httpx.Response(403)
        with self.assertRaises(GeminiRequestError):
            await GeminiProvider(api_keys=['one','two'],transport=httpx.MockTransport(handle)).chat([])
        self.assertEqual(seen,['one'])

    async def test_separate_clients_do_not_share_credentials(self):
        seen=[]
        def handle(req):
            seen.append(req.headers['x-goog-api-key'])
            return self.success()
        transport=httpx.MockTransport(handle)
        a=GeminiProvider(api_key='a',transport=transport)
        b=GeminiProvider(api_key='b',transport=transport)
        await a.chat([])
        await b.chat([])
        await a.chat([])
        self.assertEqual(seen,['a','b','a'])

    async def test_native_tool_and_role_serialization(self):
        def handle(req):
            body=json.loads(req.content)
            self.assertEqual(body['contents'][0]['role'],'user')
            self.assertEqual(len(body['contents']),1)
            return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'functionCall':{'name':'calculator','args':{'expression':'1+1'}}}]}}]})
        result=await GeminiProvider(api_key='a',transport=httpx.MockTransport(handle)).chat([
            ChatMessage(role='user',content='question'),ChatMessage(role='tool',content='evidence')])
        self.assertEqual(result.tool_calls[0].arguments,{'expression':'1+1'})

    async def test_invalid_pool(self):
        for keys in [[],['a']*6,['a','a'],['']]:
            with self.assertRaises(ValueError):
                GeminiProvider(api_keys=keys)

    async def test_native_final_text_becomes_agent_answer(self):
        provider=GeminiProvider(api_key='a',transport=httpx.MockTransport(lambda req:self.success()))
        terminal=ToolDefinition(name='answer',description='Final answer',parameters={'properties':{'answer':{'type':'string'}},'required':['answer']})
        result=await provider.chat([ChatMessage(role='user',content='question')],tools=[terminal])
        self.assertEqual(result.tool_calls[0].name,'answer')
        self.assertEqual(result.tool_calls[0].arguments,{'answer':'ok'})
