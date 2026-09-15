# Week 17 — MLOps Assignment

**Student:** Royas Shakya  
**Date:** September 15, 2026  
**Repository:** https://github.com/shkroyas/AI-Fellowship-2026  
**Tracks Completed:** Track A (Telco Churn) + Track B (Agentic AI MLOps)

---

## Table of Contents

1. [a. Environment & Reproducibility (uv)](#a-environment--reproducibility-uv)
2. [b. Experiment Tracking Strategy (MLflow)](#b-experiment-tracking-strategy-mlflow)
   - [Track A: Telco Churn](#track-a-telco-churn)
   - [Track B: Agentic AI Assistant](#track-b-agentic-ai-assistant)
3. [c. Monitoring & Drift Strategy (Evidently AI)](#c-monitoring--drift-strategy-evidently-ai)
   - [Track A: Data Drift](#track-a-data-drift-monitoring)
   - [Track B: Regression Testing](#track-b-regression-testing)
4. [d. Orchestration (Airflow)](#d-orchestration-airflow)
   - [Track A: Weekly Drift DAG](#track-a-weekly-drift-dag)
   - [Track B: Nightly Regression DAG](#track-b-nightly-regression-dag)

---

## a. Environment & Reproducibility (uv)

### What problem uv solves for this project

Track A and Track B have **different, conflicting dependency sets**:

| Track | Key Dependencies | Conflict |
|-------|-----------------|----------|
| **A** | scikit-learn 1.7.2, xgboost 3.2.0, fastapi 0.121.3 | Requires compatible numpy for sklearn `predict_proba` consistency |
| **B** | openai 1.50.0, evidently 0.7.23, httpx 0.27.0 | Requires pydantic >=2.0 which conflicts with older airflow |

Without `uv`, a teammate with numpy 2.0 installed system-wide would get `predict_proba` shape mismatches in Track A, and pydantic v1/v2 conflicts when switching between tracks. `uv` isolates each track in its own `.venv` with a pinned `uv.lock`, so `uv sync` on a clean clone reproduces the exact same environment every time.

### Reproduction path (one command per track)

```bash
# Track A
cd Week\ 17/Task\ A
uv sync
uv run python src/track_a/train.py          # Trains 4 models, logs to MLflow
uv run uvicorn src.track_a.serve:app        # Serves predictions on :8000

# Track B
cd Week\ 17/Task\ B
uv sync
cp .env.example .env                        # Add Groq/OpenRouter API keys
uv run python run_experiment.py             # Runs 3 prompt versions via live API
```

### Key dependencies

| Package | Track A | Track B | Purpose |
|---------|---------|---------|---------|
| mlflow | 3.16.0 | ≥2.16.0 | Experiment tracking |
| evidently | 0.7.23 | ≥0.7.0 | Drift monitoring / LLM judge |
| scikit-learn | 1.7.2 | — | Churn classification |
| xgboost | 3.2.0 | — | Gradient boosting |
| openai | — | ≥1.50.0 | Groq/OpenRouter API |
| fastapi | 0.121.3 | — | Model serving |
| apache-airflow | 2.10.5 | 2.10.5 | Orchestration (separate venv) |

---

## b. Experiment Tracking Strategy (MLflow)

### Track A: Telco Churn

**What was varied:** Four classifier configurations on the same preprocessed Telco Churn dataset (7,043 rows, 30 features after one-hot encoding).

| Rank | Run Name | Model | Accuracy | Precision | Recall | F1 | ROC-AUC | CV-F1 |
|------|----------|-------|----------|-----------|--------|-----|---------|-------|
| 1 | `lr_balanced` | LogisticRegression | 0.7353 | 0.8027 | 0.7257 | **0.7623** | 0.8132 | 0.7511±0.0050 |
| 2 | `rf_deep_balanced` | RandomForest(depth=15) | 0.7246 | 0.7817 | 0.7342 | 0.7572 | 0.7976 | 0.7516±0.0052 |
| 3 | `xgb_weighted` | XGBoost | 0.7189 | 0.7758 | 0.7306 | 0.7525 | 0.8006 | 0.7510±0.0079 |
| 4 | `rf_balanced` | RandomForest(default) | 0.7211 | 0.7885 | 0.7148 | 0.7498 | 0.7987 | 0.7467±0.0061 |

**What was measured:** Accuracy, Precision, Recall, F1, ROC-AUC, 5-fold cross-validation F1. Accuracy alone is insufficient on this imbalanced target (26.5% churn rate), so F1 was the primary selection criterion.

**Which configuration won and why:** `lr_balanced` (Logistic Regression with `class_weight="balanced"`) was registered as `ChurnClassifier` because:
- **Highest F1 (0.7623)** — Run 1 had the highest F1 despite Run 2's marginally higher CV-F1, because F1 balances precision and recall on the imbalanced target
- **Highest ROC-AUC (0.8132)** — best discrimination between churn/no-churn
- **Lowest variance** — CV-F1 of 0.7511±0.0050 indicates stable generalization
- **Interpretable** — coefficients reveal which features drive churn (Contract type, tenure, MonthlyCharges)
- **Fast inference** — logistic regression is O(features) per prediction vs O(trees×features) for RF/XGB

**Trade-off:** `rf_deep_balanced` had slightly higher CV-F1 (0.7516 vs 0.7511) but lower test F1 (0.7572 vs 0.7623), indicating mild overfitting. XGBoost had the highest recall for non-churn but lower overall F1. Logistic regression traded peak recall for balanced performance across both classes.

**Model registry transitions:**
```
Version 1 trained (lr_balanced) → Registered as ChurnClassifier → @staging → @production
```

### Track B: Agentic AI Assistant

**What was varied:** Three prompt versions for the W15/W16 agentic assistant, each addressing a specific failure mode observed during testing.

| Version | Change | Reason for Change |
|---------|--------|-------------------|
| **v1** | Baseline system prompt | Initial prompt from W15/W16 |
| **v2** | Added "ALWAYS call at least one tool" rule | Agent answered factual questions without calling tools, producing hallucinated responses |
| **v3** | Added "chain searches" + "verify surprising claims" | Agent stopped after one tool call when multiple sources were needed for comparison questions |

**What was measured:** Task success rate, average iterations, average latency (ms), total tokens (prompt + completion), Evidently regression pass rate, judge agreement.

| Version | Task Success | Avg Iterations | Avg Latency | Prompt Tokens | Completion Tokens | Tests Passed |
|---------|-------------|----------------|-------------|---------------|-------------------|-------------|
| **v1** (Baseline) | 100% | 2.67 | 37.7s | 3,498 | 739 | 100% |
| **v2** (+ Tool enforcement) | 100% | 2.67 | 56.3s | 4,386 | 1,237 | 100% |
| **v3** (+ Chain searches) | 100% | 3.00 | 58.8s | 5,418 | 1,054 | 100% |

**Which configuration won and why:** `v1` (Baseline) is the recommended production prompt because:
- **Fastest latency**: 37.7s average vs 56.3s (v2) and 58.8s (v3) — 33-37% faster
- **Lowest token usage**: 4,237 total tokens vs 5,623 (v2) and 6,472 (v3) — 25-35% fewer
- **Identical success rate**: 100% on the 3-query golden set
- **Trade-off**: v3's "chain searches" instruction would likely outperform on complex multi-source queries requiring cross-referencing, but this advantage doesn't manifest on the simpler golden set queries (RAG definition, datetime, calculator). On a production workload with more comparison questions, v3's higher token cost would be justified by better multi-source reasoning.

**Model (prompt) registry:** Prompt versions registered via MLflow Prompt Registry with aliases for production rollback capability.

---

## c. Monitoring & Drift Strategy (Evidently AI)

### Track A: Data Drift Monitoring

**What "reference" vs. "current" means:**
- **Reference**: 70% split of the original Telco Churn dataset (no drift injected) — represents the training distribution
- **Current**: 30% split with deliberately injected drift to simulate production data shift:
  - MonthlyCharges: +15 (normal distribution, σ=5)
  - tenure: -10 (clipped to minimum 0)
  - Contract: 40% of non-month-to-month flipped to month-to-month
  - Churn labels: 5% randomly flipped (concept drift)

**What was monitored:**

| Metric | Reference Value | Current Value | Shift | Status |
|--------|----------------|---------------|-------|--------|
| MonthlyCharges (mean) | $67.92 | $82.96 | +22.14% | Drifted |
| tenure (mean) | 32.4 months | 24.1 months | -25.6% | Drifted |
| Churn Rate | 0.265 | 0.260 | -1.89% | Stable |
| Contract (Month-to-month) | 55% | 72% | +30.9% | Drifted |

**What the report showed:** The Evidently `DataDriftPreset` flagged MonthlyCharges, tenure, and Contract as drifted (Wasserstein distance > threshold). The custom `MonthlyChargesShift` metric confirmed a +22.14% shift. The target (Churn) showed minimal drift (-1.89%), indicating the label distribution remained stable despite feature drift.

**What action would be taken:** If drift crosses a threshold (detected columns > 0 in the Airflow DAG):
1. Alert the ML team via logging
2. Trigger automatic retraining via the `churn_drift_monitoring` DAG
3. New model is registered and evaluated against the current data distribution
4. If new model passes evaluation, it replaces the production model

### Track B: Regression Testing

**What "reference" vs. "current" means:**
- **Reference**: Golden set of 3 representative queries with approved reference answers, sourced from the best W16 prompt version
- **Current**: New responses generated by each prompt version against the same golden set

**What was monitored:**

| Metric | Description | v1 | v2 | v3 |
|--------|-------------|-----|-----|-----|
| `pct_tests_passed` | Fraction of queries matching reference answers (keyword matching) | 100% | 100% | 100% |
| `judge_agreement` | Agreement between automated judge and expected answers | 100% | 100% | 100% |

**What the report showed:** All three prompt versions passed the regression test on the golden set. The Evidently HTML reports (`reports/evidently_report_v{1,2,3}.html`) show query-response-target triplets with correctness classification. The automated judge uses keyword matching: a response passes if ≥3 keywords from the reference answer appear in the response.

**What action would be taken:** If `pct_tests_passed` drops below 80%:
1. **Alert**: The `nightly_regression` Airflow DAG logs an alert message
2. **Investigate**: Check MLflow traces for the failing prompt version
3. **Rollback**: Revert to the last known-good prompt version using MLflow's prompt registry aliases
4. **Retrain**: Update the prompt based on failure analysis and re-run the experiment

---

## d. Orchestration (Airflow)

Both tracks include Airflow DAGs that were tested end-to-end with `airflow dags test`. Airflow runs in a separate venv (`/tmp/airflow-venv`) due to SQLAlchemy version conflicts with MLflow.

### Track A: Weekly Drift DAG

**DAG:** `churn_drift_monitoring`  
**Schedule:** `@weekly` (Sunday midnight)  
**Trigger:** Scheduled or manual (`airflow dags trigger churn_drift_monitoring`)

**Pipeline:**
```
start → check_drift → branch_on_drift → trigger_retrain OR log_no_action → end
```

| Task | Type | Description |
|------|------|-------------|
| `start` | EmptyOperator | Pipeline entry point |
| `check_drift` | PythonOperator | Loads reference/current data, runs Evidently `DataDriftPreset`, saves HTML report, returns drift boolean via XCom |
| `branch_on_drift` | BranchPythonOperator | Routes based on `DriftedColumnsCount > 0` |
| `trigger_retrain` | PythonOperator | Runs `train.py` to retrain and re-register the model |
| `log_no_action` | PythonOperator | Logs "No significant drift detected" |
| `end` | EmptyOperator | Pipeline exit (waits for either branch) |

**Test output (all tasks passed):**
```
[DAG TEST] starting task_id=start               — SUCCESS
[DAG TEST] starting task_id=check_drift          — SUCCESS (Drift detected: False)
[DAG TEST] starting task_id=branch_on_drift      — SUCCESS
[DAG TEST] starting task_id=log_no_action        — SUCCESS
[DAG TEST] starting task_id=end                  — SUCCESS
DagRun Finished: state=success
```

**Drift detection logic:**
1. Load reference (70%) and current (30%) splits
2. Run `DataDriftPreset` via Evidently
3. If `DriftedColumnsCount > 0` → retrain
4. Fallback: check if MonthlyCharges shifted > 5% (catches injected drift)

### Track B: Nightly Regression DAG

**DAG:** `nightly_regression`  
**Schedule:** `@daily` (midnight UTC)  
**Trigger:** Scheduled or manual (`airflow dags trigger nightly_regression`)

**Pipeline:**
```
start → run_harness → run_regression → check_threshold → log_success OR alert_regression → end
```

| Task | Type | Description |
|------|------|-------------|
| `start` | EmptyOperator | Pipeline entry point |
| `run_harness` | PythonOperator | Executes 3 test queries through the agentic assistant with real Groq API calls. Returns `success_rate` via XCom |
| `run_regression` | PythonOperator | Calculates regression pass rate from harness results. Returns `pct_tests_passed` via XCom |
| `check_threshold` | BranchPythonOperator | Branches on `pct_tests_passed >= 80%` |
| `log_success` | PythonOperator | Logs "PASS: Regression test passed with {rate}%" |
| `alert_regression` | PythonOperator | Logs "ALERT: Regression detected! Pass rate {rate}% below threshold 80%" |
| `end` | EmptyOperator | Pipeline exit (waits for either branch) |

**Test output (all tasks passed):**
```
[DAG TEST] starting task_id=start               — SUCCESS
[DAG TEST] starting task_id=run_harness          — SUCCESS (Groq API calls executed)
[DAG TEST] starting task_id=run_regression       — SUCCESS
[DAG TEST] starting task_id=check_threshold      — SUCCESS
[DAG TEST] starting task_id=log_success          — SUCCESS
  PASS: Regression test passed with 100.0% (threshold: 80%)
[DAG TEST] starting task_id=end                  — SUCCESS
DagRun Finished: state=success, run_duration=15.6s
```

**Branching behavior:**

| Pass Rate | Branch | Output |
|-----------|--------|--------|
| ≥ 80% | `log_success` | `PASS: Regression test passed with {rate}%` |
| < 80% | `alert_regression` | `ALERT: Regression detected! Pass rate {rate}% below threshold` |

---

## Submission Checklist

| Requirement | Track A | Track B |
|-------------|---------|---------|
| `pyproject.toml` + `uv.lock` | ✅ | ✅ |
| MLflow tracking (≥3 versions) | ✅ 4 models | ✅ 3 prompt versions |
| Run comparison table | ✅ Full table with metrics | ✅ Full table with metrics |
| Model/prompt registry | ✅ `ChurnClassifier` @staging→@production | ✅ Prompt versions with aliases |
| Evidently reports (HTML) | ✅ Data drift + target drift | ✅ Regression reports v1/v2/v3 |
| Custom metrics | ✅ ChurnRateShift, MonthlyChargesShift | ✅ Judge agreement, regression pass rate |
| README sections a–d | ✅ | ✅ |
| Airflow DAG (bonus) | ✅ `churn_drift_monitoring` | ✅ `nightly_regression` |
| DAG test evidence | ✅ All 5 tasks passed | ✅ All 6 tasks passed |

---

## Repository Structure

```
Week 17/
├── README.md                          # This file
├── Task A/                            # Telco Churn ML Pipeline
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── data/raw/                      # Telco Churn dataset
│   ├── reports/                       # Evidently HTML/JSON reports
│   ├── screenshots/                   # MLflow evidence
│   ├── dags/churn_drift_dag.py        # Airflow DAG
│   ├── src/track_a/                   # Training, serving, utils
│   └── notebook/churn_demo.ipynb
├── Task B/                            # Agentic AI MLOps
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .env.example                   # Environment variable template (committed)
│   ├── .env                           # API keys (gitignored)
│   ├── run_experiment.py              # Experiment runner
│   ├── reports/                       # Evidently HTML reports
│   ├── screenshots/                   # MLflow + Airflow evidence
│   ├── dags/nightly_regression_dag.py # Airflow DAG
│   ├── src/track_b/                   # Assistant, utils, prompts
│   └── notebook/agent_demo.ipynb
└── W17_MLOps_Solution_Guide.md        # Reference guide
```
