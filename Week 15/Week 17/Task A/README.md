# Track A — IBM Telco Churn: MLOps Pipeline

## Overview

This track trains, registers, serves, and monitors a churn-prediction classifier on the IBM Telco Customer Churn dataset (7,043 rows, 26.5% positive rate). The full workflow covers: data → training → MLflow tracking → model registry → FastAPI serving → Evidently drift monitoring → Airflow orchestration.

---

## a. Environment & Reproducibility (uv)

**Problem uv solves here:** The three main ML libraries (scikit-learn, xgboost, evidently) each pin conflicting transitive dependencies. Without a lockfile, `pip install` resolves them differently on every machine. `uv.lock` pins every dependency down to its hash and ensures identical resolution on any machine.

**One-command reproduction from a clean clone:**
```bash
cd "Week 17/Task A"
uv sync --locked           # installs exact environment from uv.lock
uv run python -m src.track_a.train    # trains all 4 models + registers best
```

Python version is pinned to 3.12 via `.python-version`. No GPU required — all training runs in seconds on CPU.

---

## b. Experiment Tracking Strategy (MLflow)

**What was varied:** Four classifier families with class-imbalance handling.

| Model run | CV F1 (5-fold) | Holdout F1 | ROC-AUC |
|---|---:|---:|---:|
| `xgb_weighted` | **0.6341** | 0.6367 | **0.8443** |
| `rf_deep_balanced` | 0.6293 | 0.6369 | 0.8413 |
| `rf_balanced` | 0.6326 | 0.6285 | 0.8430 |
| `lr_balanced` | 0.6283 | 0.6136 | 0.8416 |

**Selection policy:** Rank by training CV F1 *within the current execution* only. This avoids selecting a winner by holdout ranking (which would inflate holdout metrics). CV F1 rewards balanced precision/recall on the minority churn class; plain accuracy is misleading on an imbalanced target.

**Why XGBoost won:** Highest CV F1 (0.6341) — the primary selection criterion — with the highest holdout ROC-AUC (0.8443). ROC-AUC checks useful discrimination across all classification cutoffs, not just at a single threshold.

**What was tracked per run:**
- Parameters: model family, class-weight strategy, `scale_pos_weight` (XGBoost), `n_estimators`, `max_depth`
- Metrics: accuracy, precision, recall, F1, ROC-AUC, CV F1 mean ± std
- Artifacts: confusion matrix, ROC curve, feature-importance plot, `features.json` (column list for serving)

All runs use timestamped names (`xgb_weighted_20260915_HHMMSS`) so re-running never collides with old run IDs. Full run export: [`screenshots/run_comparison.md`](screenshots/run_comparison.md).

**Acceptance gates (pre-promotion):**
- Training CV F1 ≥ 0.60 **and** holdout ROC-AUC ≥ 0.80
- XGBoost passed both → registered as `ChurnClassifier@production`
- Candidates below either floor stay in staging; existing production alias is retained

See [`../../THRESHOLD_POLICY.md`](../../THRESHOLD_POLICY.md) for gate rationale and actions.

---

## c. Monitoring & Drift Strategy (Evidently)

**Reference vs current:** The IBM dataset is split 70% reference / 30% current using `train_test_split` with `stratify=Churn`. Synthetic drift is then injected into the current split: MonthlyCharges +15, tenure -10, Contract skewed toward Month-to-month, 5% label flip.

**What was monitored:**
- **`DataDriftPreset`** — Jensen–Shannon distance per column; flags columns where distributions diverge
- **`DataSummaryPreset`** — summary statistics comparison
- **Custom metric `MonthlyChargesShift`** — absolute relative shift in mean MonthlyCharges with a 10% threshold test

**Report findings (injected drift):**
- MonthlyCharges mean: 64.95 → 82.96 (+21.7%) — **exceeds the 10% threshold → investigation/retraining triggered**
- Churn rate: 26.5% → 28.7% (+2.2 pp, +8.3% relative)
- Contract distribution drifted toward Month-to-month
- Drift reports saved as HTML: [`reports/data_drift.html`](reports/data_drift.html), [`reports/target_drift.html`](reports/target_drift.html)

**Action when drift threshold is crossed:**
- ≥10% MonthlyCharges shift: investigate the changed batch, trigger the Airflow retraining branch
- Retraining still must pass CV F1 ≥ 0.60 and ROC-AUC ≥ 0.80 before the production alias is updated

---

## d. Orchestration (Airflow)

**DAG:** `churn_drift_monitoring` — `@weekly` schedule, manual trigger for testing.

```
start → check_drift → branch_on_drift → trigger_retrain OR log_no_action → end
```

- **`check_drift`**: Loads data, runs Evidently `DataDriftPreset`, checks MonthlyCharges shift against 10% threshold; saves HTML report to `reports/airflow_drift_check.html`
- **`branch_on_drift`**: If drift detected → `trigger_retrain`; otherwise → `log_no_action`
- **`trigger_retrain`**: Calls `train.py` as a subprocess; retraining must pass acceptance gates before production promotion

**Executed outcomes:**
- Undrifted 70/30 split: `log_no_action` branch triggered — correct, no spurious retraining
- Injected-drift run: `trigger_retrain` branch triggered; XGBoost passed gates and was promoted
- Airflow task states: [`../../airflow_execution.json`](../../airflow_execution.json)

---

## Quick Start

```bash
# 1. Install environment
cd "Week 17/Task A"
uv sync --locked

# 2. Train all 4 models (creates MLflow runs + registers best)
uv run python -m src.track_a.train

# 3. View results in MLflow UI
uv run mlflow ui --backend-store-uri sqlite:///data/mlflow.db
# → http://localhost:5000

# 4. Start the serving API (requires MLflow server at :5000)
uv run uvicorn src.track_a.serve:app --port 1234
# → http://localhost:1234/docs

# 5. Run Airflow DAG manually
airflow dags test churn_drift_monitoring 2026-09-15
```

---

## Deliverables Checklist

| Item | Location |
|---|---|
| `pyproject.toml` + `uv.lock` | [`pyproject.toml`](pyproject.toml), [`uv.lock`](uv.lock) |
| MLflow run comparison (all 4 models) | [`screenshots/run_comparison.md`](screenshots/run_comparison.md) |
| Registry stage transitions | [`screenshots/registry_export.json`](screenshots/registry_export.json) |
| Evidently HTML reports | [`reports/data_drift.html`](reports/data_drift.html), [`reports/target_drift.html`](reports/target_drift.html) |
| Airflow DAG | [`dags/churn_drift_dag.py`](dags/churn_drift_dag.py) |
| Airflow execution evidence | [`../../airflow_execution.json`](../../airflow_execution.json) |
| Acceptance threshold policy | [`../../THRESHOLD_POLICY.md`](../../THRESHOLD_POLICY.md) |
| Training source | [`src/track_a/train.py`](src/track_a/train.py) |
| Serving source | [`src/track_a/serve.py`](src/track_a/serve.py) |
