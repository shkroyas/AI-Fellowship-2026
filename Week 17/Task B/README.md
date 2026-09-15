# Track B: Agentic AI MLOps

## Overview

This project applies MLOps practices (MLflow tracking, Evidently monitoring, Airflow orchestration) to the W15/W16 agentic AI assistant.

## Quick Start

```bash
# Install dependencies
uv sync

# Configure API keys
cp .env.example .env  # Edit with your Groq/OpenRouter keys

# Start MLflow server
uv run mlflow server --backend-store-uri sqlite:///data/mlflow.db \
  --default-artifact-root ./data/mlruns --host 127.0.0.1 --port 5000

# Run the experiment
uv run python run_experiment.py
```

## Results

| Version | Task Success | Avg Latency | Tokens Used |
|---------|-------------|-------------|-------------|
| v1 (Baseline) | 100% | 37.7s | 4,237 |
| v2 (+ Tool enforcement) | 100% | 56.3s | 5,623 |
| v3 (+ Chain searches) | 100% | 58.8s | 6,472 |

**Winner: v1** — fastest and most token-efficient with identical success rate.

## Airflow DAG (Verified)

The nightly regression DAG was tested end-to-end:

```
start → run_harness → run_regression → check_threshold → log_success → end
```

```bash
# Test the DAG
airflow dags test nightly_regression 2026-09-15
# Output: All 6 tasks passed, PASS: Regression test passed with 100.0%
```

## Documentation

- [DOCUMENTATION.md](DOCUMENTATION.md) — Full report with sections a-d
- [reports/](reports/) — Evidently HTML reports
- [dags/nightly_regression_dag.py](dags/nightly_regression_dag.py) — Airflow DAG
- [screenshots/](screenshots/) — MLflow and Airflow evidence

## Project Structure

```
track-b-agentic/
├── pyproject.toml              # uv config
├── run_experiment.py           # Experiment runner
├── src/track_b/
│   ├── assistant/              # Migrated W16 code
│   ├── utils/                  # MLflow + Evidently wrappers
│   └── prompts/                # v1, v2, v3 prompt files
├── reports/                    # Evidently reports
├── dags/                       # Airflow DAGs
├── screenshots/                # Evidence files
└── data/                       # MLflow DB + artifacts
```
