"""Reproducible custom harness: offline fixtures or explicit live provider evaluation.

Live mode reuses one paced provider across all queries and wires the configured
OpenRouter fallback. Keys do not multiply an organization token allowance.
"""
import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.agent.loop import AgenticLoop
from app.llm.provider import LLMResponse, ToolCall
from app.tools.registry import tool_registry
from app.evaluation.harness import EvaluationHarness
from app.evaluation.test_queries import TEST_QUERIES


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['offline', 'live'], default='offline')
    parser.add_argument('--delay', type=float, default=3, help='Live delay between queries (seconds)')
    parser.add_argument('--failure-injection', action='store_true', help='Run failure injections instead of the query suite (live mode)')
    parser.add_argument('--ids', nargs='+', help='Run only these query IDs; output uses a subset suffix')
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("app.evaluation.harness").setLevel(logging.INFO)
    retriever = None
    if args.mode == 'live':
        from app.config import settings
        from app.rag.retriever import RAGRetriever
        from app.tools.calculator import calculator_tool
        from app.tools.web_search import web_search_tool, datetime_tool
        from app.tools.knowledge_search import create_knowledge_search_tool
        retriever = RAGRetriever()
        retriever.ingest_documents()
        for tool in [calculator_tool, web_search_tool, datetime_tool, create_knowledge_search_tool(retriever)]:
            tool_registry.register(**tool)

        from app.llm.provider import get_provider
        provider = get_provider()
        fallback = None
        if settings.openrouter_api_key and settings.llm_provider != "openrouter":
            try:
                fallback = get_provider('openrouter')
            except Exception as e:
                logging.warning("Failed to create OpenRouter fallback: %s", e)
        elif settings.groq_keys() and settings.llm_provider != "groq":
            try:
                fallback = get_provider('groq')
            except Exception as e:
                logging.warning("Failed to create Groq fallback: %s", e)
        queries = TEST_QUERIES
        label = (f'Live provider: {provider.model}; shared sequential budget; '
                 f'fallback: {fallback.model if fallback else "disabled"}; '
                 f'max output tokens: {settings.max_tokens}')
    else:
        for name in ['search_knowledge', 'web_search']:
            tool_registry.register(name, 'Fixture search', {'properties': {'query': {'type': 'string'}}, 'required': ['query']},
                                   lambda query: 'Fixture evidence: RAG retrieves documents; fine-tuning changes weights [guide.md].')
        queries = [
            {'id': 'cross_source', 'query': 'compare', 'difficulty': 'moderate', 'expected_tools': ['search_knowledge','web_search'], 'answer_contains_any': [['rag'], ['fine-tuning']], 'expected_min_iterations': 3},
            {'id': 'clarification', 'query': 'ambiguous', 'difficulty': 'simple', 'expected_tools': [], 'expected_stop': 'clarification'},
            {'id': 'provider_failure', 'query': 'timeout', 'difficulty': 'simple', 'expected_tools': []},
            {'id': 'wrong_answer', 'query': 'wrong', 'difficulty': 'simple', 'expected_tools': [], 'answer_contains_any': [['51']]},
        ]
        label = 'Offline scripted provider and tools; synthetic tokens. NOT a live-model quality score.'

    async def run(query, max_iterations=5):
        if args.mode == 'offline':
            def resp(text):
                return LLMResponse(content=text, usage={'prompt_tokens':10,'completion_tokens':2})
            scripts = {'compare': [resp('ACTION: search_knowledge {"query":"RAG"}'), resp('ACTION: web_search {"query":"fine tuning"}'), resp('ANSWER: RAG retrieves documents; fine-tuning changes weights [guide.md].')],
                       'ambiguous': [resp('CLARIFY: What is your budget?')], 'timeout': [TimeoutError('injected timeout')], 'wrong': [resp('ANSWER: 99')]}
            provider_for_run = AsyncMock()
            provider_for_run.chat.side_effect = scripts[query]
        else:
            provider_for_run = provider
            if args.delay:
                await asyncio.sleep(args.delay)
        return await AgenticLoop(provider_for_run, retriever, max_iterations,
                                fallback_provider=fallback if args.mode == "live" else None,
                                initial_retrieval=True).run(query)

    if args.failure_injection:
        if args.mode != 'live':
            parser.error('--failure-injection requires --mode live')
        from app.evaluation.failure_injection import run_all_failure_tests, format_failure_report
        results = await run_all_failure_tests(run, retriever)
        output = Path(__file__).parent / 'failure_injection_live'
        output.with_suffix('.json').write_text(json.dumps({'description':label, 'results':results}, indent=2))
        output.with_suffix('.md').write_text(label + '\n\n' + format_failure_report(results))
        print(format_failure_report(results))
        return
    if args.ids:
        unknown = set(args.ids) - {q['id'] for q in queries}
        if unknown:
            parser.error('Unknown query IDs: ' + ', '.join(sorted(unknown)))
        queries = [q for q in queries if q['id'] in args.ids]

    harness = EvaluationHarness(run, progress_path=Path(__file__).parent / ("progress_" + args.mode + ".json"))
    report = await harness.run_all(queries)
    output = Path(__file__).parent / ('evaluation_' + args.mode + ('_subset' if args.ids else ''))
    output.with_suffix('.json').write_text(json.dumps({'mode': args.mode, 'description':label, 'generated_at':datetime.now(timezone.utc).isoformat(), 'queries': queries, 'report':asdict(report)}, indent=2))
    output.with_suffix('.md').write_text(label + '\n\n' + harness.format_report(report))
    if harness.progress_path:
        harness.progress_path.write_text(json.dumps({"complete": True, "results": [asdict(r) for r in report.results]}, indent=2))
    print(label)
    print(harness.format_report(report))


if __name__ == '__main__':
    asyncio.run(main())
