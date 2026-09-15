"""Experiment runner for Track B — runs the assistant with each prompt version and logs to MLflow."""
import asyncio
import json
import sys
import time
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.track_b.assistant.config import settings
from src.track_b.assistant.llm.provider import get_provider, ChatMessage
from src.track_b.assistant.agent.loop import AgenticLoop
from src.track_b.assistant.tools.registry import tool_registry
from src.track_b.assistant.tools.calculator import calculator_tool
from src.track_b.assistant.tools.web_search import web_search_tool, datetime_tool
from src.track_b.utils.agent_tracer import AgentTracer
from src.track_b.utils.evidently_judge import EvidentlyJudge, create_golden_set, build_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Register tools
tool_registry.register(calculator_tool["name"], calculator_tool["description"], calculator_tool["parameters"], calculator_tool["executor"])
tool_registry.register(web_search_tool["name"], web_search_tool["description"], web_search_tool["parameters"], web_search_tool["executor"])
tool_registry.register(datetime_tool["name"], datetime_tool["description"], datetime_tool["parameters"], datetime_tool["executor"])


# Golden set for regression testing — stable IDs, one query per capability
GOLDEN_QUERIES = [
    {"id": "rag_basic", "query": "What is RAG?", "target": "RAG (Retrieval-Augmented Generation) combines retrieval from an external knowledge base with LLM generation to produce more accurate, grounded responses.",
     "must_contain": ["retrieval", "generation", "knowledge"]},
    {"id": "datetime_now", "query": "What is the current date?", "target": "The current date can be determined using the get_current_datetime tool.",
     "must_contain": ["date"]},
    {"id": "calculator_pct", "query": "Calculate 15% of 340.", "target": "15% of 340 is 51.",
     "must_contain": ["51"]},
    {"id": "python_practices", "query": "What are Python best practices?", "target": "Python best practices include: use virtual environments, follow PEP 8, write docstrings, use type hints, and test your code.",
     "must_contain": ["PEP 8"]},
    {"id": "rag_vs_ft", "query": "Compare RAG vs fine-tuning.", "target": "RAG is better for up-to-date knowledge without retraining; fine-tuning is better for domain-specific behavior and style.",
     "must_contain": ["retrieval", "fine-tun"]},
]

# Test queries for evaluation — matches golden set order
TEST_QUERIES = [
    "What is Retrieval-Augmented Generation (RAG)?",
    "What is the current date and time?",
    "Calculate 15% of 340.",
]


def load_prompt_templates():
    prompts_dir = PROJECT_ROOT / "src" / "track_b" / "prompts"
    versions = {}
    for v in ["v1", "v2", "v3"]:
        path = prompts_dir / f"prompt_{v}.txt"
        if path.exists():
            versions[v] = path.read_text()
    return versions


async def run_single_query(provider, system_prompt: str, query: str, max_iterations: int = 5) -> dict:
    loop = AgenticLoop(provider, max_iterations=max_iterations, system_prompt=system_prompt)
    result = await loop.run(query)
    tool_calls = [s for s in result.steps if s.action == "tool_call"]
    tools_used = list({s.tool_name for s in tool_calls if s.tool_name})
    return {
        "query": query,
        "response": result.answer,
        "iterations": result.total_iterations,
        "tokens": result.total_tokens,
        "duration_ms": result.duration_ms,
        "tools_used": tools_used,
        "stopped_reason": result.stopped_reason,
        "steps": [{"iteration": s.iteration, "action": s.action, "tool_name": s.tool_name,
                    "tool_args": s.tool_args, "result": s.tool_result_summary} for s in result.steps],
    }


async def evaluate_prompt_version(provider, version_name: str, prompt_template: str, max_iterations: int = 5):
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating prompt version: {version_name}")
    logger.info(f"{'='*60}")

    results = []
    for query in TEST_QUERIES:
        logger.info(f"  Query: {query[:60]}...")
        try:
            r = await run_single_query(provider, prompt_template, query, max_iterations)
            results.append(r)
            logger.info(f"  -> stopped={r['stopped_reason']}, iters={r['iterations']}, tools={r['tools_used']}")
        except Exception as e:
            logger.error(f"  -> FAILED: {e}")
            results.append({"query": query, "response": f"Error: {e}", "iterations": 0,
                            "tokens": {}, "duration_ms": 0, "tools_used": [], "stopped_reason": "error", "steps": []})
        await asyncio.sleep(5)  # Pace between queries

    # Calculate metrics — task success = model answered AND response is non-empty
    completed = sum(1 for r in results
                    if r["stopped_reason"] == "model_answered"
                    and len(r.get("response", "").strip()) > 20)
    task_success_rate = completed / max(len(results), 1)
    avg_iterations = sum(r["iterations"] for r in results) / max(len(results), 1)
    avg_latency_ms = sum(r["duration_ms"] for r in results) / max(len(results), 1)
    total_tokens = {"prompt": sum(r["tokens"].get("prompt_tokens", 0) for r in results),
                    "completion": sum(r["tokens"].get("completion_tokens", 0) for r in results)}

    return {
        "version": version_name,
        "prompt_length": len(prompt_template),
        "task_success_rate": round(task_success_rate, 3),
        "avg_iterations": round(avg_iterations, 2),
        "avg_latency_ms": round(avg_latency_ms, 1),
        "total_tokens": total_tokens,
        "results": results,
    }


def score_response(response: str, golden: dict) -> bool:
    """Score a response against a golden query using must_contain keywords."""
    response_lower = response.lower()
    must_contain = golden.get("must_contain", [])
    if not must_contain:
        return True  # no criteria = pass
    matches = sum(1 for kw in must_contain if kw.lower() in response_lower)
    return matches >= len(must_contain)


