Live provider: openai/gpt-oss-20b; shared sequential budget; fallback: nvidia/nemotron-3-super-120b-a12b:free; max output tokens: 1024

# Agentic Loop Evaluation Report

**Total Queries:** 1
**Task Completion Rate:** 0.0%
**Tool Correctness Rate:** 100.0%
**Average Trajectory Length:** 2.0 iterations
**Total Duration:** 211.2s
**Total Tokens:** {'prompt_tokens': 1130, 'completion_tokens': 30}
**Avg Tokens/Query:** {'prompt_tokens': 1130, 'completion_tokens': 30}

## Per-Query Results

| Query ID | Difficulty | Completed | Tools OK | Iterations | Tokens | Duration |
|----------|-----------|-----------|----------|------------|--------|----------|
| simple_02 | simple | No | Yes | 2 | 1160 | 31056ms |

## Failure Summary

- **Total Failures:** 1
- **Hard Failures:** 1
- **Soft Failures:** 0
- **Cascading Soft Failures:** 0

### Failure Details

- **simple_02** (hard): Execution failed or no response was produced

## Trajectory Analysis

| Query ID | Expected Iters | Actual Iters | Reasonable? | Stopped Reason |
|----------|---------------|-------------|-------------|----------------|
| simple_02 | 1-2 | 2 | Yes | error |