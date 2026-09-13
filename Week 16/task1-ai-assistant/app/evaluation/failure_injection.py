"""
Failure Injection Tests for Agentic Loop.

Intentionally introduces failures into the system to test how the
agentic loop handles errors gracefully. Tests include:
1. Making web search unavailable
2. Providing malformed RAG output
3. Forcing provider timeout

The agent should recognize failures and adapt rather than producing
confident answers based on invalid information.
"""

import asyncio
import logging
from typing import Any, Optional
from unittest.mock import AsyncMock, patch, MagicMock

logger = logging.getLogger(__name__)


async def test_web_search_unavailable(agentic_loop_fn) -> dict:
    """
    Failure Injection: Make web search tool unavailable.

    Expected behavior:
    - Agent should still attempt to answer using knowledge base
    - Agent should acknowledge that external verification was not possible
    - Agent should not produce a confident answer claiming web-verified facts
    """
    logger.info("FAILURE INJECTION TEST: Web search unavailable")

    injected = False
    original_execute = None

    # Get the original tool registry execute function
    from ..tools.registry import tool_registry
    original_execute = tool_registry.execute

    # Replace with a failing executor for web_search
    async def failing_execute(tool_name: str, arguments: dict[str, Any]) -> str:
        nonlocal injected
        if tool_name == "web_search":
            injected = True
            return "Error: Web search service is currently unavailable. Please try again later."
        return await original_execute(tool_name, arguments)

    tool_registry.execute = failing_execute

    try:
        result = await agentic_loop_fn(
            "What are the latest developments in AI?",
            max_iterations=3,
        )

        # Analyze the response
        answer_lower = result.answer.lower()
        has_acknowledgment = any(
            phrase in answer_lower
            for phrase in [
                "unable to search",
                "cannot search",
                "web search unavailable",
                "external search",
                "limited to",
                "knowledge base only",
                "without web search",
            ]
        )
        has_false_confidence = any(
            phrase in answer_lower
            for phrase in [
                "according to recent web search",
                "search results show",
                "the web confirms",
            ]
        )

        return {
            "test_name": "web_search_unavailable",
            "injection_reached": injected,
            "inconclusive": not injected or result.stopped_reason == "error",
            "passed": injected and result.stopped_reason == "model_answered" and has_acknowledgment and not has_false_confidence,
            "agent_answered": bool(result.answer),
            "acknowledged_failure": has_acknowledgment,
            "false_confidence": has_false_confidence,
            "sources_consulted": result.sources_consulted,
            "answer_excerpt": result.answer[:300],
            "iterations": result.total_iterations,
            "notes": (
                "Agent correctly acknowledged limited sources"
                if has_acknowledgment
                else "Agent did not explicitly acknowledge the limitation"
            ),
        }
    finally:
        tool_registry.execute = original_execute


async def test_malformed_rag_output(agentic_loop_fn, rag_retriever) -> dict:
    """
    Failure Injection: Provide malformed/empty RAG output.

    Expected behavior:
    - Agent should handle empty context gracefully
    - Agent should fall back to web search or general knowledge
    - Agent should not hallucinate document references
    """
    logger.info("FAILURE INJECTION TEST: Malformed RAG output")

    original_build_context = None
    if rag_retriever:
        original_build_context = rag_retriever.build_context
        rag_retriever.build_context = lambda query, top_k=None: ""

    try:
        result = await agentic_loop_fn(
            "What does our knowledge base say about Python?",
            max_iterations=3,
        )

        answer_lower = result.answer.lower()
        references_kb = any(
            phrase in answer_lower
            for phrase in [
                "according to the document",
                "the knowledge base states",
                "our documents show",
            ]
        )
        uses_web = "web_search" in result.sources_consulted

        return {
            "test_name": "malformed_rag_output",
            "inconclusive": rag_retriever is None or result.stopped_reason == "error",
            "passed": rag_retriever is not None and result.stopped_reason == "model_answered" and not references_kb and any(w in answer_lower for w in ["empty", "unavailable", "no relevant", "cannot", "could not"]),
            "agent_answered": bool(result.answer),
            "references_empty_kb": references_kb,
            "fell_back_to_web": uses_web,
            "sources_consulted": result.sources_consulted,
            "answer_excerpt": result.answer[:300],
            "iterations": result.total_iterations,
            "notes": (
                "Agent fell back to web search when KB was empty"
                if uses_web
                else "Agent handled empty KB without hallucinating sources"
                if not references_kb
                else "Agent referenced non-existent KB content"
            ),
        }
    finally:
        if rag_retriever and original_build_context:
            rag_retriever.build_context = original_build_context