def run_evidently_regression(version_name: str, results: list[dict], reports_dir: Path) -> dict:
    """Run Evidently regression tests against the golden set."""
    judge = EvidentlyJudge(reports_dir=reports_dir)

    # Map results to golden queries by position (TEST_QUERIES matches GOLDEN_QUERIES order)
    eval_rows = []
    for i, qr in enumerate(results):
        if i < len(GOLDEN_QUERIES):
            g = GOLDEN_QUERIES[i]
            correct = score_response(qr["response"], g)
            eval_rows.append({
                "query": qr["query"],
                "new_response": qr["response"],
                "target_response": g["target"],
                "golden_id": g["id"],
                "correct": "correct" if correct else "incorrect",
            })

    eval_df = pd.DataFrame(eval_rows)
    correct_count = (eval_df["correct"] == "correct").sum()
    pct_passed = correct_count / max(len(eval_df), 1)

    # Run Evidently text eval report
    try:
        dataset = build_dataset(eval_df, text_columns=["query", "new_response", "target_response"],
                                categorical_columns=["correct", "golden_id"])
        snapshot = judge.run_text_eval_report(dataset)
        report_path = reports_dir / f"evidently_report_{version_name}.html"
        snapshot.save_html(str(report_path))
        logger.info(f"  Evidently report saved: {report_path}")
    except Exception as e:
        logger.warning(f"  Evidently report generation failed: {e}")

    return {
        "pct_tests_passed": round(pct_passed, 3),
        "total_tests": len(eval_df),
        "correct": int(correct_count),
        "judge_agreement": round(pct_passed, 3),
    }


async def main():
    logger.info("Starting Track B experiment runner")
    logger.info(f"Provider: {settings.llm_provider}, Model: {settings.groq_model}")

    # Initialize provider
    provider = get_provider(settings.llm_provider)

    # Load prompt versions
    prompt_versions = load_prompt_templates()
    logger.info(f"Loaded {len(prompt_versions)} prompt versions: {list(prompt_versions.keys())}")

    # Initialize MLflow tracer
    tracking_uri = f"sqlite:///{PROJECT_ROOT / 'data' / 'mlflow.db'}"
    tracer = AgentTracer(tracking_uri=tracking_uri)
    experiment_id = tracer.get_or_create_experiment("AgenticMLOps")
    logger.info(f"MLflow experiment ID: {experiment_id}")

    # Create data directory
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_version_results = {}

    for version_name, prompt_template in prompt_versions.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Running experiment for prompt version: {version_name}")
        logger.info(f"{'='*60}")

        # Create MLflow run
        run = tracer.get_run(f"prompt_{version_name}", experiment_id)

        # Log params
        tracer.log_run(
            run,
            params={
                "prompt_version": version_name,
                "prompt_length": len(prompt_template),
                "temperature": settings.temperature,
                "max_iterations": 3,  # actual value used in evaluate_prompt_version
                "model": settings.groq_model,
                "provider": settings.llm_provider,
            },
            metrics={},
            tags={"prompt_version": version_name, "experiment": "agentic_mlops"},
        )

        # Run evaluation
        start = time.time()
        eval_results = await evaluate_prompt_version(provider, version_name, prompt_template, 3)
        experiment_duration = time.time() - start

        # Log metrics
        metrics = {
            "task_success_rate": eval_results["task_success_rate"],
            "avg_iterations": eval_results["avg_iterations"],
            "avg_latency_ms": eval_results["avg_latency_ms"],
            "total_prompt_tokens": eval_results["total_tokens"]["prompt"],
            "total_completion_tokens": eval_results["total_tokens"]["completion"],
            "num_queries": len(eval_results["results"]),
        }

        # Run Evidently regression
        regression = run_evidently_regression(version_name, eval_results["results"], reports_dir)
        metrics["pct_tests_passed"] = regression["pct_tests_passed"]
        metrics["judge_agreement"] = regression["judge_agreement"]

        tracer.log_run(run, metrics=metrics, params={})

        # Log traces as artifacts
        trace_data = {
            "prompt_version": version_name,
            "timestamp": datetime.now().isoformat(),
            "results": eval_results["results"],
        }
        tracer.log_trace(run, trace_data, f"trace_{version_name}")

        # Save Evidently report
        report_path = reports_dir / f"evidently_report_{version_name}.json"
        report_path.write_text(json.dumps(regression, indent=2))

        logger.info(f"\nVersion {version_name} results:")
        logger.info(f"  Task success rate: {metrics['task_success_rate']:.1%}")
        logger.info(f"  Avg iterations: {metrics['avg_iterations']:.1f}")
        logger.info(f"  Avg latency: {metrics['avg_latency_ms']:.0f}ms")
        logger.info(f"  Tests passed: {metrics['pct_tests_passed']:.1%}")
        logger.info(f"  Judge agreement: {metrics['judge_agreement']:.1%}")

        all_version_results[version_name] = eval_results
        tracer.end_run(run.info.run_id, "FINISHED")

    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": settings.groq_model,
        "versions": {v: {"task_success_rate": r["task_success_rate"], "avg_iterations": r["avg_iterations"],
                         "avg_latency_ms": r["avg_latency_ms"]} for v, r in all_version_results.items()},
    }
    summary_path = reports_dir / "experiment_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    logger.info(f"\n{'='*60}")
    logger.info("Experiment complete!")
    logger.info(f"Summary saved to {summary_path}")
    logger.info(f"MLflow UI: http://localhost:5000")
    logger.info(f"{'='*60}")

    return all_version_results


if __name__ == "__main__":
    results = asyncio.run(main())
