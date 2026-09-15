# W17 Task A — Telco Churn ML Pipeline (MLOps)

**Student:** Royas Shakya  
**Date:** September 14, 2026  
**Assignment:** Week 17 MLOps — Track A: Churn Prediction  
**Repository:** [AI-Fellowship-2026/Week 17/Task A](https://github.com/shkroyas/AI-Fellowship-2026/tree/main/Week%2017/Task%20A)

---

## 1. Overview

Built a production-grade MLOps pipeline for Telco Customer Churn prediction with:

| Component | Implementation |
|-----------|---------------|
| **Reproducible Environment** | `uv` with `pyproject.toml` + `uv.lock` |
| **Experiment Tracking** | MLflow — 4 models, full metrics comparison |
| **Model Registry** | `ChurnClassifier` with `@staging` → `@production` aliases |
| **Model Serving** | FastAPI `/predict` + `/health` endpoints |
| **Drift Monitoring** | Evidently AI — data drift, target drift, custom metrics |
| **MLflow Artifacts** | All reports logged to MLflow runs |
| **Orchestration** | Apache Airflow DAG — weekly drift check + conditional retrain |

---

## 2. Repository Structure

```
Week 17/Task A/
├── pyproject.toml                          # uv project config
├── uv.lock                                 # Locked dependencies
├── README.md                               # This file
├── data/
│   └── raw/WA_Fn-UseC_-Telco-Customer-Churn.csv   # 7,043 rows
├── reports/
│   ├── data_drift.html                     # Data drift report (Evidently)
│   ├── data_drift.json                     # Data drift JSON
│   ├── target_drift.html                   # Target drift report
│   ├── target_drift.json                   # Target drift JSON
│   ├── airflow_drift_check.html            # Airflow drift check report
│   ├── lr_balanced/                        # Logistic Regression plots
│   │   ├── lr_balanced_confusion.png
│   │   └── lr_balanced_roc.png
│   ├── rf_balanced/                        # Random Forest plots
│   │   ├── rf_balanced_confusion.png
│   │   ├── rf_balanced_features.png
│   │   └── rf_balanced_roc.png
│   ├── rf_deep_balanced/                   # Deep RF plots
│   │   ├── rf_deep_balanced_confusion.png
│   │   ├── rf_deep_balanced_features.png
│   │   └── rf_deep_balanced_roc.png
│   └── xgb_weighted/                       # XGBoost plots
│       ├── xgb_weighted_confusion.png
│       ├── xgb_weighted_features.png
│       └── xgb_weighted_roc.png
├── screenshots/
│   ├── MLFLOW_TRACKING_REPORT.md           # Full MLflow report
│   ├── run_comparison.csv                  # Model comparison CSV
│   ├── run_comparison.md                   # Model comparison markdown
│   └── airflow_dag_test_output.txt         # Airflow DAG test log
├── dags/
│   └── churn_drift_dag.py                  # Airflow DAG
├── src/
│   └── track_a/
│       ├── __init__.py
│       ├── data_prep.py                    # Data loading & preprocessing
│       ├── train.py                        # Training pipeline
│       ├── serve.py                        # FastAPI serving
│       └── utils/
│           ├── __init__.py
│           ├── mlflow_utils.py             # MLFlowLogger wrapper
│           └── evidently_reporter.py       # Evidently monitoring
└── notebook/
    └── churn_demo.ipynb                    # Interactive walkthrough
```

---

## 3. Setup & Installation

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/shkroyas/AI-Fellowship-2026.git
cd AI-Fellowship-2026/Week\ 17/Task\ A
```

### Step 2: Install Dependencies with uv

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### Step 3: Activate Virtual Environment

```bash
source .venv/bin/activate
```

### Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| scikit-learn | 1.7.2 | ML models (LogisticRegression, RandomForest) |
| xgboost | 3.2.0 | Gradient boosting model |
| mlflow | 3.3.3 | Experiment tracking & model registry |
| evidently | 0.7.23 | Data drift & monitoring reports |
| fastapi | 0.121.3 | REST API for model serving |
| uvicorn | 0.38.1 | ASGI server for FastAPI |
| pandas | 2.3.4 | Data manipulation |
| numpy | 2.3.5 | Numerical operations |
| apache-airflow | 2.10.5 | Workflow orchestration (optional) |

---

## 4. Running the Pipeline

### 4.1 Full Training Pipeline

```bash
uv run python src/track_a/train.py
```

**What it does:**
1. Loads and preprocesses the Telco Churn dataset
2. Trains 4 models with MLflow tracking:
   - Logistic Regression (balanced class weights)
   - Random Forest (balanced, default depth)
   - Random Forest (balanced, max_depth=15)
   - XGBoost (scale_pos_weight)
3. Logs all metrics, parameters, and artifacts to MLflow
4. Registers best model as `ChurnClassifier` with alias transitions
5. Runs Evidently drift detection (data drift + target drift)
6. Generates custom metrics (churn rate shift, MonthlyCharges shift)
7. Saves all reports to `reports/` and logs to MLflow

**Expected Output:**
```
Loading and preprocessing data...
  Train: (5634, 30), Test: (1, 30)
  Churn rate (train): 0.585
Training models...
  [lr_balanced]    Acc=0.7353  F1=0.7623  AUC=0.8132  CV-F1=0.7511±0.0050
  [rf_balanced]    Acc=0.7211  F1=0.7498  AUC=0.7987  CV-F1=0.7467±0.0061
  [xgb_weighted]   Acc=0.7189  F1=0.7525  AUC=0.8006  CV-F1=0.7510±0.0079
  [rf_deep_balanced] Acc=0.7246 F1=0.7572  AUC=0.7976  CV-F1=0.7516±0.0052
=== Run Comparison (sorted by F1) ===
Best model: lr_balanced
Registered model version 8 with alias 'staging'
Transitioned version 8 to alias 'production'
--- Evidently Monitoring ---
  Reports saved:
    Data Drift: reports/data_drift.html
    Target Drift: reports/target_drift.html
Done!
```

### 4.2 Start Model Serving

```bash
uv run uvicorn src.track_a.serve:app --host 0.0.0.0 --port 8000 --reload
```

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | POST | Predict churn for customer data |
| `/health` | GET | Health check (returns model version) |

**Example Request:**
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "gender": "Male",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "tenure": 12,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 70.5,
    "TotalCharges": 846.0
  }'
```

**Example Response:**
```json
{
  "churn_probability": 0.72,
  "churn": true,
  "model_version": "8",
  "model_alias": "production"
}
```

### 4.3 View MLflow UI

```bash
uv run mlflow ui --backend-store-uri sqlite:///data/mlflow.db
# Open http://127.0.0.1:5000
```

### 4.4 Run Airflow DAG (Optional)

```bash
# Install Airflow in separate venv (recommended to avoid dependency conflicts)
uv venv /tmp/airflow-venv --python 3.12
source /tmp/airflow-venv/bin/activate
uv pip install apache-airflow==2.10.5 evidently pandas scikit-learn

# Initialize Airflow
export AIRFLOW_HOME=/tmp/airflow-home
mkdir -p $AIRFLOW_HOME
airflow db migrate

# Copy DAG
cp dags/churn_drift_dag.py $AIRFLOW_HOME/dags/

# Test DAG locally
airflow dags test churn_drift_monitoring 2026-01-01

# Start scheduler and webserver (for production)
airflow scheduler &
airflow webserver -p 8080 &
```

---

## 5. Experiment Tracking (MLflow)

### Run Comparison

| Rank | Run | Accuracy | Precision | Recall | F1 | ROC-AUC | CV-F1 | Model Type |
|------|-----|----------|-----------|--------|-----|---------|-------|------------|
| 1 | lr_balanced | 0.7353 | 0.8027 | 0.7257 | **0.7623** | 0.8132 | 0.7511 | LogisticRegression |
| 2 | rf_deep_balanced | 0.7246 | 0.7817 | 0.7342 | 0.7572 | 0.7976 | 0.7516 | RandomForestClassifier |
| 3 | xgb_weighted | 0.7189 | 0.7758 | 0.7306 | 0.7525 | 0.8006 | 0.7510 | XGBClassifier |
| 4 | rf_balanced | 0.7211 | 0.7885 | 0.7148 | 0.7498 | 0.7987 | 0.7467 | RandomForestClassifier |

### Best Model: `lr_balanced`

- **F1 Score:** 0.7623 (highest among all models)
- **ROC-AUC:** 0.8132
- **CV-F1:** 0.7511 ± 0.0050 (stable cross-validation)
- **Why Logistic Regression?** Best F1 score, balanced precision/recall, interpretable coefficients, fast inference, handles class imbalance well with `class_weight="balanced"`

### How to View in MLflow

```python
import mlflow
from mlflow import MlflowClient

client = MlflowClient()

# List all runs
exp = client.get_experiment_by_name("TelcoChurn")
runs = client.search_runs(experiment_ids=[exp.experiment_id])
for run in runs:
    name = run.data.tags.get("mlflow.runName", run.info.run_id[:8])
    f1 = run.data.metrics.get("f1", 0)
    print(f"{name}: F1={f1:.4f}")

# Get production model
model = client.get_model_version_by_alias("ChurnClassifier", "production")
print(f"Production model: version {model.version}")
```

---

## 6. Model Registry

**Registered Model:** `ChurnClassifier`

| Alias | Version | Status |
|-------|---------|--------|
| @staging | 8 | READY |
| @production | 8 | READY |

### Transition Flow

```
train.py runs
  → Model trained (lr_balanced)
  → Registered as ChurnClassifier version 8
  → Alias set to @staging
  → Alias transitioned to @production
```

### How to Load Production Model

```python
import mlflow

# Load as scikit-learn
model = mlflow.sklearn.load_model("models:/ChurnClassifier/production")

# Load as pyfunc (generic)
model = mlflow.pyfunc.load_model("models:/ChurnClassifier/production")
```

---

## 7. Monitoring (Evidently AI)

### Reports Generated

| Report | Type | Size | Location |
|--------|------|------|----------|
| Data Drift | HTML | 4.27 MB | `reports/data_drift.html` |
| Data Drift | JSON | 6.4 KB | `reports/data_drift.json` |
| Target Drift | HTML | 3.69 MB | `reports/target_drift.html` |
| Target Drift | JSON | 0.99 KB | `reports/target_drift.json` |
| Airflow Drift Check | HTML | 4.27 MB | `reports/airflow_drift_check.html` |

### Custom Metrics

| Metric | Reference | Current | Shift |
|--------|-----------|---------|-------|
| Churn Rate | 0.585 | 0.580 | -0.86% |
| MonthlyCharges | $67.92 | $82.96 | +22.14% |

### How Monitoring Works

1. **Reference data:** 70% of original dataset (no drift)
2. **Current data:** 30% with injected drift (+15 MonthlyCharges, -10 tenure, Contract skew, 5% label flip)
3. **Evidently runs:** `DataDriftPreset` for column-level drift detection
4. **Custom metrics:** ChurnRateShift and MonthlyChargesShift
5. **MLflow logging:** All reports saved as artifacts under the training run

### How to Run Monitoring Separately

```python
import sys
sys.path.insert(0, "src")
from track_a.utils.evidently_reporter import EvidentlyReporter
from track_a.utils.mlflow_utils import MLFlowLogger
from track_a.data_prep import load_and_preprocess
import pandas as pd

# Load data
df = load_and_preprocess("data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv")
reference = df.sample(frac=0.7, random_state=42)
current = df.drop(reference.index)

# Create reporter
logger = MLFlowLogger(experiment_name="Monitoring")
reporter = EvidentlyReporter(logger)

# Generate reports
reporter.generate_reports(reference, current)
```

---

## 8. Apache Airflow Orchestration

### DAG: `churn_drift_monitoring`

**Schedule:** `@weekly` (or trigger manually)  
**Owner:** ml-team  
**Tags:** mlops, drift, churn

### Pipeline

```
start → check_drift → branch_on_drift → trigger_retrain OR log_no_action → end
```

### Tasks

| Task | Type | Description |
|------|------|-------------|
| `start` | EmptyOperator | Pipeline entry point |
| `check_drift` | PythonOperator | Loads reference/current data, runs Evidently `DataDriftPreset`, saves HTML report, returns drift boolean |
| `branch_on_drift` | BranchPythonOperator | Routes to `trigger_retrain` if drift detected, else `log_no_action` |
| `trigger_retrain` | PythonOperator | Runs `train.py` to retrain and re-register the model |
| `log_no_action` | PythonOperator | Logs "no significant drift" |
| `end` | EmptyOperator | Pipeline exit point (waits for either branch) |

### DAG Test Results (PASSED)

```
[INFO] starting task_id=start
[INFO] Marking task as SUCCESS. task_id=start
[INFO] starting task_id=check_drift
Drift detected: False
[INFO] Marking task as SUCCESS. task_id=check_drift
[INFO] starting task_id=branch_on_drift
[INFO] Marking task as SUCCESS. task_id=branch_on_drift
[INFO] starting task_id=log_no_action
[INFO] Marking task as SUCCESS. task_id=log_no_action
[INFO] starting task_id=end
[INFO] Marking task as SUCCESS. task_id=end
[INFO] Marking run successful
DagRun state: success
```

### Drift Detection Logic

1. Load reference (70%) and current (30%) from the dataset
2. Run `DataDriftPreset` via Evidently
3. If `DriftedColumnsCount` > 0 → retrain
4. Fallback: check if MonthlyCharges shifted > 5% (catches injected drift)
5. Report saved to `reports/airflow_drift_check.html`

### How to Test

```bash
# Using separate Airflow venv
export AIRFLOW_HOME=/tmp/airflow-home
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
/tmp/airflow-venv/bin/airflow dags test churn_drift_monitoring 2026-01-01
```

---

## 9. Standard Workflow

```
data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv
    ↓
data_prep.py (load, preprocess, one-hot encode, split)
    ↓
train.py (4 models with MLflow tracking)
    ↓
MLflow Experiment (params, metrics, artifacts per run)
    ↓
Model Registry (ChurnClassifier: staging → production)
    ↓
serve.py (FastAPI loads production model)
    ↓
evidently_reporter.py (drift detection, custom metrics)
    ↓
MLflow artifacts (reports logged to run)
    ↓
Airflow DAG (weekly drift check → conditional retrain)
```

---

## 10. Data

**Dataset:** Telco Customer Churn (synthetic, 7,043 rows)  
**Source:** Originally from Kaggle, generated synthetically with realistic feature-target correlations

### Features

| Feature | Type | Description |
|---------|------|-------------|
| gender | categorical | Male/Female |
| SeniorCitizen | numerical | 0/1 |
| Partner | categorical | Yes/No |
| Dependents | categorical | Yes/No |
| tenure | numerical | Months with company |
| PhoneService | categorical | Yes/No |
| MultipleLines | categorical | Yes/No/No phone service |
| InternetService | categorical | DSL/Fiber optic/No |
| OnlineSecurity | categorical | Yes/No/No internet service |
| OnlineBackup | categorical | Yes/No/No internet service |
| DeviceProtection | categorical | Yes/No/No internet service |
| TechSupport | categorical | Yes/No/No internet service |
| StreamingTV | categorical | Yes/No/No internet service |
| StreamingMovies | categorical | Yes/No/No internet service |
| Contract | categorical | Month-to-month/One year/Two year |
| PaperlessBilling | categorical | Yes/No |
| PaymentMethod | categorical | Electronic check/Mailed check/Bank transfer/Credit card |
| MonthlyCharges | numerical | Monthly charge amount |
| TotalCharges | numerical | Total charges |
| **Churn** | **target** | **Yes/No (encoded as 1/0)** |

### Preprocessing

1. `TotalCharges` converted to numeric, NaN filled with 0
2. `Churn` encoded: Yes → 1, No → 0
3. `customerID` dropped
4. Categorical features one-hot encoded via `pd.get_dummies()`
5. Train/test split: 80/20, stratified by Churn

---

## 11. Model Details

### Logistic Regression (Best Model)

| Parameter | Value |
|-----------|-------|
| class_weight | balanced |
| max_iter | 1000 |
| solver | lbfgs |
| C | 1.0 |

### Random Forest (Default)

| Parameter | Value |
|-----------|-------|
| class_weight | balanced |
| n_estimators | 100 |
| max_depth | None |
| random_state | 42 |

### Random Forest (Deep)

| Parameter | Value |
|-----------|-------|
| class_weight | balanced |
| n_estimators | 100 |
| max_depth | 15 |
| random_state | 42 |

### XGBoost

| Parameter | Value |
|-----------|-------|
| scale_pos_weight | 1.38 (handles imbalance) |
| n_estimators | 100 |
| max_depth | 6 |
| learning_rate | 0.1 |
| random_state | 42 |

---

## 12. Key Files Explained

### `src/track_a/train.py`
Main training pipeline. Handles data loading, model training, MLflow tracking, registry, and Evidently monitoring. Run with `uv run python src/track_a/train.py`.

### `src/track_a/serve.py`
FastAPI application. Loads the production model from MLflow registry and serves predictions. Run with `uv run uvicorn src.track_a.serve:app`.

### `src/track_a/data_prep.py`
Data loading and preprocessing. Handles CSV loading, type conversions, one-hot encoding, and train/test splitting.

### `src/track_a/utils/mlflow_utils.py`
MLFlowLogger wrapper class. Handles MLflow initialization, experiment creation, run logging, model registration, and artifact logging.

### `src/track_a/utils/evidently_reporter.py`
EvidentlyReporter class. Generates data drift reports, target drift reports, and custom metrics using Evidently AI. Logs all reports to MLflow.

### `dags/churn_drift_dag.py`
Airflow DAG definition. Defines the weekly drift monitoring pipeline with branching logic for conditional retraining.

---

## 13. Troubleshooting

### Issue: LR Convergence Warning
```
ConvergenceWarning: lbfgs failed to converge (status=1): STOP: TOTAL NO. of ITERATIONS REACHED LIMIT
```
**Solution:** Increase `max_iter` in train.py or scale features with `StandardScaler`.

### Issue: Airflow Import Errors
```
RuntimeError: The package `apache-airflow-providers-standard` needs Apache Airflow 2.11.0+
```
**Solution:** Use a separate venv for Airflow with compatible versions.

### Issue: Evidently API Differences
The API in evidently v0.7.23 differs from older versions. Key changes:
- Use `Report` and `Dataset` at top-level (not from submodules)
- `Report.run()` returns `Snapshot` (not `Report`)
- Use `snapshot.dict()` to get results (not `snapshot.as_dict()`)
- Metrics use `metric_name` key (not `metric`)

---

## 14. Submission Checklist

- [x] **uv** — `pyproject.toml` + `uv.lock` committed
- [x] **MLflow tracking** — 4 models logged with full metrics
- [x] **Run comparison table** — `screenshots/run_comparison.csv`
- [x] **Model registry** — `ChurnClassifier` with alias transitions (staging → production)
- [x] **Evidently reports** — HTML/JSON reports committed
- [x] **Custom metrics** — Churn rate shift, MonthlyCharges shift
- [x] **MLflow artifact logging** — All reports logged to MLflow
- [x] **FastAPI serving** — `/predict` and `/health` endpoints
- [x] **Airflow DAG** — Weekly drift monitoring + conditional retraining
- [x] **DAG test** — All 5 tasks passed successfully
- [x] **README** — Comprehensive documentation
- [x] **Screenshots/Evidence** — All artifacts in `screenshots/`
- [x] **Notebook** — Interactive walkthrough in `notebook/churn_demo.ipynb`

---

## 15. References

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Evidently AI Documentation](https://docs.evidentlyai.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [uv Package Manager](https://docs.astral.sh/uv/)
- [Telco Customer Churn Dataset](https://www.kaggle.com/blastchar/telco-customer-churn)
