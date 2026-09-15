"""Experiment runner for Track B — runs the assistant with each prompt version and logs to MLflow."""
import asyncio
import os
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
from src.track_b.utils.evidently_judge import EvidentlyJudge

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

TEST_QUERIES = GOLDEN_QUERIES


def load_prompt_templates():
    prompts_dir = PROJECT_ROOT / "src" / "track_b" / "prompts"
    versions = {}
    for v in os.getenv("TRACK_B_VERSIONS", "v1,v2,v3").split(","):
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


async def evaluate_prompt_version(provider, version_name: str, prompt_template: str, max_iterations: int = 3):
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating prompt version: {version_name}")
    logger.info(f"{'='*60}")

    results = []
    for tq in TEST_QUERIES:
        query_text = tq["query"]
        query_id = tq["id"]
        logger.info(f"  [{query_id}] {query_text[:60]}...")
        try:
            r = await run_single_query(provider, prompt_template, query_text, max_iterations)
            r["golden_id"] = query_id
            results.append(r)
            logger.info(f"  -> stopped={r['stopped_reason']}, iters={r['iterations']}, tools={r['tools_used']}")
        except Exception as e:
            logger.error(f"  -> FAILED: {e}")
            results.append({"query": query_text, "golden_id": query_id,
                            "response": f"Error: {e}", "iterations": 0,
                            "tokens": {}, "duration_ms": 0, "tools_used": [],
                            "stopped_reason": "error", "steps": []})
        await asyncio.sleep(5)  # Pace between queries

    # task_success = model reached a terminal answer (separate from correctness)
    completed = sum(1 for r in results if r["stopped_reason"] == "model_answered")
    task_success_rate = completed / max(len(results), 1)
    avg_iterations = sum(r["iterations"] for r in results) / max(len(results), 1)
    avg_latency_ms = sum(r["duration_ms"] for r in results) / max(len(results), 1)
    total_tokens = {"prompt": sum(r["tokens"].get("prompt_tokens", 0) for r in results),
                    "completion": sum(r["tokens"].get("completion_tokens", 0) for r in results)}

    return {
        "version": version_name,
        "prompt_length": len(prompt_template),
        "completion_rate": round(task_success_rate, 3),
        "avg_iterations": round(avg_iterations, 2),
        "avg_latency_ms": round(avg_latency_ms, 1),
        "total_tokens": total_tokens,
        "results": results,
    }


def run_evidently_regression(version_name, results, reports_dir):
    return EvidentlyJudge(reports_dir).evaluate(version_name, results, GOLDEN_QUERIES)


async def main():
    logger.info("Starting Track B experiment runner")
    logger.info("Provider: %s, Model: %s", settings.llm_provider, settings.groq_model if settings.llm_provider == "groq" else settings.openrouter_model)

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
    reports_dir = Path(os.getenv("TRACK_B_REPORTS", str(PROJECT_ROOT / "reports")))
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_version_results = {}
    execution_id = datetime.now().strftime("%Y%m%dT%H%M%S_%f")
    summary_path = reports_dir / "experiment_summary.json"
    if summary_path.exists():
        history = reports_dir / "history"
        history.mkdir(exist_ok=True)
        import shutil
        for old in list(reports_dir.glob("*.json")) + list(reports_dir.glob("*.html")):
            shutil.copy2(old, history / f"{execution_id}_{old.name}")
    summary_path.write_text(json.dumps({"execution_id": execution_id, "status": "running", "versions": {}}, indent=2))

    for version_name, prompt_template in prompt_versions.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Running experiment for prompt version: {version_name}")
        logger.info(f"{'='*60}")

        # Create MLflow run
        run = tracer.get_run(f"prompt_{version_name}", experiment_id)

        try:
            # Log params
            tracer.log_run(
                run,
                params={
                    "prompt_version": version_name,
                    "prompt_length": len(prompt_template),
                    "execution_id": execution_id,
                    "prompt_sha256": __import__("hashlib").sha256(prompt_template.encode()).hexdigest(),
                    "temperature": settings.temperature,
                    "max_iterations": 3,  # actual value used in evaluate_prompt_version
                    "model": (settings.groq_model if settings.llm_provider == "groq" else settings.openrouter_model),
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
                "completion_rate": eval_results["completion_rate"],
                "avg_iterations": eval_results["avg_iterations"],
                "avg_latency_ms": eval_results["avg_latency_ms"],
                "total_prompt_tokens": eval_results["total_tokens"]["prompt"],
                "total_completion_tokens": eval_results["total_tokens"]["completion"],
                "num_queries": len(eval_results["results"]),
            }

            # Preserve costly live outputs even if judge/report generation fails.
            (reports_dir / f"trace_{version_name}.json").write_text(json.dumps(eval_results, indent=2))
            tracer.log_trace(run, eval_results, f"trace_{version_name}")
            # Run Evidently regression
            regression = await asyncio.to_thread(run_evidently_regression, version_name, eval_results["results"], reports_dir)
            metrics["pct_tests_passed"] = regression["pct_tests_passed"]
            metrics["task_success_rate"] = regression["pct_tests_passed"]

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


            eval_results.update(run_id=run.info.run_id, regression=regression,
                                task_success_rate=regression["pct_tests_passed"])
            for artifact in reports_dir.glob(f"*{version_name}.*"):
                tracer.client.log_artifact(run.info.run_id, str(artifact), "evaluation")
            (reports_dir / f"trace_{version_name}.json").write_text(json.dumps(trace_data, indent=2))
            all_version_results[version_name] = eval_results
            summary_path.write_text(json.dumps({"execution_id": execution_id, "status": "running",
                "versions": all_version_results}, indent=2))
            tracer.end_run(run.info.run_id, "FINISHED")
        except BaseException as exc:
            summary_path.write_text(json.dumps({"execution_id": execution_id, "status": "failed",
                "failed_version": version_name, "failed_run_id": run.info.run_id,
                "error_type": type(exc).__name__, "versions": all_version_results}, indent=2))
            tracer.end_run(run.info.run_id, "FAILED")
            raise

    # Save summary
    summary = {
        "execution_id": execution_id, "status": "finished",
        "timestamp": datetime.now().isoformat(),
        "model": (settings.groq_model if settings.llm_provider == "groq" else settings.openrouter_model),
        "versions": {v: {"run_id": r["run_id"], "regression": r["regression"], "task_success_rate": r["task_success_rate"], "avg_iterations": r["avg_iterations"],
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
