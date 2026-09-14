Offline scripted provider and tools; synthetic tokens. NOT a live-model quality score.

# Agentic Loop Evaluation Report

**Total Queries:** 4
**Task Completion Rate:** 50.0%
**Tool Correctness Rate:** 100.0%
**Average Trajectory Length:** 1.5 iterations
**Total Duration:** 0.0s
**Total Tokens:** {'prompt_tokens': 50, 'completion_tokens': 10}
**Avg Tokens/Query:** {'prompt_tokens': 12, 'completion_tokens': 2}

## Per-Query Results

| Query ID | Difficulty | Completed | Tools OK | Iterations | Tokens | Duration |
|----------|-----------|-----------|----------|------------|--------|----------|
| cross_source | moderate | Yes | Yes | 3 | 36 | 1ms |
| clarification | simple | Yes | Yes | 1 | 12 | 0ms |
| provider_failure | simple | No | Yes | 1 | 0 | 0ms |
| wrong_answer | simple | No | Yes | 1 | 12 | 0ms |

## Failure Summary

- **Total Failures:** 2
- **Hard Failures:** 1
- **Soft Failures:** 1
- **Cascading Soft Failures:** 0

### Failure Details

- **provider_failure** (hard): Execution failed or no response was produced
- **wrong_answer** (soft): Response did not meet required evidence, content, stopping or trajectory criteria

## Trajectory Analysis

| Query ID | Expected Iters | Actual Iters | Reasonable? | Stopped Reason |
|----------|---------------|-------------|-------------|----------------|
| cross_source | 3-5 | 3 | Yes | model_answered |
| clarification | 1-5 | 1 | Yes | clarification |
| provider_failure | 1-5 | 1 | Yes | error |
| wrong_answer | 1-5 | 1 | Yes | model_answered |