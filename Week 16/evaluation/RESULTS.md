# Evaluation Results

Royas Shakya · Week 16 · Evaluation date: 2026-09-13.

## Method

The harness is implemented in plain Python without an external evaluation framework. Ten queries span simple, moderate and complex tasks. The live run used `gemini-3.6-flash` with a 15-second pause per model call and at most five decisions per query. Scores use the submitted query rubrics without post-run relaxation. Source hashes and environment versions are supplied alongside this report.

Completion requires the expected stopping state, every required successful tool call and the query's lexical content checks. Tool correctness checks names and arguments from execution traces. Initial automatic retrieval is context, not a model-selected tool call. Trajectory reasonableness is measured separately against the expected range. These are useful proxies, not proofs of factual accuracy.

## Live summary

| Metric | Measured result |
|---|---|
| Queries evaluated | 10 |
| Task completion | 50% (5/10) |
| Tool correctness | 60% (6/10) |
| Mean decision iterations | 2.4 |
| All completion and trajectory checks | 3/10 |
| Prompt tokens | 30,436 |
| Completion/thinking tokens | 10,926 |
| Total reported tokens | 41,362 |
| Duration | 523.3 seconds |

Token totals include successful decision and compaction responses. They exclude unknown consumption on failed calls, prior runs, credential checks and separate failure-injection runs. No dollar-cost estimate is asserted. This is a single-agent design; a multi-agent coordination baseline is not applicable.

## Per-query results

| Query ID | Completed | Tools correct | Decisions | Tokens | Stop reason |
|---|---|---|---|---|---|
| simple_01 | Yes | Yes | 3 | 6,283 | model_answered |
| simple_02 | Yes | Yes | 2 | 1,897 | model_answered |
| simple_03 | Yes | Yes | 2 | 2,756 | model_answered |
| moderate_01 | Yes | Yes | 4 | 10,031 | model_answered |
| moderate_02 | Yes | Yes | 3 | 6,233 | model_answered |
| moderate_03 | No | Yes | 5 | 13,105 | max_iterations |
| complex_01 | No | No | 2 | 1,057 | error |
| complex_02 | No | No | 1 | 0 | error |
| complex_03 | No | No | 1 | 0 | error |
| complex_04 | No | No | 1 | 0 | error |

## Failure analysis

Four hard failures were provider HTTP 429 errors during the complex queries. No quota-triggered key rotation was used. `moderate_03` gathered evidence for five decisions but did not answer; it returned an explicit incomplete-verification response. This is a soft failure, not a completed task. Compaction occurred on this query and its tokens are included.

`simple_01` and `moderate_01` passed task-content/tool checks but exceeded their expected trajectory ranges, so they are also logged as soft failures. Consequently, five completed tasks and seven total failure flags are not contradictory: two completed tasks carry efficiency failures. There were no classified cascading-soft failures in this run; the taxonomy's causal candidates require human trace review.

## Manual review and limits

- `simple_01`: the RAG definition and named techniques align with the supplied guide; the answer includes document references. Three decisions exceeded the expected one-to-two range.
- `simple_02`: the final response reflects the date/time tool's returned server clock, including 2026-09-13. Timezone presentation remains dependent on the server.
- `simple_03`: the calculator result and final answer are 51, as expected for 15% of 340.
- `moderate_01`: the trace shows a knowledge search followed by two different web searches before answering. This demonstrates model-directed cross-source behavior rather than a fixed one-search sequence. The answer links external sources, but broad claims such as tooling being “mandatory” or a universal “current standard” exceed what the saved excerpts establish. Its automatic pass should not be read as independent validation of every claim.
- `moderate_02`: the answer distinguishes enduring concepts from gaps in the internal AI overview and meets the automatic rubric. External claims were not independently fact-checked exhaustively.
- `moderate_03`: the bound and compaction functioned, but evidence-sufficiency judgment did not reach an answer in time.
- Complex-query quality remains unmeasured because provider quota prevented completed responses. A successful full rerun requires available quota; waiting between calls does not repair exhausted daily allowance.

## Controlled regression and offline harness

The submitted source passes **24/24 regression/API tests**, including multi-step decisions, clarification, malformed arguments, duplicate-call reuse, context compaction and token accounting, provider errors, intentional search/timeout failures, native Gemini final-text adaptation, key isolation and production knowledge-tool startup. See `regression_tests.txt`. These tests use controlled responses and do not prove autonomous model quality.

The offline harness has four deliberate cases: cross-source completion, clarification, timeout and wrong answer. Its 2/4 completion rate is expected because the final two cases are intentional negatives; it logs one hard and one soft failure. Its 60 tokens are synthetic. See `evaluation_offline.md` and `.json`.

## Intentional failure injection

Controlled regression tests deliberately make a search executor raise an exception and force a provider timeout. They verify error propagation, exclusion of failed sources, explicit uncertainty in the scripted response, and a configured fallback call. This establishes executable failure handling independently of external quota.

The separate live failure-injection results are in `failure_injection_live.md` and `.json`. The timeout fallback case in that runner uses scripted providers and is labeled as such. Any provider-unavailable cases are inconclusive for autonomous recovery, not passing live tests. Review the injection status together with the response excerpts; do not combine controlled and live success rates.

## Reproduce

See `../docs/SETUP.md` for commands. The machine-readable live artifact retains every query's answer, stop state, token counts and trace excerpts. Excerpts are capped and do not preserve the full retrieved corpus. These results demonstrate implemented behavior and expose remaining limitations; they do not claim 100% completion or a deployed production system.
