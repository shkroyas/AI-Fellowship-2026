# Track B implementation

See [README.md](README.md) for commands and [execution status](../EXECUTION_STATUS.md) for current evidence.

## Evaluation

`GOLDEN_QUERIES` is the common query/reference source. IDs are carried from execution to evaluation. Unknown or duplicate IDs invalidate evaluation; missing cases fail. Numeric scoring compares the final parsed number against 51 with a tolerance and rejects explicit contradictions. RAG checks reject negated concepts. Datetime parses ISO and named-month dates against the captured datetime tool output, normalizing Unicode punctuation. These deterministic checks supplement semantic judges rather than claiming to replace them.

`EvidentlyJudge` attaches two `LLMJudge` descriptors built with `BinaryClassificationPromptTemplate`, explicit PASS tests, and per-row reasoning. Correctness compares against a reference. Grounding checks actual successful tool results and requires calculator/datetime tool use for those tasks. Conceptual answers may use general knowledge when no tool is required, but may not invent tool evidence or citations. The report stores both labels/reasons and the complete combined verdict.

The custom OpenAI-compatible wrapper uses the configured provider endpoint, bounded completion length, sequential requests, and bounded retries. It does not change the model or provider automatically. Provider errors propagate and mark the run failed. No failed judge is replaced by a deterministic proxy.

## Experiment provenance

Every execution creates a timestamped run. MLflow parameters include the exact prompt hash, version, model, provider and iteration limit. Portable JSON traces include complete tool outputs. Completion rate is separate from task success; task success requires both judges, deterministic checks, complete coverage and termination. Human agreement is explicitly unavailable without independent labels.

## Orchestration and limitations

The DAG calls the same runner/evaluator through a subprocess using the track's environment and gives each DAG execution its own report directory. It branches on the real combined pass rate. Below-threshold runs log a regression alert and do not promote a prompt. The version is selected explicitly, not through a production alias. This submission does not demonstrate knowledge-base migration, cross-source retrieval or human-label calibration; do not infer those capabilities from prompt instructions.
