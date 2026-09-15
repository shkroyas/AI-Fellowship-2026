# Week 17 requirements, methodology, and evidence audit

**Reviewed: 15 September 2026. Verdict: not ready to submit as fully complete.**

The four main Track A training results reproduce exactly, but they were obtained on a dataset that does not match the required IBM Telco dataset. Track B has saved execution evidence, but its reported task success, regression success, judge agreement, and production recommendation are not valid quality conclusions. Several required components are missing or nonfunctional.

This is an audit, not an implementation repair. Original source, reports, datasets, and experiment stores were preserved. New executions and package environments were isolated under `/tmp/w17-audit-clean`.

## Scope and verification

Read the assignment PDF, the W17 solution guide, top-level project documentation, Week 16 project overview, both Week 17 READMEs and detailed documentation, both notebooks, training/serving/monitoring code, experiment runner, agent loop/provider/tools, DAGs, saved reports, comparison exports, local MLflow databases, and all nine saved Track B query traces.

The assignment PDF is the requirement authority; the solution guide is an implementation plan. The tracked submission is `Week 17/`. The untracked `w17-mlops/` development copy has matching relevant source/configuration/data files and additional local experiment evidence. Its presence on this computer does not make that evidence available in a GitHub submission.

Verification performed:

- Copied Git-tracked Week 17 files into isolated directories; both `uv sync --locked --offline` installations succeeded with Python 3.12.3 and the existing package cache. This verifies clean environments from committed files on this machine, not a fresh internet download or every OS/Python combination.
- Ran the complete Track A training, cross-validation, MLflow registration, and monitoring workflow in that isolated copy. It exited successfully and reproduced all four main metric rows.
- Loaded the original saved production model and reproduced its accuracy, F1, and ROC-AUC on the supplied CSV.
- Called the submitted prediction handler with the saved model and a valid request; it raised a feature-name mismatch.
- Called the actual Track B regression evaluator with deliberately wrong answers. It returned `pct_tests_passed=1.0`, `total_tests=1`, and `judge_agreement=1.0`.
- Inspected a generated Track B Evidently snapshot: one `RowCount()` metric and **zero tests**.
- Downloaded the public CSV from IBM's own repository and compared rows, labels, IDs, and hashes.
- Recalculated Track B aggregate latency, iterations, and token counts from its saved traces; these match the exported numbers.
- Reviewed existing Airflow execution logs. No new live LLM experiment or scheduled Airflow run was performed; no claim of independent provider-side verification is made.

Supporting files: [numeric evidence](audit/evidence.json), [full isolated training log](audit/track_a_clean_training.txt), [API failure probe](audit/track_a_serving_probe.txt), [wrong-answer evaluation probe](audit/track_b_probe.txt), [probe source](audit/probe.py), [reviewed source hashes](audit/source_sha256.json). A final hash check confirmed that all reviewed Git-tracked files remained unchanged.

## 1. Requirement coverage

“Partial” means that some implementation/evidence exists but the whole requirement is not satisfied.

