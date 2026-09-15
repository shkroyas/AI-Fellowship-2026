# Fresh live prompt comparison

Model for agent and judges: `openai/gpt-oss-120b` via Groq. All versions use the same five cases, temperature and three-iteration budget. Two Evidently LLM judges evaluate every response; deterministic and completion checks are additional gates.

| Version | Run ID | Combined pass rate |
|---|---|---:|
| v1 | `3b0d1d94ab29444eb208a8cfb38fffb0` | 100% |
| v2 | `1d76c194477a4508bdb0ff06dbe85004` | 80% |
| v3 | `b9a8fdc27f0a4c90beca64d38ead7cfc` | 40% |

## What the traces show

- v1 passed all five combined checks in this execution.
- v2 failed `rag_vs_ft` after a provider/tool serialization error. Both judges rejected the failed-service response.
- v3 failed three combined checks: the correctness judge required timezone information on `datetime_now`; its Python-practices answer omitted reference criteria; and `rag_vs_ft` ended in a provider error. The date deterministic check and grounding judge accepted the date, so that case also illustrates judge strictness and a need for human rubric calibration.

The result does not establish that v3 is better. v1 has the highest observed pass rate here. No prompt production alias was assigned. The suite is small, calls have provider/search variability, and the evaluator uses the same model family as the agent. Human agreement remains unmeasured. Preserve failures when comparing future revisions; do not relabel a failed judge as a pass by substituting keyword scores.

## Evidence

[MLflow export](../screenshots/mlflow_evidence.json), [complete summary](experiment_summary.json), [v1 verdicts](verdicts_v1.json), [v2 verdicts](verdicts_v2.json), [v3 verdicts](verdicts_v3.json). Each version has an Evidently HTML report, full snapshot JSON and complete trace JSON alongside these files.

## Independent Airflow execution

The manually triggered DAG reran v3 with the same model and live evaluator. It scored 60%, executed `alert_regression`, and skipped `log_success`. The difference from the comparison's 40% illustrates single-run provider/model variability. Both sets of traces and verdicts are retained.
