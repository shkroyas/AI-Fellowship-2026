# Week 17 execution status — 15 September 2026

## Completed and verified

- Track A/B loggers create fresh timestamped MLflow runs.
- Track A trained four models on the IBM dataset (7,043 rows); fitted preprocessing is inside cross-validation and serving.
- Selection is training CV F1 within the current execution; production requires CV F1 ≥0.60 and holdout ROC-AUC ≥0.80. XGBoost passed those gates and is registered at `ChurnClassifier@production`.
- Holdout F1: 0.6367; ROC-AUC: 0.8443. See [run export](Task%20A/reports/training_summary.json).
- Evidently `MonthlyChargesShift` and its threshold test are in the HTML/JSON report.
- Serving probability matches the pipeline; category changes affect predictions.
- Airflow 2.10.5 was initialized and both Track A branches executed through manual scheduler triggers, including retraining. See [task states](airflow_execution.json).
- Track B source uses two live Evidently LLM judges, complete traces, stable-ID joins, numeric and negation checks, and explicit failure states.
- Seven regression/integration and gate tests pass; both track lockfiles sync successfully with `uv sync --locked --offline`.

## Fresh Track B comparison completed

The configured 20B model hit its daily quota; OpenRouter's configured upstream was overloaded. After authorization to switch, all three versions were rerun on Groq `openai/gpt-oss-120b`.

| Version | Run ID | Combined pass rate |
|---|---|---:|
| v1 | `3b0d1d94ab29444eb208a8cfb38fffb0` | 100% |
| v2 | `1d76c194477a4508bdb0ff06dbe85004` | 80% |
| v3 | `b9a8fdc27f0a4c90beca64d38ead7cfc` | 40% |

All 15 cases have both live judge verdicts/reasons, deterministic checks and full traces. HTML reports and MLflow metrics were independently cross-checked; see [verification](tests/fresh_run_verification.txt) and [result analysis](Task%20B/reports/RESULTS.md). These are observed results, including failures, not a claim of v3 improvement.

The manually triggered Track B DAG completed successfully. Its independent v3 run scored **60%**, below the 80% gate; `alert_regression` succeeded and `log_success` was skipped. See [scheduler task states](airflow_execution.json) and [DAG evaluation](Task%20B/reports/airflow/fresh_live_judges_20260915/experiment_summary.json). This confirms the workflow executes and handles a failed quality gate; it does not promote v3.

Fresh reports, screenshots, run exports, traces and documentation accompany this change. The injected-drift DAG was rerun after enforcing promotion floors; `fresh_gated_retrain_20260915` succeeded and its selected candidate passed both gates.

## Scope limits

Human-judge agreement is not measured without independent human labels. The suite does not demonstrate a migrated knowledge-base retrieval harness or production prompt registry. Injected drift is a simulation; its retraining uses the original labeled IBM dataset.

## Threshold rationale

[Threshold policy](THRESHOLD_POLICY.md) documents the chosen acceptance/drift levels and the action when each gate fails. These are project-defined choices, not fixed assignment requirements.
