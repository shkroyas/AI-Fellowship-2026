# W17 Task A — Telco Churn ML Pipeline (MLOps)

**Student:** Royas Shakya  
**Date:** September 14, 2026  
**Assignment:** Week 17 MLOps — Track A: Churn Prediction  
**Repository:** https://github.com/shkroyas/AI-Fellowship-2026  

---

## Executive Summary

Built a production-grade MLOps pipeline for Telco Customer Churn prediction featuring:
- **4 ML models** tracked in MLflow with full experiment comparison
- **Model registry** with staging → production alias transitions
- **FastAPI serving** endpoint for real-time predictions
- **Evidently AI monitoring** with data drift, target drift, and custom metrics
- **Apache Airflow DAG** for weekly drift detection and conditional retraining
- **Reproducible environment** using `uv` package manager

---

## 1. Environment & Reproducibility (uv)

### Setup
```bash
# Clone the repository
git clone https://github.com/shkroyas/AI-Fellowship-2026.git
cd AI-Fellowship-2026/w17-mlops/track-a-churn

# Install dependencies with uv
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

### Key Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| scikit-learn | 1.7.2 | ML models |
| mlflow | 3.3.3 | Experiment tracking |
| evidently | 0.7.23 | Data monitoring |
| fastapi | 0.121.3 | Model serving |
| uvicorn | 0.38.1 | ASGI server |
| apache-airflow | 2.10.5 | Workflow orchestration |
| pandas | 2.3.4 | Data manipulation |
| xgboost | 3.2.0 | Gradient boosting |

### File Structure
```
track-a-churn/
├── pyproject.toml              # uv project config
├── uv.lock                     # Locked dependencies
├── README.md                   # This file
├── data/
│   ├── raw/                    # Telco Churn dataset
│   └── mlflow.db              # MLflow tracking database
├── reports/                    # Evidently HTML/JSON reports
│   ├── data_drift.html         # Data drift report
│   ├── data_drift.json         # Data drift JSON
│   ├── target_drift.html       # Target drift report
│   ├── target_drift.json       # Target drift JSON
│   ├── airflow_drift_check.html # Airflow drift check
│   └── {model_name}/          # Per-model plots
├── screenshots/                # Evidence for submission
│   ├── MLFLOW_TRACKING_REPORT.md
│   ├── run_comparison.csv
│   └── airflow_dag_test_output.txt
├── dags/
│   └── churn_drift_dag.py     # Airflow DAG
├── src/track_a/
│   ├── data_prep.py           # Data loading & preprocessing
│   ├── train.py               # Training pipeline
│   ├── serve.py               # FastAPI serving
│   └── utils/
│       ├── mlflow_utils.py    # MLFlowLogger wrapper
│       └── evidently_reporter.py  # Evidently monitoring
└── notebook/
    └── churn_demo.ipynb       # Interactive walkthrough
```

---

## 2. Experiment Tracking (MLflow)

### Run Comparison Table

| Rank | Run | Accuracy | Precision | Recall | F1 | ROC-AUC | CV-F1 | Model Type |
|------|-----|----------|-----------|--------|-----|---------|-------|------------|
| 1 | lr_balanced | 0.7353 | 0.8027 | 0.7257 | **0.7623** | 0.8132 | 0.7511 | LogisticRegression |
| 2 | rf_deep_balanced | 0.7246 | 0.7817 | 0.7342 | 0.7572 | 0.7976 | 0.7516 | RandomForestClassifier |
| 3 | xgb_weighted | 0.7189 | 0.7758 | 0.7306 | 0.7525 | 0.8006 | 0.7510 | XGBClassifier |
| 4 | rf_balanced | 0.7211 | 0.7885 | 0.7148 | 0.7498 | 0.7987 | 0.7467 | RandomForestClassifier |

### Best Model: `lr_balanced`
- **F1 Score:** 0.7623
- **ROC-AUC:** 0.8132
- **CV-F1:** 0.7511 ± 0.0050
- **Why Logistic Regression?** Best F1 score among all models, balanced precision/recall, interpretable coefficients, and fast inference.

### How to View in MLflow UI
```bash
uv run mlflow ui --backend-store-uri sqlite:///src/data/mlflow.db
# Open http://127.0.0.1:5000
```

---

## 3. Model Registry

**Registered Model:** `ChurnClassifier`

| Alias | Version | Status |
|-------|---------|--------|
| @staging | 8 | READY |
| @production | 8 | READY |

### Transition Flow
```
Version 8 trained → Registered → @staging → @production
```

### How to Interact
```python
import mlflow
client = mlflow.MlflowClient()

# Get production model
model = client.get_model_version_by_alias("ChurnClassifier", "production")
print(f"Production model: version {model.version}")

# Load for serving
model = mlflow.pyfunc.load_model("models:/ChurnClassifier/production")
```

---

## 4. Model Serving (FastAPI)

### Start the Server
```bash
uv run uvicorn src.track_a.serve:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | POST | Predict churn for customer data |
| `/health` | GET | Health check |

### Example Request
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

### Example Response
```json
{
  "churn_probability": 0.72,
  "churn": true,
  "model_version": "8",
  "model_alias": "production"
}
```

