# W17 MLOps Assignment — Solution Guide
### Track A (Telco Churn) + Track B (Agentic MLOps on your W15/W16 assistant)

This guide turns the four session guides (uv → MLflow → Evidently → Airflow) and the W17
problem set into a concrete build plan, sequenced so each step only depends on what came
before it — same order the roadmap PDF recommends.

---

## 0. Compute strategy: do you actually need the RTX 4050?

Short answer: **no, and that's good news** — it means nothing here will fight your laptop.

| Track | What actually trains/runs | Compute profile |
|---|---|---|
| **A** | LogisticRegression / RandomForest / Gradient Boosting (or a tiny PyTorch MLP) on ~7,000 rows, ~20 columns | Seconds on CPU. Even a neural net variant finishes in under a minute on a laptop CPU. |
| **B** | Calls to a hosted LLM (Gemini/OpenAI-compatible endpoint) for tracing, prompt iteration, and LLM-as-judge scoring | Zero local compute — it's API round-trips. Your bottleneck is API rate limits, not GPU. |

So the RTX 4050 isn't a bottleneck-breaker here — nothing in this assignment is GPU-bound.
Where it **does** help is everything *around* the compute:

- **MLflow tracking server**, **Evidently's monitoring UI**, and an **Airflow scheduler** are all
  long-running local processes bound to `localhost`. Colab/Kaggle notebooks are ephemeral,
  don't persist a local server across sessions, and need ngrok-style tunneling tricks to expose
  `localhost:5000` — friction you don't need.
- You already have Ubuntu + `uv` + `rclone`/Drive configured. Staying local keeps one consistent
  environment for the whole pipeline (tracking → registry → serving → monitoring →
  orchestration) instead of splitting work between a notebook host and your machine.
- If you *do* want to show GPU literacy for extra polish in Track A (Section 3.4 below), the
  RTX 4050 (6 GB VRAM, mobile) is more than enough for a 2-hidden-layer MLP on tabular data —
  it'll be memory-idle the whole time.

**Recommendation: build both tracks locally, on Ubuntu, via `uv`.** Reserve Colab/Kaggle only as
a fallback if your environment breaks in a way you can't quickly fix (rare given `uv`'s
reproducibility guarantees), or if you want a shareable read-only notebook to send a teammate —
not because you need the compute.

---

## 1. Repository layout

The assignment lets you use one repo with two branches, or two repos. Given the tracks need
different dependency sets (Track A: `scikit-learn`/`xgboost`/`fastapi`; Track B:
`openai`/`evidently[llm]`), the cleanest local-dev setup is **one repo, two independent `uv`
projects as subfolders** — you get isolated lockfiles without branch-switching overhead, and it
still satisfies "single repo, organized clearly":

```
w17-mlops/
├── README.md                      # top-level: links to both tracks' READMEs
├── track-a-churn/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── data/
│   │   ├── raw/                   # Telco-Customer-Churn.csv
│   │   ├── mlflow.db
│   │   └── mlruns/
│   ├── reports/                   # Evidently HTML/JSON land here
│   ├── notebook/
│   │   └── churn_demo.ipynb
│   ├── src/track_a/
│   │   ├── utils/
│   │   │   ├── mlflow_utils.py    # MLFlowLogger
│   │   │   └── evidently_reporter.py
│   │   ├── data_prep.py
│   │   ├── train.py
│   │   └── serve.py               # optional FastAPI wrapper
│   ├── dags/
│   │   └── churn_drift_dag.py     # optional Airflow bonus
│   └── README.md
└── track-b-agentic/
    ├── pyproject.toml
    ├── uv.lock
    ├── data/
    │   ├── mlflow.db
    │   └── mlruns/
    ├── reports/
    ├── notebook/
    │   └── agent_demo.ipynb
    ├── src/track_b/
    │   ├── utils/
    │   │   ├── agent_tracer.py    # AgentTracer
    │   │   └── evidently_judge.py # EvidentlyJudge
    │   ├── assistant/             # your actual W15/W16 code, migrated
    │   └── prompts/               # prompt_v1.txt, prompt_v2.txt, prompt_v3.txt
    ├── dags/
    │   └── nightly_regression_dag.py  # optional Airflow bonus
    └── README.md
```

If your program specifically wants branches instead, keep the same internal structure per
branch (`main`/`track-a`, `track-b`) — nothing else changes.

---

## 2. Environment setup (both tracks)

