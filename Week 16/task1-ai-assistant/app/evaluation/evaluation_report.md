> Historical artifact: these results used the old evaluator and contain unsupported success/cost claims. See the root W16_Assignment_Report_UPDATED.md and evaluation_live.md / evaluation_offline.md for the corrected evidence.

# Agentic Loop Evaluation Report

**Total Queries:** 10
**Task Completion Rate:** 100.0%
**Tool Correctness Rate:** 10.0%
**Average Trajectory Length:** 0.4 iterations
**Total Duration:** 33.4s
**Total Tokens:** {'prompt_tokens': 4866, 'completion_tokens': 463}
**Avg Tokens/Query:** {'prompt_tokens': 486, 'completion_tokens': 46}

## Per-Query Results

| Query ID | Difficulty | Completed | Tools OK | Iterations | Tokens | Duration |
|----------|-----------|-----------|----------|------------|--------|----------|
| simple_01 | simple | Yes | No | 3 | 4441 | 22985ms |
| simple_02 | simple | Yes | Yes | 1 | 888 | 3303ms |
| simple_03 | simple | Yes | No | 0 | 0 | 801ms |
| moderate_01 | moderate | Yes | No | 0 | 0 | 1131ms |
| moderate_02 | moderate | Yes | No | 0 | 0 | 879ms |
| moderate_03 | moderate | Yes | No | 0 | 0 | 1156ms |
| complex_01 | complex | Yes | No | 0 | 0 | 734ms |
| complex_02 | complex | Yes | No | 0 | 0 | 814ms |
| complex_03 | complex | Yes | No | 0 | 0 | 759ms |
| complex_04 | complex | Yes | No | 0 | 0 | 811ms |

## Failure Summary

- **Total Failures:** 0
- **Hard Failures:** 0
- **Soft Failures:** 0
- **Cascading Soft Failures:** 0

## Trajectory Analysis

| Query ID | Expected Iters | Actual Iters | Reasonable? | Stopped Reason |
|----------|---------------|-------------|-------------|----------------|
| simple_01 | 1-2 | 3 | Yes | model_answered |
| simple_02 | 1-2 | 1 | Yes | error |
| simple_03 | 1-2 | 0 | No | error |
| moderate_01 | 2-3 | 0 | No | error |
| moderate_02 | 2-3 | 0 | No | error |
| moderate_03 | 2-3 | 0 | No | error |
| complex_01 | 3-5 | 0 | No | error |
| complex_02 | 3-5 | 0 | No | error |
| complex_03 | 3-4 | 0 | No | error |
| complex_04 | 3-4 | 0 | No | error |