| Requirement | Finding | Status |
|---|---|---|
| A: specified IBM Telco Customer Churn dataset | Supplied dataset differs completely in IDs and full non-ID rows | **Fail** |
| Both: committed `pyproject.toml` and `uv.lock` | Both present; isolated locked installations succeeded | **Pass** |
| A: at least three genuinely different model configurations | Four configurations; independently reproduced | **Pass on supplied data** |
| A: accuracy, precision, recall, F1, ROC-AUC per run | Present in MLflow and exports; independently reproduced | **Pass on supplied data** |
| A: hyperparameters, model, confusion matrix, ROC artifacts | Main four runs have logging code/local evidence; parameters not all recorded exactly | **Partial** |
| A: full run comparison and justified winner | Four main rows reproduce; historical rows are not a valid single comparison; dataset wrong | **Partial** |
| A: register winner and demonstrate lifecycle transitions | Local registry and fresh reproduction show staging/production aliases | **Pass using guide's alias interpretation** |
| A: serve registered model through API | Handler fails; probability output also incorrect | **Fail** |
| A: 70/30 reference/current split and synthetic drift | Implemented and reproduced, but on wrong source data | **Partial** |
| A: identify perturbed columns with Evidently | Correctly identifies tenure, MonthlyCharges, Contract on supplied data | **Pass on supplied data** |
| A: target drift or equivalent | Target `ValueDrift` report exists; stable marginal churn distribution | **Pass on supplied data** |
| A: custom metric using Evidently custom metric/test API | Plain Python calculations, not integrated Evidently metrics/tests | **Fail** |
| A: HTML reports saved to MLflow | Confirmed in isolated complete run | **Pass** |
| B: migrate W15 assistant plus W16 agentic feature | Agent subset exists; RAG, knowledge-search, API and W16 harness are missing | **Partial** |
| B: explicit prompt versions and at least three configuration runs | Three files, three saved runs, three queries each | **Pass** |
| B: full per-query trace, raw results and intermediate decisions | Results truncated; decisions and per-step token fields omitted from artifact serialization | **Partial** |
| B: representative traces available as MLflow artifacts | Three query records per local artifact, but trace directories are not Git-tracked | **Partial** |
| B: revisions respond to observed failures | Claimed diagnoses do not correspond to supplied traces | **Fail as documented** |
| B: meaningful version comparison including cost | Token/latency arithmetic correct; quality metric invalid and timing confounded | **Partial** |
| B: fixed representative golden regression set | Five references defined, three queries executed, only one matched for evaluation | **Fail** |
| B: Evidently LLM-as-judge with at least two checks | No actual judge execution or attached checks | **Fail** |
| B: regression suite after each change; failures gate promotion | Unconditional calculator pass; empty test suite; no promotion gate | **Fail** |
| B: log genuine suite pass/fail metric to MLflow | Logs a defective keyword score under that name | **Fail** |
| B: interpret individual failures and sanity-check judge | Failures obscured; agreement is copied from pass rate | **Fail** |
| Both: HTML report deliverables | HTML files tracked, but B reports do not implement the required evaluation | **A pass / B partial** |
| Both: implementation-specific documentation | Extensive, but significant incorrect claims and broken commands | **Partial** |
| Optional A: scheduled drift/retrain DAG | Schedule/branches exist; fixed undrifted split and only no-action execution evidenced | **Partial bonus** |
| Optional B: scheduled W16 evaluation/degradation alert | Schedule/branches exist; uses a three-query termination proxy, not W16 evaluation | **Partial bonus** |

The PDF says “at least two checks” although it only explicitly enumerates reference correctness. Implement a second distinct criterion and report both. The PDF discusses separate repos or feature branches; the guide permits two subfolders. Existing folder organization follows the guide, but it is not proof of literal branch-based submission compliance. Local inspection does not establish that GitHub is up to date.

## 2. Critical findings

### A1 — The required dataset has been replaced