```bash
# one-time, if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

mkdir -p w17-mlops/track-a-churn && cd w17-mlops/track-a-churn
uv init
uv python pin 3.11
uv add mlflow scikit-learn pandas numpy matplotlib evidently xgboost fastapi uvicorn jupyter python-dotenv
mkdir -p data reports notebook
```

```bash
cd ../.. && mkdir -p w17-mlops/track-b-agentic && cd w17-mlops/track-b-agentic
uv init
uv python pin 3.11
uv add mlflow openai "evidently[llm]" jupyter python-dotenv
# plus whatever your W15/W16 assistant already used (langchain/langgraph/chromadb/etc.)
mkdir -p data reports notebook src/track_b/prompts
```

Keep API keys in a local, git-ignored `.env`:

```bash
echo ".env" >> .gitignore
echo "data/" >> .gitignore     # mlflow.db + mlruns are large/binary, don't commit
echo "GEMINI_API_KEY=..." >> .env     # or OPENAI_API_KEY, matching whichever endpoint you use
```

Commit `pyproject.toml` and `uv.lock` for each track — that's your "one-command reproducible
setup" deliverable (`uv sync` from a clean clone).

**Start a local MLflow tracking server** (one per track, or share one server with two
experiments — simplest is one server per track folder so `data/mlflow.db` stays scoped):

```bash
mkdir -p data
uv run mlflow server --backend-store-uri sqlite:///data/mlflow.db \
  --default-artifact-root ./data/mlruns --host 127.0.0.1 --port 5000
```

Leave this running in its own terminal. Open `http://localhost:5000` to confirm.

---

## 3. Track A — Data Science MLOps (Telco Churn)

### 3.1 Data

Download `blastchar/telco-customer-churn` from Kaggle into `data/raw/`. Known quirk: the
`TotalCharges` column has blank strings for a handful of new customers (tenure = 0) — these need
explicit handling (impute as 0, or drop) before modeling; don't let `pd.to_numeric` silently coerce
them to `NaN` and leave them unhandled.

```python
import pandas as pd
df = pd.read_csv("data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv")
df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)
df["Churn"] = df["Churn"].map({"Yes": 1, "No": 0})
```

One-hot encode the categorical columns (`Contract`, `PaymentMethod`, `InternetService`, etc.),
drop `customerID`, then split with `stratify=df["Churn"]` since it's imbalanced (~27% churn).

### 3.2 `MLFlowLogger` utility

Build `src/track_a/utils/mlflow_utils.py` following the classic-ML session guide's pattern:
`MLFlowLogger` wraps `MlflowClient` with:

- `get_run(run_name, experiment_name, create_new=True)` — get-or-create a run by name
- `log_run(run, metrics, params, tags)` — batch-log a final snapshot
- `log_fold_wise(run, metrics, step)` — per-epoch curves, only needed if you add the optional MLP
- `log_artifact` / `load_artifact` — files (confusion matrix PNG, ROC curve PNG, Evidently HTML)
- `log_model(run, model, ...)` — logs any model (sklearn or PyTorch) wrapped in a uniform
  `ModelWrapper(mlflow.pyfunc.PythonModel)` that dispatches on `callable(model)` (PyTorch-style)
  vs. `.predict()` (sklearn-style)
- `register_model(name, model_uri, run_id, alias)` — creates the registered-model container if it
  doesn't exist, then creates a version and optionally assigns an alias

