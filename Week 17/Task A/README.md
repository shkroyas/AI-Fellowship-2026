# Track A — IBM Telco churn

Train and monitor four classifiers on the IBM Telco data (7,043 rows). Every execution creates new timestamped MLflow runs. Production selection uses the highest training cross-validation F1 within that execution.

```bash
uv sync --locked
uv run python src/track_a/train.py
uv run uvicorn src.track_a.serve:app --port 8000
uv run mlflow ui --backend-store-uri sqlite:///data/mlflow.db
```

Training splits raw inputs first. A fitted sklearn pipeline learns scaling and one-hot encoding inside each training fold, then serves the same raw input schema. The API loads the exact registered `ChurnClassifier@production` version and uses `predict_proba`.

## Fresh evidence

- [Training summary, source dataset hash, run IDs and metrics](reports/training_summary.json)
- [Run comparison](screenshots/run_comparison.md)
- [Serving verification](reports/serving_verification.json)
- [Evidently data drift report](reports/data_drift.html)
- [Target drift report](reports/target_drift.html)
- [Airflow execution evidence](screenshots/airflow_dag_test_output.txt)

`MonthlyChargesShift` is an Evidently `SingleValueMetric` with its registered calculation and a `<10%` test. The demonstration monitoring batch deliberately shifts charges, tenure, contracts and labels; these changes are simulated, not evidence of observed business drift.

## Airflow

Use a separate Airflow 2.10.5 environment. Link the DAG into its DAG folder, or set `TRACK_A_ROOT` to this project when copying the DAG. Each task invokes this track's `.venv/bin/python` so Airflow dependencies stay isolated.

```bash
airflow dags unpause churn_drift_monitoring
airflow dags trigger churn_drift_monitoring
airflow dags trigger churn_drift_monitoring --conf '{"inject_drift":true}'
```

The default branch monitors an undrifted split. The injected example triggers a fresh training execution on the original labeled IBM data. This is orchestration evidence; it does not claim adaptation to a newly labeled production batch.

## Acceptance policy

See the [project threshold policy](../THRESHOLD_POLICY.md) for chosen thresholds, rationale, promotion decisions and monitoring actions. The numbers are project choices, not assignment-mandated targets.
