"""Deterministic transport tests for pacing, bounded retries and fallback."""
import unittest
from unittest.mock import AsyncMock
import httpx
from app.llm.groq import GroqProvider, GroqRequestError
from app.llm.openrouter import OpenRouterProvider, OpenRouterRequestError
from app.llm.provider import ChatMessage, LLMResponse, ToolDefinition
from app.agent.loop import AgenticLoop

class VirtualClock:
    def __init__(self): self.now = 0; self.waits = []
    def time(self): return self.now
    async def sleep(self, seconds): self.waits.append(seconds); self.now += seconds

def success():
    return httpx.Response(200, json={'choices':[{'message':{'content':'ok'}}],
                                   'usage':{'prompt_tokens':10,'completion_tokens':2}})

class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_key_retry_honors_retry_after(self):
        clock=VirtualClock(); seen=[]
        def handle(req):
            seen.append(req.headers['authorization'])
            return httpx.Response(429,headers={'retry-after':'4'}) if len(seen)==1 else success()
        p=GroqProvider(api_keys=['a','b'],max_tokens=100,transport=httpx.MockTransport(handle),clock=clock.time,sleep=clock.sleep)
        self.assertEqual((await p.chat([])).content,'ok')
        self.assertEqual(seen,['Bearer a','Bearer a'])
        self.assertEqual(clock.waits,[4])

    async def test_budget_spans_multiple_calls(self):
        clock=VirtualClock()
        p=GroqProvider(api_key='a',max_tokens=300,tokens_per_minute=1000,transport=httpx.MockTransport(lambda req:success()),clock=clock.time,sleep=clock.sleep)
        for _ in range(3): await p.chat([ChatMessage(role='user',content='hello')])
        self.assertGreaterEqual(sum(clock.waits),61)

    async def test_persistent_429_is_bounded(self):
        clock=VirtualClock(); seen=[]
        def handle(req):
            seen.append(req.headers['authorization'])
            return httpx.Response(429,headers={'retry-after':'1'})
        p=GroqProvider(api_keys=['a','b'],max_tokens=100,transport=httpx.MockTransport(handle),clock=clock.time,sleep=clock.sleep)
        with self.assertRaises(GroqRequestError): await p.chat([])
        self.assertEqual(seen,['Bearer a']*3)

    async def test_fallback_is_used_and_primary_failure_retained(self):
        primary=AsyncMock(); primary.chat.side_effect=GroqRequestError(429)
        fallback=AsyncMock(); fallback.chat.return_value=LLMResponse(content='ANSWER: Available evidence is insufficient.',usage={'prompt_tokens':7,'completion_tokens':3})
        result=await AgenticLoop(primary,fallback_provider=fallback).run('verify')
        self.assertEqual(result.stopped_reason,'model_answered')
        self.assertEqual(result.steps[0].action,'provider_fallback')
        self.assertIn('429',result.steps[0].tool_result_summary)
        self.assertEqual(result.total_tokens['prompt_tokens'],7)

    async def test_final_decision_has_only_terminal_tools(self):
        p=AsyncMock(); p.chat.return_value=LLMResponse(content='ANSWER: Cannot verify without evidence.')
        await AgenticLoop(p,max_iterations=1).run('verify')
        self.assertEqual({t.name for t in p.chat.call_args.kwargs['tools']},{'answer','ask_user'})

    async def test_openrouter_rejects_error_in_success_envelope(self):
        p=OpenRouterProvider(api_key='a',transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'error':{'message':'upstream failure'}})))
        with self.assertRaises(OpenRouterRequestError): await p.chat([])

    async def test_openrouter_requires_tool_capable_route(self):
        import json
        def handle(req):
            self.assertEqual(json.loads(req.content)['provider'],{'require_parameters':True})
            return success()
        p=OpenRouterProvider(api_key='a',transport=httpx.MockTransport(handle))
        await p.chat([],tools=[ToolDefinition(name='answer',description='Answer',parameters={'type':'object'})])

    async def test_failure_runner_survives_injection_exception(self):
        from app.evaluation.failure_injection import run_all_failure_tests
        run=AsyncMock(side_effect=RuntimeError('injected runner fault'))
        results=await run_all_failure_tests(run)
        self.assertEqual(len(results),3)
        self.assertTrue(results[0]['inconclusive'])
        self.assertTrue(results[1]['inconclusive'])
        self.assertTrue(results[2]['passed'])

    async def test_rejected_native_tool_generation_retries_text_once(self):
        import json
        clock=VirtualClock(); payloads=[]
        def handle(req):
            payloads.append(json.loads(req.content))
            if len(payloads)==1:
                return httpx.Response(400,json={'error':{'code':'tool_use_failed','failed_generation':'not executable'}})
            return success()
        p=GroqProvider(model='openai/gpt-oss-20b',api_key='a',max_tokens=100,clock=clock.time,sleep=clock.sleep,transport=httpx.MockTransport(handle))
        terminal=ToolDefinition(name='answer',description='Answer',parameters={'type':'object'})
        result=await p.chat([],tools=[terminal])
        self.assertEqual(result.tool_calls[0].name,'answer')
        self.assertEqual(len(payloads),2)
        self.assertIn('tools',payloads[0]); self.assertNotIn('tools',payloads[1])
        self.assertEqual(payloads[0]['reasoning_effort'],'low')
