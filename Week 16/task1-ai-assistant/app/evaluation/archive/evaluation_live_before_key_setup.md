Live provider: gemini-3.6-flash; delay 15.0s per call

# Agentic Loop Evaluation Report

**Total Queries:** 10
**Task Completion Rate:** 0.0%
**Tool Correctness Rate:** 0.0%
**Average Trajectory Length:** 1.0 iterations
**Total Duration:** 154.7s
**Total Tokens:** {'prompt_tokens': 0, 'completion_tokens': 0}
**Avg Tokens/Query:** {'prompt_tokens': 0, 'completion_tokens': 0}

## Per-Query Results

| Query ID | Difficulty | Completed | Tools OK | Iterations | Tokens | Duration |
|----------|-----------|-----------|----------|------------|--------|----------|
| simple_01 | simple | No | No | 1 | 0 | 15784ms |
| simple_02 | simple | No | No | 1 | 0 | 15447ms |
| simple_03 | simple | No | No | 1 | 0 | 15438ms |
| moderate_01 | moderate | No | No | 1 | 0 | 15372ms |
| moderate_02 | moderate | No | No | 1 | 0 | 15487ms |
| moderate_03 | moderate | No | No | 1 | 0 | 15461ms |
| complex_01 | complex | No | No | 1 | 0 | 15408ms |
| complex_02 | complex | No | No | 1 | 0 | 15404ms |
| complex_03 | complex | No | No | 1 | 0 | 15386ms |
| complex_04 | complex | No | No | 1 | 0 | 15525ms |

## Failure Summary

- **Total Failures:** 10
- **Hard Failures:** 10
- **Soft Failures:** 0
- **Cascading Soft Failures:** 0

### Failure Details

- **simple_01** (hard): Execution failed or no response was produced
- **simple_02** (hard): Execution failed or no response was produced
- **simple_03** (hard): Execution failed or no response was produced
- **moderate_01** (hard): Execution failed or no response was produced
- **moderate_02** (hard): Execution failed or no response was produced
- **moderate_03** (hard): Execution failed or no response was produced
- **complex_01** (hard): Execution failed or no response was produced
- **complex_02** (hard): Execution failed or no response was produced
- **complex_03** (hard): Execution failed or no response was produced
- **complex_04** (hard): Execution failed or no response was produced

## Trajectory Analysis

| Query ID | Expected Iters | Actual Iters | Reasonable? | Stopped Reason |
|----------|---------------|-------------|-------------|----------------|
| simple_01 | 1-2 | 1 | Yes | error |
| simple_02 | 1-2 | 1 | Yes | error |
| simple_03 | 1-2 | 1 | Yes | error |
| moderate_01 | 2-3 | 1 | No | error |
| moderate_02 | 2-3 | 1 | No | error |
| moderate_03 | 2-3 | 1 | No | error |
| complex_01 | 3-5 | 1 | No | error |
| complex_02 | 3-5 | 1 | No | error |
| complex_03 | 3-4 | 1 | No | error |
| complex_04 | 3-4 | 1 | No | error |