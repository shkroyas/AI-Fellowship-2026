"""
Evaluation Harness for Agentic Cross-Source Verification.

Builds a from-scratch evaluation framework that tests the agentic loop's
actual behavior. Measures:
- Task completion rate
- Tool-call correctness
- Trajectory length
- Token usage
- Failure classification

No external evaluation frameworks are used.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .test_queries import TEST_QUERIES

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of evaluating a single query."""
    query_id: str
    query: str
    difficulty: str
    answer: str
    sources_consulted: list[str]
    iterations_used: int
    total_tokens: dict
    duration_ms: float
    stopped_reason: str
    compacted: bool
    steps: list[dict]
    # Evaluation metrics
    task_completed: bool = False
    tools_correct: bool = False
    trajectory_reasonable: bool = False
    failure_type: Optional[str] = None  # None, "hard", "soft", "cascading_soft"
    failure_notes: Optional[str] = None


@dataclass
class EvaluationReport:
    """Complete evaluation report across all test queries."""
    results: list[QueryResult]
    total_queries: int
    task_completion_rate: float
    tool_correctness_rate: float
    avg_trajectory_length: float
    avg_tokens_per_query: dict
    failure_summary: dict
    total_tokens_all_queries: dict
    duration_seconds: float


class EvaluationHarness:
    """
    Custom evaluation harness for the agentic loop.

    Runs test queries through the agentic endpoint and evaluates
    the results against expected behavior. Also supports single-pass
    comparison for token/cost analysis.
    """

    def __init__(self, agentic_loop_fn, single_pass_fn=None, progress_path=None):
        """
        Args:
            agentic_loop_fn: An async callable that takes (query, max_iterations)
                and returns an AgenticResult.
            single_pass_fn: Optional async callable that takes (query)
                and returns a dict with 'response', 'usage', 'model' keys.
                Used for token/cost comparison with single-pass mode.
        """
        self.agentic_loop_fn = agentic_loop_fn
        self.single_pass_fn = single_pass_fn
        self.progress_path = progress_path

    @staticmethod
    def _steps(result):
        return [vars(step) if hasattr(step, "__dict__") else step for step in result.steps]

    def _evaluate_task_completion(self, result, expected):
        if result.stopped_reason != expected.get("expected_stop", "model_answered") or not result.answer.strip():
            return False
        if not self._evaluate_tool_correctness(result, expected):
            return False
        answer = result.answer.lower()
        return all(any(word.lower() in answer for word in group)
                   for group in expected.get("answer_contains_any", []))

    def _evaluate_tool_correctness(self, result, expected):
        from ..tools.registry import tool_registry, validate_arguments
        definitions = {d.name: d for d in tool_registry.get_definitions()}
        steps = [s for s in self._steps(result) if s.get("action") == "tool_call"]
        if any(validate_arguments(definitions.get(s.get("tool_name")), s.get("tool_args")) for s in steps):
            return False
        successful = {s.get("tool_name") for s in steps
                      if not (s.get("tool_result_summary") or "").startswith("Error:")}
        return set(expected.get("expected_tools", [])).issubset(successful)

    def _evaluate_trajectory(self, result, expected):
        return expected.get("expected_min_iterations", 1) <= result.total_iterations <= expected.get("expected_max_iterations", 5)

    def _classify_failure(self, result, expected):
        if result.stopped_reason == "error" or not result.answer:
            return "hard", "Execution failed or no response was produced"
        if self._evaluate_task_completion(result, expected) and self._evaluate_trajectory(result, expected):
            return None, ""
        steps = self._steps(result)
        error_indexes = [i for i, s in enumerate(steps) if (s.get("tool_result_summary") or "").startswith("Error:")]
        if error_indexes and any(s.get("action") == "tool_call" for s in steps[error_indexes[0]+1:]):
            return "cascading_soft", "Tool failure followed by further actions and an unmet rubric (trace requires causal review)"
        return "soft", "Response did not meet required evidence, content, stopping or trajectory criteria"

    async def run_single(self, query_data: dict) -> QueryResult:
        """Run and evaluate a single test query."""
        query = query_data["query"]
        logger.info(f"Evaluating: {query_data['id']} - {query[:60]}...")

        try:
            result = await self.agentic_loop_fn(query, max_iterations=5)
        except Exception as e:
            logger.error(f"Query {query_data['id']} failed with exception: {e}")
            return QueryResult(
                query_id=query_data["id"],
                query=query,
                difficulty=query_data["difficulty"],
                answer="",
                sources_consulted=[],
                iterations_used=0,
                total_tokens={},
                duration_ms=0,
                stopped_reason="error",
                compacted=False,
                steps=[],
                task_completed=False,
                tools_correct=False,
                trajectory_reasonable=False,
                failure_type="hard",
                failure_notes=f"Exception: {str(e)}",
            )

        task_completed = self._evaluate_task_completion(result, query_data)
        tools_correct = self._evaluate_tool_correctness(result, query_data)
        trajectory_reasonable = self._evaluate_trajectory(result, query_data)
        failure_type, failure_notes = self._classify_failure(result, query_data)

        # Convert AgenticStep objects to dicts
        steps_dicts = []
        for s in result.steps:
            if hasattr(s, '__dict__'):
                steps_dicts.append({
                    "iteration": s.iteration,
                    "action": s.action,
                    "tool_name": s.tool_name,
                    "tool_args": s.tool_args,
                    "tool_result_summary": s.tool_result_summary,
                })
            elif isinstance(s, dict):
                steps_dicts.append(s)

        return QueryResult(
            query_id=query_data["id"],
            query=query,
            difficulty=query_data["difficulty"],
            answer=result.answer,
            sources_consulted=result.sources_consulted,
            iterations_used=result.total_iterations,
            total_tokens=result.total_tokens,
            duration_ms=result.duration_ms,
            stopped_reason=result.stopped_reason,
            compacted=result.compacted,
            steps=steps_dicts,
            task_completed=task_completed,
            tools_correct=tools_correct,
            trajectory_reasonable=trajectory_reasonable,
            failure_type=failure_type,
            failure_notes=failure_notes,
        )

    async def run_all(self, queries: Optional[list[dict]] = None) -> EvaluationReport:
        """Run all test queries and generate the evaluation report."""
        if queries is None:
            queries = TEST_QUERIES

        self._query_specs = {q["id"]: q for q in queries}
        start_time = time.time()
        results = []

        for query_data in queries:
            result = await self.run_single(query_data)
            results.append(result)
            if self.progress_path:
                from dataclasses import asdict
                self.progress_path.write_text(json.dumps({"complete": False, "results": [asdict(r) for r in results]}, indent=2))
            logger.info(
                f"  {result.query_id}: completed={result.task_completed}, "
                f"tools={result.tools_correct}, iters={result.iterations_used}"
            )

        total_duration = time.time() - start_time

        # Calculate aggregate metrics
        total = len(results)
        completed = sum(1 for r in results if r.task_completed)
        tools_ok = sum(1 for r in results if r.tools_correct)
        avg_iters = sum(r.iterations_used for r in results) / max(total, 1)

        # Token aggregation
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0}
        for r in results:
            for key in r.total_tokens:
                total_tokens[key] = total_tokens.get(key, 0) + r.total_tokens[key]
        avg_tokens = {k: v // max(total, 1) for k, v in total_tokens.items()}

        # Failure summary
        failures = [r for r in results if r.failure_type]
        failure_summary = {
            "total_failures": len(failures),
            "hard_failures": sum(1 for f in failures if f.failure_type == "hard"),
            "soft_failures": sum(1 for f in failures if f.failure_type == "soft"),
            "cascading_soft_failures": sum(1 for f in failures if f.failure_type == "cascading_soft"),
            "failure_details": [
                {"query_id": f.query_id, "type": f.failure_type, "notes": f.failure_notes}
                for f in failures
            ],
        }

        return EvaluationReport(
            results=results,
            total_queries=total,
            task_completion_rate=completed / max(total, 1),
            tool_correctness_rate=tools_ok / max(total, 1),
            avg_trajectory_length=avg_iters,
            avg_tokens_per_query=avg_tokens,
            failure_summary=failure_summary,
            total_tokens_all_queries=total_tokens,
            duration_seconds=round(total_duration, 2),
        )

    def format_report(self, report: EvaluationReport) -> str:
        """Format the evaluation report as readable Markdown."""
        lines = [
            "# Agentic Loop Evaluation Report\n",
            f"**Total Queries:** {report.total_queries}",
            f"**Task Completion Rate:** {report.task_completion_rate:.1%}",
            f"**Tool Correctness Rate:** {report.tool_correctness_rate:.1%}",
            f"**Average Trajectory Length:** {report.avg_trajectory_length:.1f} iterations",
            f"**Total Duration:** {report.duration_seconds:.1f}s",
            f"**Total Tokens:** {report.total_tokens_all_queries}",
            f"**Avg Tokens/Query:** {report.avg_tokens_per_query}",
            "",
            "## Per-Query Results\n",
            "| Query ID | Difficulty | Completed | Tools OK | Iterations | Tokens | Duration |",
            "|----------|-----------|-----------|----------|------------|--------|----------|",
        ]

        for r in report.results:
            token_sum = r.total_tokens.get("prompt_tokens", 0) + r.total_tokens.get("completion_tokens", 0)
            lines.append(
                f"| {r.query_id} | {r.difficulty} | "
                f"{'Yes' if r.task_completed else 'No'} | "
                f"{'Yes' if r.tools_correct else 'No'} | "
                f"{r.iterations_used} | {token_sum} | "
                f"{r.duration_ms:.0f}ms |"
            )

        lines.extend([
            "",
            "## Failure Summary\n",
            f"- **Total Failures:** {report.failure_summary['total_failures']}",
            f"- **Hard Failures:** {report.failure_summary['hard_failures']}",
            f"- **Soft Failures:** {report.failure_summary['soft_failures']}",
            f"- **Cascading Soft Failures:** {report.failure_summary['cascading_soft_failures']}",
        ])

        if report.failure_summary["failure_details"]:
            lines.extend(["", "### Failure Details\n"])
            for detail in report.failure_summary["failure_details"]:
                lines.append(
                    f"- **{detail['query_id']}** ({detail['type']}): {detail['notes']}"
                )

        # Add trajectory analysis
        lines.extend([
            "",
            "## Trajectory Analysis\n",
            "| Query ID | Expected Iters | Actual Iters | Reasonable? | Stopped Reason |",
            "|----------|---------------|-------------|-------------|----------------|",
        ])
        for r in report.results:
            expected = getattr(self, "_query_specs", {}).get(r.query_id, {})
            exp_range = f"{expected.get('expected_min_iterations', 1)}-{expected.get('expected_max_iterations', 5)}"
            lines.append(
                f"| {r.query_id} | {exp_range} | {r.iterations_used} | "
                f"{'Yes' if r.trajectory_reasonable else 'No'} | {r.stopped_reason} |"
            )

        return "\n".join(lines)

    async def run_cost_comparison(self, queries=None):
        """Optional paired comparison; unavailable usage is not a zero-cost success."""
        if not self.single_pass_fn:
            return "Single-pass function not provided. Cannot run cost comparison."
        lines = ["# Paired token comparison", "", "| Query | Single-pass | Agentic | Overhead |",
                 "|---|---:|---:|---:|"]
        for query in queries or TEST_QUERIES[:5]:
            ag, sp = None, None
            try:
                result = await self.agentic_loop_fn(query["query"], max_iterations=5)
                if result.stopped_reason == "model_answered":
                    ag = sum(result.total_tokens.get(k, 0) for k in ("prompt_tokens", "completion_tokens"))
            except Exception:
                pass
            try:
                result = await self.single_pass_fn(query["query"])
                if result.get("response") and result.get("usage"):
                    sp = sum(result["usage"].get(k, 0) for k in ("prompt_tokens", "completion_tokens"))
            except Exception:
                pass
            overhead = f"{(ag-sp)/sp:+.1%}" if ag is not None and sp else "N/A"
            lines.append(f"| {query['id']} | {sp if sp is not None else 'N/A'} | {ag if ag is not None else 'N/A'} | {overhead} |")
        lines += ["", "N/A means failed/unavailable usage. Token counts alone do not establish answer quality or dollar cost."]
        return "\n".join(lines)
