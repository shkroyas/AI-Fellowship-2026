Live provider: openai/gpt-oss-20b; shared sequential budget; fallback: nvidia/nemotron-3-super-120b-a12b:free; max output tokens: 1024

# Agentic Loop Evaluation Report

**Total Queries:** 10
**Task Completion Rate:** 0.0%
**Tool Correctness Rate:** 0.0%
**Average Trajectory Length:** 1.2 iterations
**Total Duration:** 1053.7s
**Total Tokens:** {'prompt_tokens': 3392, 'completion_tokens': 455}
**Avg Tokens/Query:** {'prompt_tokens': 339, 'completion_tokens': 45}

## Per-Query Results

| Query ID | Difficulty | Completed | Tools OK | Iterations | Tokens | Duration |
|----------|-----------|-----------|----------|------------|--------|----------|
| simple_01 | simple | No | No | 1 | 1476 | 1176ms |
| simple_02 | simple | No | No | 1 | 0 | 30510ms |
| simple_03 | simple | No | No | 2 | 1187 | 91694ms |
| moderate_01 | moderate | No | No | 1 | 0 | 35491ms |
| moderate_02 | moderate | No | No | 1 | 0 | 30434ms |
| moderate_03 | moderate | No | No | 1 | 0 | 30468ms |
| complex_01 | complex | No | No | 1 | 0 | 30491ms |
| complex_02 | complex | No | No | 2 | 1184 | 91535ms |
| complex_03 | complex | No | No | 1 | 0 | 30812ms |
| complex_04 | complex | No | No | 1 | 0 | 30478ms |

## Failure Summary

- **Total Failures:** 10
- **Hard Failures:** 9
- **Soft Failures:** 1
- **Cascading Soft Failures:** 0

### Failure Details

- **simple_01** (soft): Response did not meet required evidence, content, stopping or trajectory criteria
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
| simple_01 | 1-2 | 1 | Yes | model_answered |
| simple_02 | 1-2 | 1 | Yes | error |
| simple_03 | 1-2 | 2 | Yes | error |
| moderate_01 | 2-3 | 1 | No | error |
| moderate_02 | 2-3 | 1 | No | error |
| moderate_03 | 2-3 | 1 | No | error |
| complex_01 | 3-5 | 1 | No | error |
| complex_02 | 3-5 | 2 | No | error |
| complex_03 | 3-4 | 1 | No | error |
| complex_04 | 3-4 | 1 | No | error |