This is exactly the utility class described in your MLflow session guide — copy that
implementation in as your starting point and adapt it (it's dataset-agnostic).

### 3.3 A note on "Staging → Production"

The assignment text says "transition through at least two stages (e.g., Staging → Production)."
Current MLflow (and the session guides you have) use **aliases**, not the older
`transition_model_version_stage` stage API, which is deprecated. Satisfy the requirement with
aliases instead — it's functionally the same "movable label" concept the roadmap PDF describes:

```python
# after logging + registering your best run's model as version 1:
mlflow_logger.client.set_registered_model_alias("ChurnClassifier", alias="staging", version=1)
# later, once you're satisfied:
mlflow_logger.client.set_registered_model_alias("ChurnClassifier", alias="production", version=1)
```

Screenshot both alias assignments (or list them via `client.get_model_version_by_alias`) for your
README — that's your "stage transition" evidence. Mention in the README that you used the
alias mechanism because stage-based transitions are deprecated in the MLflow version you're on.

### 3.4 Training ≥3 models

Vary hyperparameters genuinely — not just the random seed. A clean 3-run spread:

1. `LogisticRegression(C=1.0, penalty="l2")` — baseline, fast, interpretable
2. `RandomForestClassifier(n_estimators=200, max_depth=8)` — different family
3. `RandomForestClassifier(n_estimators=500, max_depth=None)` or `XGBClassifier(...)` — a second
   tuning point or a third family

**Optional GPU-literacy run**: a small PyTorch MLP (2 hidden layers, as in the classic MLflow
guide's Section 16) as a 4th comparison point. To actually route it through CUDA:

```bash
uv add torch --index-url https://download.pytorch.org/whl/cu124
```
```python
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"   # should print "cuda" on your 4050
mlp.to(device)
```
Log `device` as a tag (`mlflow_logger.log_run(run, tags={"device": device, ...})`) — this is a nice
concrete way to show GPU awareness in the write-up even though it doesn't meaningfully change
training time on this dataset size.

For every run, log:
- **Params**: hyperparameters used
- **Metrics**: accuracy, precision, recall, F1, ROC-AUC (`sklearn.metrics`) — the assignment is
  explicit that accuracy alone is insufficient on this imbalanced target
- **Artifacts**: the model (`mlflow_logger.log_model`), confusion matrix PNG, ROC curve PNG
  (build with `sklearn.metrics.ConfusionMatrixDisplay` / `RocCurveDisplay`, save with
  matplotlib, then `mlflow_logger.log_artifact`)

Compare all runs in the MLflow UI's run-comparison table (or export it) — this table, with actual
numbers, is what your README's justification paragraph must reference (per the assignment's
explicit example format: *"Run 2 had the highest F1 (0.81)... because accuracy is misleading on
this imbalanced target"*).

### 3.5 Serving

Either the built-in server:
```bash
uv run mlflow models serve -m "models:/ChurnClassifier@production" -p 1234 --env-manager local
```
or a thin FastAPI wrapper (`src/track_a/serve.py`) that loads via
`mlflow.pyfunc.load_model("models:/ChurnClassifier@production")` in a startup hook and exposes a
`/predict` POST endpoint — do this version if you want a nicer deliverable to demo, since
`mlflow models serve` gives you a bare inference endpoint with no docs page.

### 3.6 Monitoring with `EvidentlyReporter`

Build `src/track_a/utils/evidently_reporter.py` following the Evidently data-science guide's
pattern: a `Dataset`/`DataDefinition` wrapper (`make_dataset`), a `data_quality_report`
(`DataSummaryPreset`), a `data_drift_report` (`DataDriftPreset`), a `classification_report`
(`ClassificationPreset`), a `run_test_suite` (any preset/metric with `include_tests=True`), plus
`save_html`/`save_json`.

**Reference vs. current split, with injected drift:**

```python
from sklearn.model_selection import train_test_split
reference_df, current_df = train_test_split(df, test_size=0.3, random_state=42, stratify=df["Churn"])

import numpy as np
rng = np.random.default_rng(42)
current_df = current_df.copy()
current_df["MonthlyCharges"] = current_df["MonthlyCharges"] + rng.normal(15, 5, size=len(current_df))
current_df["tenure"] = current_df["tenure"] + rng.normal(-10, 3, size=len(current_df)).clip(min=-current_df["tenure"])
# skew Contract toward month-to-month relative to its natural frequency
mtm_mask = current_df["Contract"] == "Month-to-month"
current_df.loc[current_df[~mtm_mask].sample(frac=0.4, random_state=1).index, "Contract"] = "Month-to-month"
# optional: flip 5% of labels to simulate label/concept drift
flip_idx = current_df.sample(frac=0.05, random_state=2).index
current_df.loc[flip_idx, "Churn"] = 1 - current_df.loc[flip_idx, "Churn"]

current_df["prediction"] = best_model.predict(current_df[feature_cols])   # predict on real (undrifted) features
reference_df["prediction"] = best_model.predict(reference_df[feature_cols])
```

**Data Drift report** — include `target` (`Churn`) as one of the columns Evidently sees (via
`make_dataset(..., target="Churn", prediction="prediction")`), and `DataDriftPreset` will flag it
alongside the feature columns — this is your "target drift" check; the current Evidently API
doesn't ship a separate `TargetDriftPreset`, so folding the target into the same drift report is the
documented equivalent.

**Custom metric**: adapt the guide's `MeanValueChangeMetric` pattern (a `SingleValueMetric` +
`SingleValueCalculation` subclass) to `MonthlyCharges`, or write a small custom calculation for
"churn rate shift within Month-to-month contracts specifically" — either satisfies "at least one
custom metric beyond built-in defaults."

**Save into MLflow**: after `evidently_reporter.save_html(drift_eval, "data_drift.html")`, log that
file as an MLflow artifact on the training run: `mlflow_logger.log_artifact(run,
"reports/data_drift.html", "evidently_reports")`.

Interpret the report in your README: which columns got flagged (should match what you
perturbed), what the p-values looked like, and what you'd do if this happened for real (retrain
trigger, alert, etc.) — this maps directly to the "Monitoring & Drift Strategy" README section.

