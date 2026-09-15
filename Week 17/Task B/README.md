# Track B — prompt experiments and live regression evaluation

```bash
uv sync --locked
cp .env.example .env  # configure a provider key
LLM_PROVIDER=groq GROQ_MODEL=openai/gpt-oss-120b uv run python run_experiment.py
uv run mlflow ui --backend-store-uri sqlite:///data/mlflow.db
```

The runner compares v1, v2 and v3 on five stable-ID cases: RAG, datetime, calculator, Python practices and RAG/fine-tuning comparison. It records new MLflow run IDs, prompt hashes, full tool traces, completion rate, latency and token usage. Task success is the conjunction of termination, deterministic checks, and two actual Evidently LLM judges: reference-based correctness and grounding in captured tool evidence.

## Evidence

- [Execution status](../EXECUTION_STATUS.md)
- [Experiment summary](reports/experiment_summary.json)
- [v1 report](reports/evidently_report_v1.html), [v2 report](reports/evidently_report_v2.html), [v3 report](reports/evidently_report_v3.html)
- Per-case verdict JSON includes stable IDs, both judge labels/reasons, deterministic checks and the combined result.
- `judge_agreement` remains null until independent human labels are supplied. Pass rate is not human agreement.

Judge errors stop an evaluation and mark its MLflow run failed; they never fall back to keyword scoring. Raw responses are saved before evaluation so provider failures do not discard expensive agent outputs. Reports from failed or older executions must not be represented as fresh success evidence.

## Airflow

Use a separate Airflow 2.10.5 environment and link the DAG, or set `TRACK_B_ROOT` when copying it. The DAG invokes this track's Python environment, executes the live evaluator and branches at an 80% combined pass rate. The prompt version is explicit (default v3, Groq `openai/gpt-oss-120b`); this is not an MLflow production-prompt alias.

```bash
airflow dags unpause agentic_nightly_regression
airflow dags trigger agentic_nightly_regression --conf '{"prompt_version":"v3","provider":"groq","model":"openai/gpt-oss-120b"}'
```

`TRACK_B_VERSIONS=v1,v2,v3` controls runner versions; `TRACK_B_REPORTS` selects the output folder. All versions in a comparison must use the same model/configuration. Provider/model settings come from `.env` or environment variables.

## Limits

This suite exercises calculator, datetime and web search. It does not claim a migrated knowledge-base retrieval harness, validated cross-source retrieval, measured human-judge agreement, or a deployed prompt registry. Latency includes provider pacing and external search variability; a single run does not establish prompt-speed superiority.

## Acceptance policy

See the [project threshold policy](../THRESHOLD_POLICY.md) for chosen thresholds, rationale, promotion decisions and monitoring actions. The numbers are project choices, not assignment-mandated targets.