Evidence: `Task A/data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv`, compared with [IBM's published CSV](https://github.com/IBM/telco-customer-churn-on-icp4d/blob/master/data/Telco-Customer-Churn.csv).

| Check | Submitted CSV | IBM CSV |
|---|---:|---:|
| Rows | 7,043 | 7,043 |
| Churn = Yes | 4,118 (58.47%) | 1,869 (26.54%) |
| Churn = No | 2,925 | 5,174 |
| First customer ID | `CUST-0000` | `7590-VHVEG` |
| Customer IDs shared between files | 0 | 0 |
| Entire non-ID rows shared between files | 0 | 0 |

This is not just different ordering or anonymized IDs. The provided file looks like a generated replacement, but its exact origin and the author's intent cannot be established from these files. Calling it the specified IBM dataset is incorrect. The PDF only authorizes synthetic drift in the **current monitoring split**, not replacement of the training dataset.

**Impact:** All Track A model-selection and drift numbers must be regenerated on the correct source before they support assignment completion. Preserve the existing results as an explicitly labeled experiment on the supplied replacement dataset.

### B1 — The 100% regression score can pass every wrong answer

Evidence: [run_experiment.py](Task%20B/run_experiment.py), lines 119–160; `reports/evidently_report_v*.json`.

1. Golden/test query wording differs. Substring matching drops the RAG and datetime queries. Only the calculator query reaches evaluation.
2. The calculator reference is `15% of 340 is 51.`. Every token has at most three characters, so filtering for words longer than three produces an empty list.
3. The condition becomes `0 >= min(3, 0)`, which is always true, even for an empty answer or `999`.
4. All saved regression JSON files confirm **one test**, not three or five.

I supplied deliberately wrong responses to all three queries and obtained:

```json
{"pct_tests_passed": 1.0, "total_tests": 1, "correct": 1, "judge_agreement": 1.0}
```

There is a second labeling bug: the report marks the first `correct` rows as correct instead of preserving each row's actual verdict. If multiple rows are evaluated, failures can be assigned to the wrong questions.

**Fix:** Join by stable test-case IDs, require complete coverage, store per-case verdicts, and fail on missing/empty/unscored cases. Add an exact numerical check for calculator output alongside the required LLM checks.

### B2 — There is no functioning LLM-as-judge Test Suite

Evidence: [evidently_judge.py](Task%20B/src/track_b/utils/evidently_judge.py), lines 28–66; runner lines 134–160.

`add_reference_judge` and `add_open_ended_judge` merely store dictionaries. They never attach or execute an evaluator. `LLMClassification` and `eq` are imported but unused. `Report(metrics=[TextEvals()])` has no evaluation descriptors or tests; the tested snapshot contains only a row count. `judge_agreement` is assigned the same value as the pass rate. The separate quality helper compares answer strings and ignores the manual-label argument, so it also does not measure agreement with human judgments.

The generated HTML files are not evidence of correctness judgments, judge reasoning, or regression tests. A local function named “judge” does not satisfy this requirement. [Evidently's judge example](https://docs.evidentlyai.com/examples/LLM_judge) demonstrates actual evaluator configuration and judge-quality evaluation.

**Fix:** Execute reference-based correctness plus a second explicit check, attach pass/fail conditions, save each verdict and explanation, and compare a manually labeled subset against the judge. Derive MLflow pass rate from those actual outcomes.

### B3 — “Task success” counts termination, including clear failures

Evidence: runner line 97; saved `trace_v1.json`, `trace_v2.json`, `trace_v3.json`.

Any `stopped_reason == "model_answered"` counts as success; correctness, successful tool use, and fulfillment are not checked. In v1, the date tool is called twice with the invalid argument `{"": ""}`. The final response says it cannot fetch the current date/time. This is counted as a successful task.

All versions' RAG query traces contain `Error: Web search unavailable; install ddgs.`. Thus “100% task success with correct tool usage” is false. At minimum v1 cannot exceed 2/3 on answer fulfillment; under the documented source-verification objective, its RAG answer also fails verification. This is not a substitute complete rescore; a declared rubric is needed for all versions.

**Fix:** Separate answer termination, task fulfillment, tool correctness, and evidence grounding. Reuse the W16 rubric/harness where appropriate. Withdraw the recommendation that v1 is the production winner with equal quality.

### A2 — The API cannot perform the documented inference

Evidence: [serve.py](Task%20A/src/track_a/serve.py), lines 30–73.

- Training expects 30 encoded features. The request schema omits several original inputs.
- `pd.get_dummies(..., drop_first=True)` on a single row removes every categorical column's only observed category. The resulting frame has only the three numeric fields.
- The comment about aligning training columns has no implementation.
- Calling the handler with the actual saved production model raised `ValueError: The feature names should match those that were passed during fit`.
- Even after fixing columns, `churn_probability` currently comes from the classifier's predicted class, not `predict_proba`. Its confidence will therefore be 1 for binary labels. The second `predict(..., params={"return_proba": True})` call does not implement a probability interface and its output is unused.
- The documented response fields `churn`, `model_version`, and `model_alias` do not match the actual response model.

**Fix:** Save a complete fitted preprocessing/classifier pipeline, accept the complete raw feature schema, and return actual positive-class probability through a supported model interface. Verify registry startup and prediction with a realistic request.

## 3. Other required-component and evidence gaps

### A3 — Custom calculations bypass Evidently's custom metric API

`ChurnRateShift` and `MonthlyChargesShift` in `evidently_reporter.py:65–100` are ordinary Python classes. Their arithmetic is valid and the numbers reproduce, but they are neither Evidently metric/calculation subclasses nor attached custom tests. They are logged separately to MLflow. The PDF explicitly requires Evidently's custom metric/test API; the guide specifies `SingleValueMetric` / `SingleValueCalculation` as one approach.

### B4 — Migration is incomplete and web search is broken in a clean environment

The Track B source contains no RAG package, knowledge-search tool, or assistant API. Its `assistant/evaluation/` contains only `__init__.py`, not the W16 harness. The runner only registers calculator, datetime, and web search. `ddgs` is absent from both declared and locked dependencies; the fresh environment reproduced its missing-package error. The evaluated system cannot demonstrate W16 cross-source knowledge-base/web verification.

`cp .env.example .env` also fails in the tracked submission: `.env.example` exists only in the untracked development copy. Providing a sanitized example is required for the documented setup path to work.

### B5 — Traces are incomplete and not shipped in Git

The local artifacts contain three query records per version, satisfying the representative-count intent locally. However, the loop truncates tool results to 500 characters (`loop.py:176`), and the runner serializes neither intermediate model decision explanations nor per-step token usage (`run_experiment.py:73–74`). A tool name plus arguments is not the full requested decision record.

`git ls-files 'Week 17'` includes no `mlruns/` trace artifacts or MLflow databases. Databases do not have to be committed, but required representative traces need a portable export or accessible artifact link. Exported numeric comparison tables cannot replace them. The copied B database also points to absolute artifact paths in the untracked `w17-mlops/` tree.

The runner does not log its Evidently HTML reports as MLflow artifacts, contrary to the detailed documentation's artifact listing. The assignment explicitly requires this association for A, which does implement it; for B this is additionally a documentation/plan mismatch.

### B6 — Revision rationale and prompt registry claims lack evidence

The stated v2 diagnosis is that v1 answered without a tool call. Each supplied v1 query actually attempted a tool. The visible failures are missing `ddgs`, invalid empty datetime arguments, and invalid calculator expression syntax. v2/v3 leave the missing dependency unfixed and still initially produce the invalid calculator syntax.

The v3 “chain searches” benefit is not tested with a comparison question. Both Python best practices and RAG-vs-fine-tuning references are defined but never queried. No query-specific trace-to-change explanation supports the claimed progression.

Prompt registry helper methods exist, but the runner never calls them. Both local B registries inspected are empty. Therefore the claims of registered prompt versions, production aliases, and ready rollback capability are unsupported. Prompt files are valid explicit versioning; the PDF does not separately mandate a B prompt registry, but the solution plan and documentation claim one.

### B7 — Logged configuration and latency comparison are misleading

The exported MLflow parameters say `max_iterations=5`; execution explicitly uses `3` (`run_experiment.py:204,214`). Documentation saying the runs were tagged with 3 contradicts the export.

All versions share one provider instance. Its pacing queue carries across versions. `_pace` reserves an estimated request cost, then `chat` appends actual usage without replacing that reservation (`groq.py:69–77,146,202`), double-counting successful calls for pacing. Many measured queries take approximately 55–57 seconds, while the first v1 query takes 2.14 seconds. These are end-to-end times including pacing; they do not isolate prompt-inherent latency. One fixed-order trial on three easy questions cannot establish a general production winner.

Token totals are arithmetically consistent with saved query usage, but not independently verified against provider billing. Retry/failure consumption is not fully accounted for. Log actual configuration, measure pacing and API time separately, repeat/counterbalance versions, and compare quality before declaring a winner.

## 4. Track A methodology and monitoring interpretation

### What is sound on the supplied data

The 80/20 training split is stratified; cross-validation uses five stratified shuffled folds; models genuinely differ; required binary classification metrics are calculated with conventional sklearn functions. Independently reproduced results:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | CV F1 mean |
|---|---:|---:|---:|---:|---:|---:|
| lr_balanced | 0.7353 | 0.8027 | 0.7257 | 0.7623 | 0.8132 | 0.7511 |
| rf_balanced | 0.7211 | 0.7885 | 0.7148 | 0.7498 | 0.7987 | 0.7467 |
| xgb_weighted | 0.7189 | 0.7758 | 0.7306 | 0.7525 | 0.8006 | 0.7510 |
| rf_deep_balanced | 0.7246 | 0.7817 | 0.7342 | 0.7572 | 0.7976 | 0.7516 |

These are reproducible measurements, not evidence of performance on the required IBM dataset.

### A4 — Preprocessing and selection need methodological corrections

- `prepare_pipeline` computes scaled features, but training/CV use the **unscaled** frames. The isolated run produced repeated LR convergence warnings at 1,000 iterations. Use a pipeline that fits scaling inside each CV training fold. Do not simply feed globally scaled training data into CV.
- One-hot categories are discovered before the train/test split. This exposes test-set category vocabulary, though not target labels. Fit the encoder on training folds with explicit unseen-category handling.
- Selecting the best model by repeatedly inspecting test F1 uses the test set for selection. It no longer provides an untouched final performance estimate. Select with validation/CV and evaluate once on held-out data.
- RF CV-F1 0.7516 versus LR 0.7511, with fold standard deviations around 0.005, does not establish a meaningful advantage or “mild overfitting.” Both listed test F1 values exceed their respective CV means. The documentation's inference is unsupported.
- The monitored 70/30 split is separate from the training 80/20 split. Calling it training-time/production-like is acceptable as a demonstration, but it is not the actual training/holdout partition, and it does not measure model degradation on production data.

### A5 — Experiment history is not a clean comparable record

The exported eight-row comparison mixes the four current runs with older baseline runs. An older LR row has approximately 72.68% accuracy and zero precision/recall. Those numbers cannot occur on the current test set with 58.48% positive labels: predicting no positives would yield only about 41.52% accuracy. The old rows therefore use a different target distribution or incompatible scoring; the available evidence does not establish which. Do not present all eight as a controlled same-data comparison.

Both loggers reuse existing runs by name. Repeated experiments write metrics/traces to previous run IDs; changed parameters can conflict with immutable MLflow params. Track A selects from all historical runs. Use new run IDs, experiment-group/data-hash tags, and a current-experiment filter. Preserve the old trials separately.

Some hyperparameter evidence is incomplete: XGBoost's actual `scale_pos_weight` is rounded when logged; defaults/random state/eval metric are not all logged. Record `get_params()` and dataset/split fingerprints. Per-class metrics are added to the local dictionary after the MLflow logging call, so those added fields are not actually logged.

### A6 — Drift detection works, but the stated statistics are wrong

Saved and regenerated reports identify three drifted columns:

| Column | Method | Score | Threshold |
|---|---|---:|---:|
| tenure | Normalized Wasserstein distance | 0.411684 | 0.1 |
| MonthlyCharges | Normalized Wasserstein distance | 0.518729 | 0.1 |
| Contract | Jensen–Shannon distance | 0.124571 | 0.1 |
| Churn target | Jensen–Shannon distance | 0.003615 | 0.1 |

These are **distance scores, not p-values below 0.05**. The 3/20 drifted-column share is 0.15, below the preset's configured dataset threshold of 0.5. Distinguish column-level flags from an overall dataset-drift decision. The saved data report has no tests; the target report has one successful test. A data-drift report, rather than a test suite, is sufficient for this part of A's PDF requirement.

Churn-rate change is −0.005043 in probability, or **−0.5043 percentage points**, equivalent to −0.8623% relative change. Label flipping is an artificial corruption scenario; a stable marginal churn rate does not establish that model performance or the conditional relationship stayed stable.

The feature-selection expression has an operator-precedence bug: `... and ... or nunique < 10` allows Churn back into the purported feature-only list. Fix the parentheses or explicitly define feature and target schemas.

## 5. Orchestration, serving setup, and documentation

### O1 — Track A's DAG never observes the injected/current production batch

The DAG reloads the same CSV and repeats the same undrifted split at seed 42 every week. It never calls `inject_drift` or reads an independently arriving current batch. Its no-drift success is consistent with that code, not a demonstration of detecting the engineered shift. The saved log tests only the no-action route; retraining is skipped.

Retraining runs the original training script on the original data, then sets the production alias without a current-data evaluation or promotion gate. The documentation claims evaluation against the current distribution and conditional replacement, which are absent. The PDF bonus permits merely logging a retraining recommendation, so a correctly connected monitor plus an honest recommendation is sufficient; automated deployment is not required.

Copying this DAG into `$AIRFLOW_HOME/dags` changes its inferred project root to `$AIRFLOW_HOME`, breaking dataset/source paths. Its retrain subprocess also uses Airflow's interpreter; the documented A Airflow install omits MLflow/XGBoost required by training.

### O2 — Track B's DAG does not run the claimed regression system

It hardcodes an absolute path to the untracked development tree. `run_harness` executes a new three-query loop with the default system prompt, not the registered production prompt or W16 harness. `run_regression` simply copies termination success into `pct_tests_passed`; it executes no Evidently check and does not examine responses. A wrong answer ending normally can never trigger the quality alert.

The success branch was executed in the saved log. That proves task wiring on the success path, not correctness monitoring or the alert path. Connect the actual fixed-case evaluator, load an explicit prompt version, and exercise both outcomes.

### D1 — Tracking paths and registry-loading examples disagree

Track A's logger uses `src/data/mlflow.db`, while several docs and the training script's final message start a UI on `data/mlflow.db`. The development `data/mlflow.db` inspected contains no TelcoChurn experiment. Serving requires a server at port 5000, which is not started by the advertised training-then-serving sequence. Starting the server on the wrong DB still fails to load the model.

Examples using `models:/ChurnClassifier/production` request the old stage form; the implemented registry uses `models:/ChurnClassifier@production`. Actual model stages remain `None`; aliases are confirmed. Aliases are a reasonable, guide-authorized modernization because [MLflow deprecated stages](https://www.mlflow.org/docs/latest/ml/model-registry/workflow/). Explain that explicitly rather than claiming literal stage transitions occurred.

### D2 — Versions and reproducibility prose do not match implementation

The tested lockfiles install MLflow 3.16.0, sklearn 1.9.1, FastAPI 0.141.1, numpy 2.5.3, pandas 3.0.5, and Evidently 0.7.23; B also installs OpenAI 3.13.0. The documentation lists different versions. The asserted numpy `<2.0` requirement is contradicted by the successfully reproduced training and saved-model predictions under numpy 2.5.3. No evidence establishes the claimed historical teammate dependency incident; the guide presented it as an example, not project history.

Deleting `uv.lock` in B's “verified reproducibility” instructions re-resolves dependencies rather than reproducing the committed environment. Preserve the lockfile and use `uv sync --locked`. Live stochastic LLM calls and datetime responses cannot promise identical outputs just because dependencies are pinned.

Other definite documentation errors:

- Deep RF uses `max_depth=None`, not 15; the other RF uses depth 10, not default depth.
- A's expected test shape `(1, 30)` should be `(1409, 30)`.
- The B DAG log starts tasks at approximately 10:02:44 and ends at 10:04:47: roughly 123 seconds, not 15.6 seconds. Its `run_duration=15587.848327` is seconds relative to its recorded logical start, not 15.6 seconds of execution.
- Several READMEs instruct entering `w17-mlops/`, which is not tracked in this repository.
- A's separate-monitoring example imports nonexistent `load_and_preprocess`, passes an unsupported `experiment_name` constructor argument, and calls nonexistent `generate_reports`.
- The overview claims XGBoost has highest non-churn recall; the supplied confusion statistics do not support this. State class-specific values if using them in model selection.

### D3 — Both notebooks are unexecuted and contain broken cells

All code cells have null execution counts and no saved output; they are walkthrough drafts, not execution evidence.

- A accesses raw `Contract` after `preprocess()` has one-hot encoded and removed that column; it also expects nonexistent `drift_path` and `run_drift_tests` interfaces.
- B uses `asyncio.run` inside a normal Jupyter kernel with an already-running event loop; use top-level `await`. It truncates responses to 200 characters, overwrites the same trace artifact names with less complete records, and calls the defective string-equality “judge quality” helper without generating the claimed LLM test suite.

### D4 — Prompt/tool and time handling deserve correction

All prompt files include literal `{tools_description}` but are passed without substitution. Native tool schemas provide some tool information independently, but the saved prompt template is not rendered as written. The date tool uses naive local `datetime.now()` without a timezone; v3 adds “UTC” to a tool result that contains no timezone. Its answer's timezone is therefore unsupported by the tool evidence.

## 6. Prioritized repair order

1. **Restore source-data correctness.** Obtain and fingerprint the IBM dataset; quarantine the existing dataset/results under an explicit historical label. Do not overwrite evidence silently.
2. **Repair B evaluation before collecting new scores.** Stable case IDs; complete coverage; answer/tool/grounding rubrics; real Evidently judge with two checks; independent human labels; failure gates.
3. **Restore the assistant capabilities.** Package required tools/dependencies, RAG and W16 evaluation; add a sanitized environment example.
4. **Repair A inference and monitoring requirements.** Fitted preprocessing pipeline, proper probabilities, one consistent registry URI, genuine Evidently custom metric.
5. **Create fresh, attributable experiments.** New run IDs; exact parameters; source/data/prompt hashes; full raw-result traces and decision summaries; portable trace exports. Use real failures to justify prompt revisions.
6. **Regenerate A results and rerun B comparisons.** Select A using validation/CV; reserve final holdout. Counterbalance B execution order and separate pacing from inference latency.
7. **Connect and verify bonus DAGs.** Current batch/production prompt, actual quality metrics, positive and negative branch evidence. Log a recommendation if retraining/promotion is not implemented.
8. **Rewrite documentation from final evidence.** Correct versions, metrics, paths, notebook examples, remaining limitations, and checklists. Verify the exact Git-tracked submission from a clean environment.

## Final assessment of genuineness

- **Track A numbers:** independently reproducible, including full CV and drift calculations. **Wrong dataset for this assignment.**
- **Track B latency/token/iteration totals:** internally consistent with saved traces and MLflow exports. No fresh provider run was performed in this audit.
- **Track B 100% task success, regression success, and judge agreement:** invalid measures of the claimed quality; specific saved failures and an executable wrong-answer probe refute them.
- **Airflow success logs:** evidence that the exercised task paths ran, not that substantive drift/regression handling works.
- **Overall:** substantial implementation exists, but the fully checked completion claims and “production-grade” descriptions are not supported. This audit establishes technical discrepancies; it does not establish deliberate fabrication or misconduct.
