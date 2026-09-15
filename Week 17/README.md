# Week 17 — MLOps: Experiment Tracking, Monitoring & Orchestration

## Structure

```
Week 17/
├── Task A/          # IBM Telco Churn — sklearn/XGBoost MLOps pipeline
│   ├── src/track_a/ # data_prep.py · train.py · serve.py · utils/
│   ├── dags/        # churn_drift_dag.py (Airflow)
│   ├── reports/     # Evidently HTML + JSON + Airflow run artifacts
│   ├── screenshots/ # MLflow run comparison, registry export
│   ├── pyproject.toml · uv.lock
│   └── README.md    ← detailed docs for this track
├── Task B/          # Agentic assistant — prompt MLOps pipeline
│   ├── src/track_b/ # assistant/ · prompts/ · utils/
│   ├── dags/        # nightly_regression_dag.py (Airflow)
│   ├── reports/     # Evidently HTML + traces + verdicts
│   ├── screenshots/ # MLflow export, Evidently captures
│   ├── run_experiment.py
│   ├── pyproject.toml · uv.lock
│   └── README.md    ← detailed docs for this track
├── tests/           # unit + integration tests (both tracks)
├── THRESHOLD_POLICY.md   ← acceptance gates, drift thresholds, rationale
├── EXECUTION_STATUS.md   ← verified outcomes from fresh runs
├── airflow_execution.json ← both DAG task-state exports
└── README.md        ← this file
```

## Reproduction

```bash
# Track A — churn pipeline
cd "Week 17/Task A" && uv sync --locked
uv run python -m src.track_a.train       # train → track → register

# Track B — prompt experiments
cd "Week 17/Task B"
cp .env.example .env                      # add provider API key
uv sync --locked
uv run python run_experiment.py           # run 3 versions → judge → compare
```

## Results Summary

### Track A

| Model | CV F1 | Holdout F1 | ROC-AUC | Decision |
|---|---:|---:|---:|---|
| XGBoost weighted | **0.6341** | 0.6367 | **0.8443** | ✅ **Promoted** |
| RF deep balanced | 0.6293 | 0.6369 | 0.8413 | staging |
| RF balanced | 0.6326 | 0.6285 | 0.8430 | staging |
| LR balanced | 0.6283 | 0.6136 | 0.8416 | staging |

Airflow drift-check DAG: both branches executed. Injected +21.7% charge shift triggered retraining; undrifted split kept existing model.

### Track B

| Prompt | Combined pass rate | Eligible? |
|---|---:|---|
| v1 | 100% | ✅ Yes |
| v2 | 80% | ✅ Yes (at gate) |
| v3 | 40% | ❌ No |

Airflow nightly regression DAG: independent v3 run scored 60% → `alert_regression` fired.

## Acceptance Policy

See [THRESHOLD_POLICY.md](THRESHOLD_POLICY.md) — project-defined gates with rationale and action for each threshold.

## Completion Record

See [EXECUTION_STATUS.md](EXECUTION_STATUS.md) — authoritative record of what ran, what passed, and scope limits.