### 3.7 Optional Airflow bonus

A DAG with two tasks: `check_drift` (loads reference/current, runs `run_test_suite(DataDriftPreset(),
...)`, pushes a boolean via XCom) → branch → `trigger_retrain` (calls your `train.py`) or
`log_no_action`. Use `BranchPythonOperator` on the drift boolean. Schedule with
`schedule_interval="@weekly"` for the writeup even if you only trigger it manually during grading.

---

## 4. Track B — Agentic AI MLOps (your W15/W16 assistant)

### 4.1 Migrate to `uv`

Move your existing W15 assistant + W16 agentic feature code into `track-b-agentic/src/track_b/assistant/`,
and reconstruct its dependencies via `uv add` (whatever LLM SDK / framework / vector store you
used) so `pyproject.toml` + `uv.lock` capture it exactly.

### 4.2 `AgentTracer` utility

Build `src/track_b/utils/agent_tracer.py` on the Agentic MLflow guide's pattern — it's the GenAI
counterpart to `MLFlowLogger`:

- `get_run` / `search_runs` / `end_run` — same get-or-create pattern
- `enable_autolog(library)` — one line of tracing for whichever library backs your assistant
  (`"openai"`, `"langchain"`, `"langgraph"`, `"autogen"`, `"llama_index"` — match your W15/W16 stack)
- `log_agent` / `load_agent` — logs your assistant as a `ChatModel` via "Models from Code"
- `evaluate_agent` — wraps `mlflow.genai.evaluate()` with scorers
- `register_agent` / `load_registered_agent` — get-or-create registry pattern, same as Track A
- `register_prompt` / `load_prompt` / `set_prompt_alias` — Prompt Registry wrapper

### 4.3 Prompt versioning driven by traces, not guesses

This is the part of Track B that actually needs your own judgment, not boilerplate:

1. Register `prompt_v1` (your current W15/W16 system prompt) via `register_prompt`.
2. Trace every test query against it — either `mlflow.trace`/autolog (preferred, shows up in the UI
   next to the run) or your own structured `{step, tool, args, result, reasoning}` JSON per step, as
   the assignment allows either.
3. Read the traces. Find a concrete failure mode — e.g. the agent stopped searching after one tool
   call when it needed two, or misread a retrieved chunk, or looped without terminating.
4. Write `prompt_v2` as a direct response to that specific failure (not a speculative tweak), register
   it as a new version under the **same** prompt name (`register_prompt` auto-versions), re-run the
   same queries, re-trace.
5. Repeat once more for `prompt_v3`. You now have 3 versions, each with a documented reason for
   existing — this is what the "Experiment Tracking Strategy" README section needs to explain.

Save 2–3 representative traces per version as run artifacts (one clean success, one failure) —
either export via `mlflow.get_trace(trace_id)` → `.to_json()` and `log_artifact`, or, if you built your
own structured JSON logs, just log those files directly; the assignment is explicit that either
approach is fine.

### 4.4 Metrics per version

Pull from your W16 evaluation harness (whatever it already scores — task success rate, tool-call
correctness, step count, latency) plus anything new you think is worth tracking (e.g. token cost per
query, `pct_tests_passed` from Section 4.5 below). Log via `mlflow_logger`-style
`log_run(run, params={"prompt_version": "v2", "temperature": ..., "max_iterations": ...}, metrics={...})`.
Compare all 3 versions side by side in the MLflow UI, same as Track A's run comparison.

### 4.5 `EvidentlyJudge` — regression testing

Build `src/track_b/utils/evidently_judge.py` on the Evidently agentic-track guide's pattern:

