"""
Airflow DAG: Weekly drift check + conditional retraining.

Schedule: @weekly (or trigger manually)
Logic:
  check_drift → branch → trigger_retrain OR log_no_action

Setup:
  pip install apache-airflow
  airflow db init
  airflow users create --username admin --role Admin --password admin -e admin@example.com -f Admin -l User
  airflow scheduler &  airflow webserver -p 8080 &

Place this file in ~/airflow/dags/ or set AIRFLOW__CORE__DAGS_FOLDER to this directory.
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator

# Add project root to path so we can import our modules
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def check_drift(**context):
    """Load reference/current data, run Evidently drift test suite.
    Returns True if significant drift is detected (trigger retraining).
    """
    import pandas as pd
    from evidently import DataDefinition, Dataset, Report
    from evidently.presets import DataDriftPreset

    data_dir = Path(PROJECT_ROOT) / "data" / "raw"
    csv_path = data_dir / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
    df = pd.read_csv(csv_path)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)
    df["Churn"] = df["Churn"].map({"Yes": 1, "No": 0})
    df = df.drop(columns=["customerID"])

    # Split 70/30
    from sklearn.model_selection import train_test_split
    reference, current = train_test_split(df, test_size=0.3, random_state=42, stratify=df["Churn"])

    # Detect drift using Evidently
    num_cols = [c for c in reference.columns if reference[c].dtype in ("int64", "float64")]
    cat_cols = [c for c in reference.columns if c not in num_cols]

    ref_ds = Dataset.from_pandas(reference, data_definition=DataDefinition(
        numerical_columns=num_cols, categorical_columns=cat_cols))
    cur_ds = Dataset.from_pandas(current, data_definition=DataDefinition(
        numerical_columns=num_cols, categorical_columns=cat_cols))

    report = Report(metrics=[DataDriftPreset(include_tests=True)])
    snapshot = report.run(current_data=cur_ds, reference_data=ref_ds)

    # Save report
    reports_dir = Path(PROJECT_ROOT) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    snapshot.save_html(str(reports_dir / "airflow_drift_check.html"))

    # Check if any drift was detected
    drift_detected = False
    try:
        results = snapshot.dict()
        metrics = results.get("metrics", [])
        for m in metrics:
            metric_name = m.get("metric_name", "")
            val = m.get("value", {})
            if "DriftedColumnsCount" in metric_name:
                count = val.get("count", 0) if isinstance(val, dict) else 0
                if count > 0:
                    drift_detected = True
                    print(f"Drift detected in {count} columns")
                    break
    except Exception as e:
        print(f"Error parsing drift results: {e}")
        drift_detected = True

    # If we couldn't detect drift from the report, use a simpler heuristic
    if not drift_detected:
        # Check MonthlyCharges shift (our injected drift)
        ref_mean = reference["MonthlyCharges"].mean()
        cur_mean = current["MonthlyCharges"].mean()
        pct_shift = abs(cur_mean - ref_mean) / ref_mean * 100
        if pct_shift > 5:  # 5% threshold
            drift_detected = True
            print(f"Drift detected: MonthlyCharges shifted {pct_shift:.1f}%")

    print(f"Drift detected: {drift_detected}")

    # Push result to XCom
    context["ti"].xcom_push(key="drift_detected", value=drift_detected)

    return drift_detected


def branch_on_drift(**context):
    """Branch: if drift detected, go to retrain; otherwise, log no action."""
    drift_detected = context["ti"].xcom_pull(
        task_ids="check_drift", key="drift_detected"
    )
    if drift_detected:
        return "trigger_retrain"
    return "log_no_action"


def trigger_retrain(**context):
    """Retrain the model by running the training script."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(Path(PROJECT_ROOT) / "src" / "track_a" / "train.py")],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr[-1000:]}")
        raise Exception(f"Training failed with return code {result.returncode}")
    return "Retraining complete"


def log_no_action(**context):
    """Log that no retraining is needed."""
    print("No significant drift detected. Model remains in production.")
    return "No action needed"


# DAG definition
with DAG(
    dag_id="churn_drift_monitoring",
    description="Weekly drift check + conditional retraining for Telco Churn model",
    schedule="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["mlops", "drift", "churn"],
    default_args={
        "owner": "ml-team",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
) as dag:

    start = EmptyOperator(task_id="start")

    check = PythonOperator(
        task_id="check_drift",
        python_callable=check_drift,
        doc="Runs Evidently DataDriftPreset on reference vs current data",
    )

    branch = BranchPythonOperator(
        task_id="branch_on_drift",
        python_callable=branch_on_drift,
        doc="Branches based on whether drift was detected",
    )

    retrain = PythonOperator(
        task_id="trigger_retrain",
        python_callable=trigger_retrain,
        doc="Retrains the model by running train.py",
    )

    no_action = PythonOperator(
        task_id="log_no_action",
        python_callable=log_no_action,
        doc="Logs that no retraining is needed",
    )

    end = EmptyOperator(task_id="end", trigger_rule="none_failed_min_one_success")

    start >> check >> branch >> [retrain, no_action] >> end
