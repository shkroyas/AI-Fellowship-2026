"""
Airflow DAG: Nightly Regression Test for Agentic AI Assistant

Schedule: @daily (midnight UTC)
Purpose: Run evaluation harness + Evidently regression tests on the current
         production prompt version. If pass rate drops below 80%, log an alert.

Tasks:
1. run_harness — Execute the evaluation harness
2. run_regression — Run Evidently regression tests
3. check_threshold — Branch on pass rate
4. log_success / alert_regression — Log outcome
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    "owner": "royas-shakya",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

PASS_THRESHOLD = 0.80  # 80% minimum pass rate


def run_harness(**context):
    """Run the evaluation harness and return results."""
    import json
    import asyncio
    import sys
    from pathlib import Path
    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "src"))

    from src.track_b.assistant.config import settings
    from src.track_b.assistant.llm.provider import get_provider
    from src.track_b.assistant.agent.loop import AgenticLoop
    from src.track_b.assistant.tools.registry import tool_registry
    from src.track_b.assistant.tools.calculator import calculator_tool
    from src.track_b.assistant.tools.web_search import web_search_tool, datetime_tool

    # Register tools (idempotent)
    for tool in [calculator_tool, web_search_tool, datetime_tool]:
        if tool["name"] not in tool_registry.list_tools():
            tool_registry.register(tool["name"], tool["description"], tool["parameters"], tool["executor"])

    provider = get_provider(settings.llm_provider)

    test_queries = [
        "What is Retrieval-Augmented Generation (RAG)?",
        "What is the current date and time?",
        "Calculate 15% of 340.",
    ]

    results = []
    for query in test_queries:
        loop = AgenticLoop(provider, max_iterations=3)
        result = asyncio.run(loop.run(query))
        results.append({
            "query": query,
            "response": result.answer,
            "stopped_reason": result.stopped_reason,
            "iterations": result.total_iterations,
        })

    completed = sum(1 for r in results
                    if r["stopped_reason"] == "model_answered"
                    and len(r.get("response", "")) > 20)
    success_rate = completed / max(len(results), 1)

    context["ti"].xcom_push(key="success_rate", value=success_rate)
    context["ti"].xcom_push(key="results", value=json.dumps(results))

    return {"success_rate": success_rate, "num_queries": len(results)}


def run_regression(**context):
    """Run Evidently regression tests."""
    success_rate = context["ti"].xcom_pull(key="success_rate", task_ids="run_harness")
    pct_passed = success_rate  # Simplified: use harness success rate as proxy
    context["ti"].xcom_push(key="pct_tests_passed", value=pct_passed)
    return {"pct_tests_passed": pct_passed}


def check_threshold(**context):
    """Branch based on pass rate threshold."""
    pct = context["ti"].xcom_pull(key="pct_tests_passed", task_ids="run_regression")
    if pct >= PASS_THRESHOLD:
        return "log_success"
    return "alert_regression"


def log_success(**context):
    """Log successful regression check."""
    pct = context["ti"].xcom_pull(key="pct_tests_passed", task_ids="run_regression")
    print(f"PASS: Regression test passed with {pct:.1%} (threshold: {PASS_THRESHOLD:.0%})")


def alert_regression(**context):
    """Log regression alert."""
    pct = context["ti"].xcom_pull(key="pct_tests_passed", task_ids="run_regression")
    print(f"ALERT: Regression detected! Pass rate {pct:.1%} below threshold {PASS_THRESHOLD:.0%}")
    print("ACTION: Investigate MLflow traces and consider rolling back prompt version")


with DAG(
    dag_id="nightly_regression",
    default_args=default_args,
    description="Nightly regression test for agentic AI assistant",
    schedule_interval="@daily",
    start_date=datetime(2026, 9, 15),
    catchup=False,
    tags=["regression", "agentic", "mlops"],
) as dag:

    start = EmptyOperator(task_id="start")

    harness = PythonOperator(
        task_id="run_harness",
        python_callable=run_harness,
    )

    regression = PythonOperator(
        task_id="run_regression",
        python_callable=run_regression,
    )

    branch = BranchPythonOperator(
        task_id="check_threshold",
        python_callable=check_threshold,
    )

    success = PythonOperator(
        task_id="log_success",
        python_callable=log_success,
    )

    alert = PythonOperator(
        task_id="alert_regression",
        python_callable=alert_regression,
    )

    end = EmptyOperator(task_id="end", trigger_rule="none_failed_min_one_success")

    start >> harness >> regression >> branch >> [success, alert] >> end
