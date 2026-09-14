Live provider: gemini-3.6-flash; delay 15.0s per call

# Agentic Loop Evaluation Report

**Total Queries:** 10
**Task Completion Rate:** 50.0%
**Tool Correctness Rate:** 60.0%
**Average Trajectory Length:** 2.4 iterations
**Total Duration:** 523.3s
**Total Tokens:** {'prompt_tokens': 30436, 'completion_tokens': 10926}
**Avg Tokens/Query:** {'prompt_tokens': 3043, 'completion_tokens': 1092}

## Per-Query Results

| Query ID | Difficulty | Completed | Tools OK | Iterations | Tokens | Duration |
|----------|-----------|-----------|----------|------------|--------|----------|
| simple_01 | simple | Yes | Yes | 3 | 6283 | 87406ms |
| simple_02 | simple | Yes | Yes | 2 | 1897 | 35408ms |
| simple_03 | simple | Yes | Yes | 2 | 2756 | 34911ms |
| moderate_01 | moderate | Yes | Yes | 4 | 10031 | 96985ms |
| moderate_02 | moderate | Yes | Yes | 3 | 6233 | 63843ms |
| moderate_03 | moderate | No | Yes | 5 | 13105 | 126379ms |
| complex_01 | complex | No | No | 2 | 1057 | 33286ms |
| complex_02 | complex | No | No | 1 | 0 | 15026ms |
| complex_03 | complex | No | No | 1 | 0 | 15026ms |
| complex_04 | complex | No | No | 1 | 0 | 15022ms |

## Failure Summary

- **Total Failures:** 7
- **Hard Failures:** 4
- **Soft Failures:** 3
- **Cascading Soft Failures:** 0

### Failure Details

- **simple_01** (soft): Response did not meet required evidence, content, stopping or trajectory criteria
- **moderate_01** (soft): Response did not meet required evidence, content, stopping or trajectory criteria
- **moderate_03** (soft): Response did not meet required evidence, content, stopping or trajectory criteria
- **complex_01** (hard): Execution failed or no response was produced
- **complex_02** (hard): Execution failed or no response was produced
- **complex_03** (hard): Execution failed or no response was produced
- **complex_04** (hard): Execution failed or no response was produced

## Trajectory Analysis

| Query ID | Expected Iters | Actual Iters | Reasonable? | Stopped Reason |
|----------|---------------|-------------|-------------|----------------|
| simple_01 | 1-2 | 3 | No | model_answered |
| simple_02 | 1-2 | 2 | Yes | model_answered |
| simple_03 | 1-2 | 2 | Yes | model_answered |
| moderate_01 | 2-3 | 4 | No | model_answered |
| moderate_02 | 2-3 | 3 | Yes | model_answered |
| moderate_03 | 2-3 | 5 | No | max_iterations |
| complex_01 | 3-5 | 2 | No | error |
| complex_02 | 3-5 | 1 | No | error |
| complex_03 | 3-4 | 1 | No | error |
| complex_04 | 3-4 | 1 | No | error |
