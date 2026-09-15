# Week 17 — MLOps execution

[Current execution status](EXECUTION_STATUS.md) is the authoritative completion record.

- [Track A: IBM Telco churn](Task%20A/README.md) — fresh training, CV selection, real-probability serving, Evidently drift and executed Airflow branches.
- [Track B: agent evaluation](Task%20B/README.md) — three prompt variants, stable-ID regression, live correctness/grounding judges and isolated Airflow execution.
- [Airflow execution export](airflow_execution.json)
- [Regression test evidence](tests/verification.txt)

Each track has its own `pyproject.toml` and `uv.lock`; use `uv sync --locked`. Local MLflow SQLite databases/model stores are excluded from Git. Portable reports, run IDs, metrics, traces and task-state exports are the committed evidence. Historical audits describe earlier commits and are not current success claims.

## Acceptance policy

See the [project threshold policy](THRESHOLD_POLICY.md) for chosen thresholds, rationale, promotion decisions and monitoring actions. The numbers are project choices, not assignment-mandated targets.