- `build_dataset(df, text_columns, categorical_columns)`
- `add_reference_judge(...)` — `BinaryClassificationPromptTemplate`-based judge comparing a new
  response against an approved reference, for regression testing
- `add_open_ended_judge(...)` — reference-free quality checks (tone, verbosity, safety)
- `run_text_eval_report(dataset)` — summarizes every descriptor added
- `evaluate_judge_quality(...)` — sanity-checks the judge itself against a handful of your own
  manual labels

Build a small golden set (5–10 representative queries with an approved reference answer, sourced
from your best W16 prompt version). Whenever you change the prompt, re-run those same queries
through the new version, then judge `new_response` against `target_response` with:

```python
evidently_judge.add_reference_judge(
    eval_dataset,
    response_column="new_response",
    reference_column="target_response",
    criteria=(
        "An ANSWER is correct when it matches the REFERENCE in all facts and details, "
        "even if worded differently. Incorrect if it contradicts, adds unsupported claims, "
        "or omits details.\nREFERENCE:\n=====\n{target_response}\n====="
    ),
    target_category="incorrect",
    non_target_category="correct",
    alias="Correctness",
    tests=[eq("correct", column="Correctness", alias="Matches reference")],
)
```

Attach `TestSummary(success_all=True, alias="Regression check")`, run it after every prompt
change, and log the pass rate as an MLflow metric (`pct_tests_passed`) on that version's run —
this is what ties the regression signal into the same comparison table as your harness numbers.

Sanity-check the judge itself with `evaluate_judge_quality` against a handful of examples you
labeled by hand — note in the README whether the judge's verdicts matched your own reading.

### 4.6 Optional Airflow bonus

A nightly DAG: run the W16 harness → run the Evidently regression Test Suite → if
`pct_tests_passed` drops below a threshold, log/alert (or flag in a Slack-style message stub) that
the current production prompt version has regressed.

---

## 5. Documentation checklist (per track, per the rubric)

Each README needs, in your own words, grounded in your actual numbers:

- **a. Environment & Reproducibility** — what problem `uv` solves *for this project specifically*
  (e.g. "teammate had numpy 1.26 vs 2.0, broke sklearn's `predict_proba` shape"), and confirm
  `uv sync` from a clean clone actually works.
- **b. Experiment Tracking Strategy** — what you varied and why, what you measured, which
  configuration won and the trade-off. **Track A**: must include the full run-comparison table (not
  just the winner) and cite the specific numbers that justified your registration choice.
- **c. Monitoring & Drift Strategy** — what "reference" vs. "current" means in your setup, what you
  monitored, what the report showed, what action you'd take on a real threshold breach.
- **d. Orchestration** — only if you did the Airflow bonus: schedule, trigger condition, what
  happens on a positive signal.

---

## 6. Submission checklist

- [ ] GitHub link(s) — one repo (two folders/branches) or two repos
- [ ] `pyproject.toml` + `uv.lock` committed for each track
- [ ] MLflow run-comparison screenshots/exports for both tracks, ≥3 versions each
- [ ] Registered model (Track A) with two alias transitions documented
- [ ] Evidently HTML reports for both tracks, committed or linked
- [ ] READMEs covering sections a–d above
- [ ] Airflow DAG file(s), if attempted

---

## 7. Pitfalls worth knowing up front (pulled from the guides' own callouts)

- **Jupyter `sys.path`**: every notebook needs the `project_root = Path.cwd().parent;
  sys.path.insert(...)` cell before `from src...` imports work — Jupyter's cwd is `notebook/`, not
  the project root.
- **Reusing an `artifact_path` in the same run silently overwrites** the previous model on a local
  filesystem artifact store — no warning. Give each logged model a distinct `artifact_path`.
- **`uv lock` vs. `uv sync` are separate steps** — updating the lockfile doesn't touch your
  installed environment until you `uv sync`.
- **Report paths are relative to the process's working directory** — if you run from inside
  `notebook/`, `reports/` resolves to `notebook/reports/`, not the project root's `reports/`, unless
  you account for it.
- **Gemini via the OpenAI-compatible endpoint still uses `mlflow.openai.autolog()`** — the library
  name for autologging tracks the SDK you're calling through, not the model provider.
- **A stray `"unknown"` verdict** from a judge template will break a binary
  `ClassificationPreset` check in `evaluate_judge_quality` — sanity-check value counts before
  running it (`scored_df["Correctness"].value_counts(dropna=False)`).
