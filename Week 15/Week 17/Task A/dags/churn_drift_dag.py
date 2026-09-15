"""Weekly drift gate; uses the track environment for monitoring and retraining."""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator

PROJECT_ROOT = Path(os.getenv('TRACK_A_ROOT', Path(__file__).resolve().parents[1]))


def check_drift(**context):
    conf = context['dag_run'].conf or {}
    output = PROJECT_ROOT / 'reports' / 'airflow' / context['run_id'].replace(':', '_')
    command = [str(PROJECT_ROOT / '.venv/bin/python'), '-m', 'src.track_a.check_drift', '--output', str(output)]
    if conf.get('inject_drift', False):
        command.append('--inject-drift')
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    verdict = json.loads((output / 'drift_verdict.json').read_text())
    context['ti'].xcom_push(key='drift_detected', value=verdict['drift_detected'])
    return verdict


def branch_on_drift(**context):
    return 'trigger_retrain' if context['ti'].xcom_pull(task_ids='check_drift', key='drift_detected') else 'log_no_action'


def trigger_retrain(**context):
    # Demonstration retraining uses the original labeled IBM training set.
    # An injected monitoring batch is not treated as new labeled training data.
    subprocess.run([str(PROJECT_ROOT / '.venv/bin/python'), 'src/track_a/train.py'],
                   cwd=PROJECT_ROOT, check=True)
    return 'Fresh training and CV-based selection completed'


with DAG('churn_drift_monitoring', schedule='@weekly', start_date=datetime(2026, 1, 1),
         catchup=False, tags=['mlops', 'drift']) as dag:
    check = PythonOperator(task_id='check_drift', python_callable=check_drift)
    branch = BranchPythonOperator(task_id='branch_on_drift', python_callable=branch_on_drift)
    retrain = PythonOperator(task_id='trigger_retrain', python_callable=trigger_retrain)
    no_action = EmptyOperator(task_id='log_no_action')
    check >> branch >> [retrain, no_action]