---

## 5. Monitoring (Evidently AI)

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

### MLflow Artifact Logging
All Evidently reports are logged to MLflow as artifacts under the training run:
```
mlruns/{experiment_id}/{run_id}/artifacts/evidently_reports/
├── data_drift.html
├── data_drift.json
└── target_drift.html
```

---

## 6. Orchestration (Apache Airflow)

### DAG: `churn_drift_monitoring`

**Schedule:** `@weekly` (or trigger manually)

**Pipeline:**
```
start → check_drift → branch_on_drift → trigger_retrain OR log_no_action → end
```

### Tasks

| Task | Type | Description |
|------|------|-------------|
| `start` | EmptyOperator | Pipeline entry point |
| `check_drift` | PythonOperator | Runs Evidently DataDriftPreset on reference vs current data |
| `branch_on_drift` | BranchPythonOperator | Routes based on drift detection |
| `trigger_retrain` | PythonOperator | Runs `train.py` to retrain and re-register model |
| `log_no_action` | PythonOperator | Logs "no significant drift" |
| `end` | EmptyOperator | Pipeline exit point |

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
```

### Setup Instructions
```bash
# Install Airflow in separate venv (recommended)
uv venv /tmp/airflow-venv --python 3.12
source /tmp/airflow-venv/bin/activate
uv pip install apache-airflow==2.10.5 evidently pandas scikit-learn

# Initialize Airflow
export AIRFLOW_HOME=/tmp/airflow-home
mkdir -p $AIRFLOW_HOME
airflow db migrate

# Copy DAG
cp dags/churn_drift_dag.py $AIRFLOW_HOME/dags/

# Start scheduler and webserver
airflow scheduler &
airflow webserver -p 8080 &

# Trigger DAG manually
airflow dags trigger churn_drift_monitoring

# Test DAG locally
airflow dags test churn_drift_monitoring 2026-01-01
```

### Drift Detection Logic
1. Load reference (70%) and current (30%) from the dataset
2. Run `DataDriftPreset` via Evidently
3. If any columns flagged as drifted → retrain
4. Fallback: check if MonthlyCharges shifted > 5% (catches injected drift)
5. Report saved to `reports/airflow_drift_check.html`

---

## 7. Standard Workflow

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

## 8. Submission Checklist

- [x] **uv** — `pyproject.toml` + `uv.lock` committed
- [x] **MLflow tracking** — 4 models logged with full metrics
- [x] **Run comparison table** — `screenshots/run_comparison.csv`
- [x] **Model registry** — `ChurnClassifier` with alias transitions (staging → production)
- [x] **Evidently reports** — HTML/JSON reports committed
- [x] **Custom metrics** — Churn rate shift, MonthlyCharges shift
- [x] **MLflow artifact logging** — All reports logged to MLflow
- [x] **FastAPI serving** — `/predict` and `/health` endpoints
- [x] **Airflow DAG** — Weekly drift monitoring + conditional retraining
- [x] **DAG test** — All 5 tasks passed
- [x] **README** — Comprehensive documentation
- [x] **Screenshots/Evidence** — All artifacts in `screenshots/`

---

## 9. Files

```
track-a-churn/
├── pyproject.toml                          # uv project config
├── uv.lock                                 # Locked dependencies
├── README.md                               # This file
├── data/
│   ├── raw/WA_Fn-UseC_-Telco-Customer-Churn.csv  # Dataset
│   └── mlflow.db                          # MLflow tracking DB
├── reports/                                # Evidently reports
│   ├── data_drift.html
│   ├── data_drift.json
│   ├── target_drift.html
│   ├── target_drift.json
│   ├── airflow_drift_check.html
│   └── {model_name}/                      # Model plots
├── screenshots/                            # Submission evidence
│   ├── MLFLOW_TRACKING_REPORT.md
│   ├── run_comparison.csv
│   └── airflow_dag_test_output.txt
├── dags/
│   └── churn_drift_dag.py                 # Airflow DAG
├── src/track_a/
│   ├── data_prep.py                       # Data preprocessing
│   ├── train.py                           # Training pipeline
│   ├── serve.py                           # FastAPI serving
│   └── utils/
│       ├── mlflow_utils.py                # MLFlowLogger
│       └── evidently_reporter.py          # Evidently monitoring
└── notebook/
    └── churn_demo.ipynb                   # Interactive notebook
```

---

## How to Reproduce

```bash
# 1. Clone and setup
git clone https://github.com/shkroyas/AI-Fellowship-2026.git
cd AI-Fellowship-2026/w17-mlops/track-a-churn
uv sync

# 2. Run full pipeline
uv run python src/track_a/train.py

# 3. Start serving
uv run uvicorn src.track_a.serve:app --host 0.0.0.0 --port 8000

# 4. View MLflow UI
uv run mlflow ui --backend-store-uri sqlite:///src/data/mlflow.db

# 5. Test Airflow DAG
export AIRFLOW_HOME=/tmp/airflow-home
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
/tmp/airflow-venv/bin/airflow dags test churn_drift_monitoring 2026-01-01
```
