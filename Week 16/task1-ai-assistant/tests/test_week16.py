"""Offline behavioral regression tests; no model quality claims."""
import unittest
from unittest.mock import AsyncMock, patch
from app.agent.loop import AgenticLoop
from app.llm.provider import LLMResponse, ToolCall
from app.tools.registry import ToolRegistry, tool_registry
from app.evaluation.harness import EvaluationHarness
from app.evaluation.failure_injection import test_provider_timeout


def response(text='', calls=None):
    return LLMResponse(content=text, tool_calls=calls or [], usage={'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12})


def call(name, **args):
    return ToolCall(id=name, name=name, arguments=args)


class Week16Tests(unittest.IsolatedAsyncioTestCase):
    def registry(self, executor=lambda query: 'Source: guide.md; RAG retrieves documents.'):
        registry = ToolRegistry()
        registry.register('search_knowledge', 'Search', {'properties': {'query': {'type': 'string'}}, 'required': ['query']}, executor)
        return registry

    async def test_adaptive_search_and_sources_not_model_claims(self):
        registry = self.registry()
        async def chat(messages, tools):
            evidence = messages[-1].content
            return response(calls=[call('answer', answer='RAG retrieves documents [guide.md].')]) if 'guide.md' in evidence else response(calls=[call('search_knowledge', query='RAG')])
        result = await AgenticLoop(AsyncMock(chat=chat), registry=registry).run('What is RAG?')
        self.assertEqual(result.total_iterations, 2)
        self.assertEqual(result.sources_consulted, ['search_knowledge'])
        self.assertEqual(result.total_tokens, {'prompt_tokens': 20, 'completion_tokens': 4})

    async def test_multiple_calls_count_one_iteration(self):
        provider = AsyncMock()
        provider.chat.side_effect = [response(calls=[call('search_knowledge', query='a'), call('search_knowledge', query='b')]), response('ANSWER: verified')]
        result = await AgenticLoop(provider, registry=self.registry()).run('compare')
        self.assertEqual(result.total_iterations, 2)
        self.assertEqual(len(result.steps), 3)

    async def test_limit_and_invalid_decisions(self):
        provider = AsyncMock()
        provider.chat.return_value = response('unparseable prose')
        result = await AgenticLoop(provider, registry=self.registry(), max_iterations=2).run('q')
        self.assertEqual(result.stopped_reason, 'max_iterations')
        self.assertEqual(provider.chat.await_count, 2)
        self.assertIn('incomplete', result.answer)

    async def test_clarification(self):
        provider = AsyncMock()
        provider.chat.return_value = response('CLARIFY: Which deployment budget?')
        result = await AgenticLoop(provider).run('Which is better?')
        self.assertEqual(result.stopped_reason, 'clarification')

    async def test_argument_validation_prevents_execution(self):
        executor = unittest.mock.Mock()
        registry = self.registry(executor)
        result = await registry.execute('search_knowledge', {'query': 3})
        self.assertTrue(result.startswith('Error:'))
        executor.assert_not_called()

    async def test_compaction_counts_tokens_and_retains_query(self):
        provider = AsyncMock()
        provider.chat.side_effect = [response(calls=[call('search_knowledge', query='q')]), response('Summary [guide.md] relevant facts'), response('ANSWER: Facts [guide.md]')]
        loop = AgenticLoop(provider, registry=self.registry(lambda query: 'guide.md ' + 'x'*2900), compact_threshold_chars=1000)
        result = await loop.run('original user question')
        self.assertTrue(result.compacted)
        self.assertEqual(result.total_tokens['prompt_tokens'], 30)
        final_messages = provider.chat.call_args.kwargs['messages']
        self.assertEqual(final_messages[1].content, 'original user question')
        self.assertNotIn('x'*100, final_messages[-1].content)
        self.assertIn('guide.md', final_messages[-1].content)

    async def test_tool_failure_recognized_by_next_decision(self):
        def fail(query):
            raise TimeoutError('injected search outage')
        async def chat(messages, tools):
            if 'Error:' in messages[-1].content:
                return response('ANSWER: Search unavailable; I cannot verify this claim.')
            return response(calls=[call('search_knowledge', query='q')])
        result = await AgenticLoop(AsyncMock(chat=chat), registry=self.registry(fail)).run('verify')
        self.assertEqual(result.sources_consulted, [])
        self.assertIn('cannot verify', result.answer)
        self.assertTrue(result.steps[0].tool_result_summary.startswith('Error:'))

    async def test_provider_timeout_injected(self):
        self.assertTrue((await test_provider_timeout(None))['passed'])

    async def test_provider_error_not_success(self):
        provider = AsyncMock()
        provider.chat.side_effect = TimeoutError('quota or timeout')
        result = await AgenticLoop(provider).run('q')
        harness = EvaluationHarness(None)
        self.assertFalse(harness._evaluate_task_completion(result, {}))
        self.assertEqual(harness._classify_failure(result, {})[0], 'hard')

    async def test_all_expected_tools_required(self):
        provider = AsyncMock()
        provider.chat.side_effect = [response(calls=[call('search_knowledge', query='q')]), response('ANSWER: RAG retrieval generation')]
        registry = self.registry()
        with patch.object(tool_registry, '_tools', registry._tools):
            result = await AgenticLoop(provider, registry=registry).run('q')
            harness = EvaluationHarness(None)
            self.assertFalse(harness._evaluate_tool_correctness(result, {'expected_tools': ['search_knowledge', 'web_search']}))
            self.assertTrue(harness._evaluate_tool_correctness(result, {'expected_tools': ['search_knowledge']}))

    async def test_empty_retrieval_and_compaction_error(self):
        retriever = unittest.mock.Mock()
        retriever.build_context.return_value = None
        provider = AsyncMock()
        provider.chat.return_value = response('ANSWER: KB unavailable; cannot verify.')
        result = await AgenticLoop(provider, rag_retriever=retriever).run('q')
        self.assertIn('Error: empty', provider.chat.call_args.kwargs['messages'][-1].content)
        self.assertEqual(result.sources_consulted, [])

    async def test_bad_iteration_limit(self):
        with self.assertRaises(ValueError):
            AgenticLoop(AsyncMock(), max_iterations=0)

    async def test_duplicate_successful_call_reuses_result(self):
        executor = unittest.mock.Mock(return_value='Evidence [guide.md]')
        provider = AsyncMock()
        provider.chat.side_effect = [response(calls=[call('search_knowledge', query='q')]),
                                    response(calls=[call('search_knowledge', query='q')]),
                                    response('ANSWER: Evidence [guide.md]')]
        result = await AgenticLoop(provider, registry=self.registry(executor)).run('q')
        executor.assert_called_once_with(query='q')
        self.assertEqual(result.steps[1].action, 'duplicate_tool_call')
        self.assertEqual(result.stopped_reason, 'model_answered')
        self.assertIn('already succeeded', provider.chat.call_args.kwargs['messages'][-1].content)
