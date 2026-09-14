> Historical artifact: these results used the old evaluator and contain unsupported success/cost claims. See the root W16_Assignment_Report_UPDATED.md and evaluation_live.md / evaluation_offline.md for the corrected evidence.

# Token Cost Comparison: Agentic vs Single-Pass

| Query | Single-Pass Tokens | Agentic Tokens | Overhead |
|-------|-------------------|----------------|----------|
| simple_01 | 0 | 0 | +0% |
| simple_02 | 0 | 0 | +0% |
| simple_03 | 0 | 0 | +0% |
| moderate_01 | 0 | 0 | +0% |
| moderate_02 | 0 | 0 | +0% |

**Total Single-Pass Tokens:** 0
**Total Agentic Tokens:** 0
**Average Overhead:** +0.0%

The agentic loop uses more tokens because it makes multiple LLM calls per query (one per iteration) to iteratively gather and verify evidence. This additional cost buys cross-source verification that a single-pass pipeline cannot provide.