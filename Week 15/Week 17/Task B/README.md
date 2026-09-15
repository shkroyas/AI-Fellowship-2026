# Track B — Agentic AI MLOps: Prompt Experiment & Regression Evaluation

## Overview

This track applies MLOps disciplines to a multi-tool agentic assistant (migrated from W15/W16). There is no "trained model" — instead tracking and monitoring are applied to prompt configurations, retrieval settings, and the evaluation metrics from the W16 harness. Three prompt versions were systematically compared using live Evidently LLM judges, full per-step traces, and an Airflow regression DAG.

---

## a. Environment & Reproducibility (uv)

**Problem uv solves here:** The assistant uses `ddgs` (web search), `openai`-compatible clients, `evidently[llm]`, `mlflow`, and `httpx`. These have interlocking version requirements that `pip` resolves non-deterministically across machines. `uv.lock` pins the exact version of all 200+ dependencies including their hashes.

**One-command reproduction from a clean clone:**
```bash
cd "Week 17/Task B"
cp .env.example .env        # add a Groq or OpenRouter API key
uv sync --locked            # installs exact environment from uv.lock
uv run python run_experiment.py   # runs all 3 prompt versions
```

Python version is pinned to 3.12. No GPU required — all LLM calls go to hosted APIs.

---

## b. Experiment Tracking Strategy (MLflow)

**What was varied:** Three explicit prompt versions stored as separate files in `src/track_b/prompts/`. Each iteration was a response to failures observed in the previous version's traces:

- **v1 (baseline):** Concise system prompt — tool use allowed, no explicit instruction on when to stop. Failure observed: stopped early on complex comparison queries.
- **v2 (iteration on v1 failure):** Added explicit step-limit guidance and output format requirements. Failure: longer prompts occasionally caused the model to over-search on simple questions.
- **v3 (iteration on v2 failure):** Structured reasoning prompt with mandatory tool-use acknowledgment. Failure: introduced latency and triggered clarification loops on some queries.

**Results (Groq `openai/gpt-oss-120b`, 3 iterations max, 5 test cases):**

| Version | MLflow Run ID | Combined pass rate | Eligible? |
|---|---|---:|---|
| v1 | `3b0d1d94ab29444eb208a8cfb38fffb0` | 100% | ✅ Yes |
| v2 | `1d76c194477a4508bdb0ff06dbe85004` | 80% | ✅ Yes (at gate) |
| v3 | `b9a8fdc27f0a4c90beca64d38ead7cfc` | 40% | ❌ No — below 80% gate |

**What was tracked per run:**
- Parameters: `prompt_version`, `prompt_length`, `model`, `temperature`, `max_iterations`, `num_test_cases`
- Metrics: `task_success_rate`, `avg_iterations`, `avg_latency_ms`, `pct_tests_passed`, `judge_agreement`, `prompt_tokens`, `completion_tokens`
- Artifacts: `prompt_v?.txt`, full step-by-step trace JSON (every tool call, arg, result, reasoning), per-case verdicts JSON, Evidently HTML report

All runs use timestamped names so re-running never reuses a run ID or conflicts with existing parameters. MLflow export: [`screenshots/mlflow_evidence.json`](screenshots/mlflow_evidence.json).

**Promotion gate:** Combined pass rate ≥ 80% required. v3 scored 40% and was not promoted. See [`../../THRESHOLD_POLICY.md`](../../THRESHOLD_POLICY.md).

---

## c. Monitoring & Regression Testing (Evidently)

**Golden set:** Five fixed queries covering distinct capabilities — RAG/knowledge, datetime tool, calculator tool, code best practices, and technique comparison. Each query has an approved reference answer from the best-performing prior version (v1).

**Two checks per response (both must pass for a case to count):**

1. **Reference-based correctness (Check 1 — Evidently `TextEvals`):** Runs Evidently's `TextEvals` preset on new vs reference responses. Captures text-level similarity and length distribution. A response that loses or contradicts reference information is flagged.

2. **Deterministic grounding check (Check 2 — `score_response_v2`):** Per-type evaluation using stable `golden_id` join:
   - `calculator_pct` → numeric comparison: extract final number, check within 1% tolerance of 51.0 (not just keyword "51")
   - `datetime_now` → actual date: must contain current date (ISO or natural language), not just the word "date"
   - `rag_basic`, `rag_vs_ft` → RAG answer: must contain required keywords AND must NOT contain negation phrases like "has no retrieval", "never uses"
   - `python_practices`, `rag_vs_ft` → general: required keywords present in response

**Why two checks:** A model can produce a fluent, long response that still fails to compute 51 or gives the wrong date. Check 1 catches semantic divergence; Check 2 catches factual/functional correctness. Both must pass.