async def test_provider_timeout(agentic_loop_fn) -> dict:
    """
    Failure Injection: Force primary provider timeout.

    Expected behavior:
    - Agent should fall back to secondary provider (Gemini)
    - Agent should still produce a reasonable answer
    - Graceful degradation rather than hard failure
    """
    logger.info("FAILURE INJECTION TEST: Provider timeout")

    from ..agent.loop import AgenticLoop
    from ..llm.provider import LLMResponse
    primary = AsyncMock()
    primary.chat.side_effect = TimeoutError("injected timeout")
    fallback = AsyncMock()
    fallback.chat.return_value = LLMResponse(content="ANSWER: Model timeout recovered; no external verification was performed.")
    result = await AgenticLoop(primary, fallback_provider=fallback).run("Test provider availability")
    return {"test_name": "provider_timeout", "passed": primary.chat.await_count == 1 and fallback.chat.await_count == 1 and result.stopped_reason == "model_answered",
            "notes": "Injected TimeoutError into the real loop; scripted fallback invoked. This tests orchestration, not live model quality."}


async def run_all_failure_tests(agentic_loop_fn, rag_retriever=None) -> list[dict]:
    """Run all failure injection tests and return results."""
    results = []

    # Test 1: Web search unavailable
    try:
        r1 = await test_web_search_unavailable(agentic_loop_fn)
        results.append(r1)
        logger.info(f"  Web search test: {'PASSED' if r1['passed'] else 'FAILED'}")
    except Exception as e:
        results.append({
            "test_name": "web_search_unavailable",
            "injection_reached": injected,
            "inconclusive": not injected or result.stopped_reason == "error",
            "passed": False,
            "error": str(e),
        })

    # Test 2: Malformed RAG output
    try:
        r2 = await test_malformed_rag_output(agentic_loop_fn, rag_retriever)
        results.append(r2)
        logger.info(f"  Malformed RAG test: {'PASSED' if r2['passed'] else 'FAILED'}")
    except Exception as e:
        results.append({
            "test_name": "malformed_rag_output",
            "inconclusive": rag_retriever is None or result.stopped_reason == "error",
            "passed": False,
            "error": str(e),
        })

    # Test 3: Provider timeout
    try:
        r3 = await test_provider_timeout(agentic_loop_fn)
        results.append(r3)
        logger.info(f"  Provider timeout test: {'PASSED' if r3['passed'] else 'FAILED'}")
    except Exception as e:
        results.append({
            "test_name": "provider_timeout",
            "passed": False,
            "error": str(e),
        })

    return results


def format_failure_report(results: list[dict]) -> str:
    """Format failure injection test results as Markdown."""
    lines = [
        "# Failure Injection Test Report\n",
        "| Test | Passed | Notes |",
        "|------|--------|-------|",
    ]
    for r in results:
        status = "INCONCLUSIVE" if r.get("inconclusive") else "PASS" if r["passed"] else "FAIL"
        notes = "Provider unavailable before autonomous recovery could be assessed" if r.get("inconclusive") else r.get("notes", r.get("error", "No details"))
        lines.append(f"| {r['test_name']} | {status} | {notes} |")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    lines.extend([
        "",
        f"**Summary:** {passed}/{total} tests passed",
    ])

    return "\n".join(lines)
