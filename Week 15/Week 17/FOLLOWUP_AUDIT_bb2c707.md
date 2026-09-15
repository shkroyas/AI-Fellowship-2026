# Week 17 follow-up audit — pushed fixes

**Verdict: improved, but still not submission-ready.**

Reviewed GitHub `main` at [bb2c707e8edf4a8e770a72c7202e3da2bd804a79](https://github.com/shkroyas/AI-Fellowship-2026/commit/bb2c707e8edf4a8e770a72c7202e3da2bd804a79), titled `fix(Week17): critical audit fixes`, on 15 September 2026. The shared local checkout is older and has uncommitted changes, so the review used a separate clone in `/tmp/w17-recheck-bb2c707`. Findings below refer to the pushed commit, not the old local source.

The original [requirements audit](REQUIREMENTS_AUDIT.md) remains historical. This report supersedes its findings where changes are explicitly confirmed below. No application fixes or pushes were made during this review.

## Confirmed improvements

| Claimed change | Verification |
|---|---|
| Correct IBM dataset | **Fixed.** 7,043 rows, 1,869 churn-positive, 5,174 negative. SHA-256 matches the IBM file downloaded during the first audit: `16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91`. |
| Training/monitoring/DAG dataset paths | **Fixed in source.** The new filename is used. The old dataset is explicitly quarantined. |
| Feature-selection operator precedence | **Fixed.** Churn is excluded by the corrected parentheses. |
| `.env.example` | **Fixed.** A sanitized example is Git-tracked. |
| Logged `max_iterations` | **Source corrected to 3**, matching execution; rerunning existing run IDs now causes a parameter conflict, detailed below. |
| Three regression queries considered | **Partly fixed.** Current positional mapping includes three supplied results rather than dropping two. It is not actually an ID-based join. |
| Per-row pass/fail assignment | **Improved.** Verdicts now stay with their rows. Their correctness criteria remain inadequate. |
| Some overview wording | Updated, but detailed documentation and result evidence remain inconsistent. |

## Blocking issues and required fixes

### 1. Track B cannot import with the committed Evidently version

**Location:** `Task B/src/track_b/utils/evidently_judge.py:8`.

The added `from evidently.metrics import TestCaseMetric` raises:

```text
ImportError: cannot import name 'TestCaseMetric' from 'evidently.metrics'
```

This was tested using Evidently **0.7.23**, the version in the pushed lockfile. The runner imports this module before entering `main`, so it cannot start. The imported symbol is unused.

**Fix:** Remove the invalid import, implement evaluation against supported APIs in the pinned environment, and add an import smoke check before running costly evaluations.

### 2. Track B's lockfile is stale, and the search dependency is the wrong package for its import

**Locations:** `Task B/pyproject.toml:16`, `Task B/uv.lock`, `assistant/tools/web_search.py:14`.

The dependency list adds `duckduckgo-search`, but the lockfile is unchanged. An online `uv lock --check` reports:

```text
Resolved 150 packages
error: The lockfile at `uv.lock` needs to be updated, but `--check` was provided.
```

The initial offline check failed because this new dependency was not cached; the online check independently established the actual lockfile mismatch. Also, the tool imports `from ddgs import DDGS`, whereas the new declared package is `duckduckgo-search`. Adding that package does not match the import.

**Fix:** Declare the package actually used by the implementation (`ddgs`), regenerate and commit `uv.lock`, then verify `uv sync --locked`, the import, and a real search. Do not call search fixed merely because a similarly named package was added.

### 3. Track A's API still fails, and probability/encoding remain incorrect

**Locations:** `Task A/src/track_a/serve.py:26–45,85–105`; `train.py:144–149`.

The following are independent defects:

1. Startup loads `@production` but then calls `get_latest_versions(..., stages=["Production"])[0]`. Training sets aliases, not model stages. Against the registry created by the fresh training run, startup raises **`IndexError: list index out of range`** because the stage lookup is empty.
2. Training saves `features.json` to `reports/<run>/`, but never logs it to MLflow. Serving tries to download `../features.json`, which is not that artifact. The actual registered run's root artifacts contain plots and Evidently reports, not the feature list.
3. Single-row `pd.get_dummies(..., drop_first=True)` still removes every categorical value. Filling the missing features with zero hides the shape error while discarding the user's categories. For example, Contract values cannot affect the encoded row.
4. `mlflow.pyfunc.load_model` returns a wrapper without `predict_proba`. The added `hasattr` branch therefore falls back to `predict`, still returning a class label as a probability.
5. The request schema still omits inputs used by training, such as SeniorCitizen and several service fields.

After manually supplying the correct feature list solely for diagnosis, both Month-to-month and Two-year requests returned `churn_probability=0.0`, `confidence=1.0`. The wrapper reported `hasattr(model, "predict_proba") == False`. This is not a functioning probability API.

**Fix:** Register a complete fitted raw-input preprocessing/classifier pipeline, using a fitted encoder and a defined input schema. Resolve the exact version with `get_model_version_by_alias`. For a sklearn-flavor model/pipeline, use a loading interface that exposes its real `predict_proba`; alternatively, define a pyfunc wrapper whose `predict` explicitly returns probabilities. Save any separate feature metadata as a correctly named artifact tied to that exact version. Fail startup clearly if required metadata is missing.

[MLflow's registry documentation](https://www.mlflow.org/docs/latest/ml/model-registry/workflow/) distinguishes aliases from deprecated stages; use one consistent mechanism.

### 4. Neither “correctness report” nor response length satisfies the required evaluation

**Locations:** `Task B/run_experiment.py:101–169`; `evidently_judge.py:29–66`.

`run_correctness_report` is a keyword counter, not an LLM evaluator, and the experiment runner **never calls it**. The runner still calls `run_text_eval_report`, which attaches no judge descriptors or tests. In a diagnostic execution removing only the invalid unused import in memory, its snapshot still contained **one RowCount metric and zero tests**. No production code was changed to perform that diagnostic.

The PDF requires an **Evidently LLM-as-judge evaluator with at least two checks**, including reference-based correctness. A deterministic keyword check can supplement this but cannot replace it. `judge_agreement` still just copies the pass rate; no independent human judgments are compared.

The new task-success rule, `len(response.strip()) > 20`, measures verbosity rather than fulfillment. It rejects a correct concise calculator answer `51` while accepting `I cannot tell you the current date.` as successful if the model terminates normally.

**Fix:** Separate termination from correctness, evidence grounding, and tool validity. Execute a real reference-based judge and a second defined criterion, attach explicit tests, save individual verdicts/reasons, and calculate a genuine suite pass rate. Review and manually label examples to compute actual agreement. The [Evidently judge tutorial](https://docs.evidentlyai.com/examples/LLM_judge) covers reference-based evaluation, additional criteria, and comparison with manual labels.

### 5. The revised keyword checks still pass false answers

I executed the submitted `score_response` function, extracted directly from the source using Python AST because the module itself cannot import. All these deliberately incorrect answers passed:

| Case | Incorrect answer | Result |
|---|---|---|
| RAG | `RAG has no retrieval or generation and never uses knowledge.` | Pass |
| Datetime | `I cannot tell you the current date.` | Pass |
| Calculator | `The answer is 510, not the correct value.` | Pass |

The RAG check ignores negation; the date check only looks for “date”; “51” matches inside “510”. Missing criteria still return `True`. The golden IDs are only copied into output after pairing rows **by position**; missing/reordered results are not safely matched. Empty results can also produce a missing-column error rather than an explicit failed suite.

**Fix:** Carry a stable ID through query execution and join on it. Validate coverage and uniqueness. Treat missing criteria/results as failure or invalid evaluation. Parse the calculator's final numeric answer and compare to 51 with a tolerance, rejecting contradictions. Validate datetime against the captured tool result with timezone information. Use semantic reference checks for RAG and an evidence/tool-use rubric. Do not use the generic date-tool description as if it were a correct answer to today's date.

### 6. The pushed results were not regenerated for the changed data or evaluation

Comparing committed Git blobs against the first audit's saved hashes shows **all 31 report/screenshot files checked are unchanged**: 16 A reports/plots, five A evidence files, seven B reports, and three B evidence files.

Thus the A F1=0.7623 result remains a synthetic-data result, even though the overview now describes a 26.5% IBM churn rate. B's saved regression JSON still says `total_tests: 1`, and its MLflow export still records `max_iterations: 5`. Editing narrative labels does not update those experiments.

I ran the pushed A training pipeline in isolation on the corrected dataset. It completed successfully. Its actual metrics are:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | CV F1 |
|---|---:|---:|---:|---:|---:|---:|
| lr_balanced | 0.7381 | 0.5043 | 0.7888 | 0.6152 | 0.8422 | 0.6298 |
| rf_balanced | 0.7551 | 0.5257 | 0.7941 | **0.6326** | **0.8461** | 0.6327 |
| xgb_weighted | 0.7523 | 0.5220 | 0.7941 | 0.6299 | 0.8435 | 0.6368 |
| rf_deep_balanced | 0.7544 | 0.5250 | 0.7861 | 0.6296 | 0.8428 | **0.6377** |

The script selects **rf_balanced**, not LR. That follows the current test-F1 rule; it is not an endorsement of choosing models on a supposedly final holdout. Choose a declared validation/CV policy before final selection. Convergence warnings still occur for unscaled logistic regression.

The regenerated monitoring numbers also differ:

- Reference/current churn: **26.5314% → 28.7269%**, a **+2.1955 percentage-point** or **+8.2750% relative** shift.
- Mean MonthlyCharges: **64.9501 → 79.0524**, or **+21.7125%** relative shift.

**Fix:** Preserve the old exports as labeled history, then generate new runs, model registry evidence, plots, monitoring HTML/JSON, and version comparison tables. Export results from the runs automatically. Do not replace numbers by hand or claim a fresh B result before actual evaluation runs successfully.

### 7. Track A custom metrics still do not use Evidently's custom metric/test API

The updated reporter explicitly calls them “standalone calculations.” That description is more honest, but the requirement remains unmet: the PDF specifically asks for a custom metric/test using Evidently's API. Correcting the feature-selection expression does not fix this separate requirement.

**Fix:** Implement and attach an actual Evidently custom metric/calculation, such as a mean MonthlyCharges change, and show it in the generated report. Continue logging its value to MLflow as well.

### 8. Reusing runs prevents clean reruns and corrupts provenance

Both loggers still reuse run IDs by name. In a temporary copy of the old B database, logging the corrected value 3 to `prompt_v1` raised:

```text
MlflowException: Changing param values is not allowed.
Param 'max_iterations' was already logged with value '5'.
Attempted logging new value '3'.
```

A also searches across all historical runs; the dataset change alters XGBoost class weights and makes historical comparisons incompatible.

**Fix:** Create a new run per experiment execution, log source/data/prompt hashes, and select models only within the intended experiment group. Do not edit old parameters or delete old evidence to avoid the error.

## Remaining prior-audit requirements

These were not resolved by the pushed changes:

- **Migration:** B still lacks the W16 evaluation harness, RAG implementation, and knowledge-search tool. Three simple queries do not demonstrate the original cross-source feature.
- **Full traces:** Raw tool results remain truncated to 500 characters, model decision explanations are missing, and portable representative traces are not Git-tracked or linked as accessible artifacts.
- **Trace-driven revisions:** The claimed diagnoses still do not identify actual query-specific failures leading to each change. Test the comparison/multi-source behavior you claim v3 improves.
- **Prompt registry:** Helpers are not called by the runner. Explicit prompt files satisfy basic versioning, but the documentation should not claim working production aliases/rollback without evidence.
- **Promotion gates:** No actual judge-test gate prevents promotion of regressed versions.
- **A bonus DAG:** Still splits a fixed undrifted CSV; changing the filename does not connect current data or exercise positive drift/retraining. Retraining does not use a new monitored batch or validate before production assignment.
- **B bonus DAG:** Still copies the response-length-based completion rate into regression pass rate; it does not run the required evaluator or load the production prompt. Using a relative project path improves portability only when the DAG remains in its project directory; copying it alone to Airflow's DAG folder changes the inferred root.
- **Methodology:** Scaling is computed but unused; encoder vocabulary is learned before the holdout split; test F1 is used for model selection; pacing state/double reservations still confound prompt latency comparisons.
- **Notebook/docs:** Broken notebook cells, incorrect registry URI examples, conflicting MLflow DB paths, missing-model/input response mismatches, and deleting `uv.lock` in reproducibility instructions remain. The detailed A documentation still says MLflow 3.3.3 and 58.5% churn. The overview now calls Contract drift “Wasserstein,” but the saved categorical metric is Jensen–Shannon distance. The claimed 15.6-second B DAG duration remains unsupported.

## Recommended completion sequence and acceptance checks

1. **Make B start reproducibly:** correct imports/package names; commit a refreshed lock; verify `uv lock --check`, `uv sync --locked`, and runner import from a clean checkout.
2. **Repair and test A serving:** fitted preprocessing pipeline, true probability output, exact alias/version metadata. Startup must succeed after fresh training; valid category changes must reach the model encoding; API probabilities must match direct pipeline probabilities.
3. **Implement real B quality evaluation:** actual LLM judge with two checks plus task-specific deterministic checks. Every deliberately wrong case above must fail, valid `51` must pass its numeric check, and missing/reordered cases must not silently pass.
4. **Implement A's custom Evidently metric and fresh run creation.** Verify old experiments remain intact and new params do not collide with old IDs.
5. **Rerun both experiments and regenerate evidence.** Use a stated selection policy, complete traces, actual parameters, per-case verdicts, and portable exports. Record any failures honestly.
6. **Reconnect bonus DAGs, execute both branch outcomes, and rewrite documentation from those artifacts.** Remove unsupported completion/production claims until their checks pass.

Supporting evidence: [fresh A training log](audit/recheck_bb2c707/track_a_training.txt), [B lock-check failure](audit/recheck_bb2c707/track_b_lock_check.txt), [exact new metrics and committed-artifact comparisons](audit/recheck_bb2c707/evidence.json).

**Limits:** No fresh live LLM or external web-search experiment was run. The B startup/lock blockers and offline scoring counterexamples are sufficient to reject its current completion claim. A training and registry creation succeeded in isolation; the API startup and encoding/probability probes failed. The new A measurements are audit results in `/tmp`, not results already published in the reviewed commit.
