"""Execute a configured prompt with live Evidently judges in Track B's environment."""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator

PROJECT_ROOT = Path(os.getenv('TRACK_B_ROOT', Path(__file__).resolve().parents[1]))
PASS_THRESHOLD = .8


def run_harness(**context):
    conf = context['dag_run'].conf or {}
    version = conf.get('prompt_version', 'v3')
    if version not in ('v1', 'v2', 'v3'):
        raise ValueError('Unknown prompt version')
    output = PROJECT_ROOT / 'reports' / 'airflow' / context['run_id'].replace(':', '_')
    output.mkdir(parents=True, exist_ok=True)
    provider = conf.get('provider', 'groq')
    if provider not in ('groq', 'openrouter'):
        raise ValueError('Unsupported provider')
    env = dict(os.environ, TRACK_B_VERSIONS=version, TRACK_B_REPORTS=str(output), LLM_PROVIDER=provider, GROQ_MODEL=conf.get("model", "openai/gpt-oss-120b"))
    with (output / 'execution.log').open('w') as log:
        subprocess.run([str(PROJECT_ROOT / '.venv/bin/python'), 'run_experiment.py'],
                       cwd=PROJECT_ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    summary = json.loads((output / 'experiment_summary.json').read_text())
    rate = summary['versions'][version]['regression']['pct_tests_passed']
    context['ti'].xcom_push(key='pct_passed', value=rate)
    return {'report_dir': str(output), 'prompt_version': version, 'pct_passed': rate}


def check_threshold(**context):
    rate = context['ti'].xcom_pull(task_ids='run_harness', key='pct_passed')
    return 'log_success' if rate >= PASS_THRESHOLD else 'alert_regression'


def alert_regression():
    print('Regression gate failed; prompt promotion is blocked. Review per-case verdicts.')


with DAG('agentic_nightly_regression', schedule='@daily', start_date=datetime(2026, 9, 15),
         catchup=False, tags=['mlops', 'regression']) as dag:
    harness = PythonOperator(task_id='run_harness', python_callable=run_harness)
    branch = BranchPythonOperator(task_id='check_threshold', python_callable=check_threshold)
    success = EmptyOperator(task_id='log_success')
    alert = PythonOperator(task_id='alert_regression', python_callable=alert_regression)
    harness >> branch >> [success, alert]