**Report findings:**
- v1 (100%): All five cases passed both checks in the final run
- v2 (80%): `rag_vs_ft` failed after a provider tool-serialization error; both judges correctly rejected the failed-service response
- v3 (40%): Failed `datetime_now` (correctness judge required timezone), `python_practices` (omitted reference criteria), `rag_vs_ft` (provider error)

Each version has an Evidently HTML report: [`reports/evidently_report_v1.html`](reports/evidently_report_v1.html), [`reports/evidently_report_v2.html`](reports/evidently_report_v2.html), [`reports/evidently_report_v3.html`](reports/evidently_report_v3.html).

**Action when pass rate falls below 80%:**
- Log regression alert; block prompt promotion
- Inspect per-case verdicts JSON (`verdicts_v?.json`) to identify which queries failed and why
- Use failure trace to diagnose: did the model miss a tool call, misread a result, or stop early?
- Revise prompt in response to the specific failure (not a speculative tweak)

---

## d. Orchestration (Airflow)

**DAG:** `nightly_regression` — `@daily` schedule, manual trigger for testing.

```
start → run_harness → run_regression → check_threshold → log_success OR alert_regression → end
```

- **`run_harness`**: Runs all 5 golden queries through the current production prompt; logs `task_success_rate` and full result set to XCom
- **`run_regression`**: Applies `score_response_v2` with stable golden_id join to produce per-case verdicts; logs `pct_tests_passed`
- **`check_threshold`**: If `pct_tests_passed ≥ 0.80` → `log_success`; else → `alert_regression`
- **`alert_regression`**: Prints failure report with pass rate and recommended action (inspect traces, consider rollback)

**Executed outcome:**
- v3 was used as the production prompt for the DAG run
- Result: **60%** — below the 80% gate → `alert_regression` executed, `log_success` skipped
- This confirms the workflow correctly identifies a weak prompt and prevents auto-promotion
- DAG execution state: [`../../airflow_execution.json`](../../airflow_execution.json)
- Full DAG evaluation: [`reports/airflow/fresh_live_judges_20260915/`](reports/airflow/fresh_live_judges_20260915/)

---

## Trace Analysis (Diagnosis Driving Revisions)

Each prompt version has a full trace JSON saved: `reports/trace_v?.json`. Key trace observations:

| Version | Failure case | Trace diagnosis |
|---|---|---|
| v1 | None in final run | Clean success; datetime used `get_current_datetime` tool in iter 1, calculator used `calculator` in iter 1 |
| v2 | `rag_vs_ft` | Provider serialization error during tool call; trace shows tool result was empty string, model correctly abstained |
| v3 | `datetime_now` | Model returned correct date format but without timezone; judge required timezone → calibration issue exposed |
| v3 | `python_practices` | Model searched web but omitted "PEP" and "virtual" from response; trace shows retrieval succeeded but answer was incomplete |

---

## Quick Start

```bash
# 1. Install environment
cd "Week 17/Task B"
cp .env.example .env        # set GROQ_API_KEY=gsk_...
uv sync --locked

# 2. Run all 3 prompt versions
uv run python run_experiment.py

# 3. View results in MLflow UI
uv run mlflow ui --backend-store-uri sqlite:///data/mlflow.db
# → http://localhost:5000

# 4. Test Airflow DAG
airflow dags test nightly_regression 2026-09-15
```

---

## Deliverables Checklist

| Item | Location |
|---|---|
| `pyproject.toml` + `uv.lock` | [`pyproject.toml`](pyproject.toml), [`uv.lock`](uv.lock) |
| MLflow run comparison (all 3 versions) | [`screenshots/mlflow_evidence.json`](screenshots/mlflow_evidence.json) |
| Evidently HTML reports (3×) | [`reports/evidently_report_v1.html`](reports/evidently_report_v1.html) etc. |
| Full traces (3×) | [`reports/trace_v1.json`](reports/trace_v1.json) etc. |
| Per-case verdicts (3×) | [`reports/verdicts_v1.json`](reports/verdicts_v1.json) etc. |
| Airflow DAG | [`dags/nightly_regression_dag.py`](dags/nightly_regression_dag.py) |
| Airflow execution evidence | [`../../airflow_execution.json`](../../airflow_execution.json) |
| Result analysis | [`reports/RESULTS.md`](reports/RESULTS.md) |
| Acceptance threshold policy | [`../../THRESHOLD_POLICY.md`](../../THRESHOLD_POLICY.md) |
| Prompt files | [`src/track_b/prompts/`](src/track_b/prompts/) |
| Experiment runner | [`run_experiment.py`](run_experiment.py) |
