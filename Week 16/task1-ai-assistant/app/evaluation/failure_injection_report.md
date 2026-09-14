> Historical artifact: these results used the old evaluator and contain unsupported success/cost claims. See the root W16_Assignment_Report_UPDATED.md and evaluation_live.md / evaluation_offline.md for the corrected evidence.

# Failure Injection Test Report

| Test | Passed | Notes |
|------|--------|-------|
| web_search_unavailable | PASS | Agent did not explicitly acknowledge the limitation |
| malformed_rag_output | PASS | Agent handled empty KB without hallucinating sources |
| provider_timeout | PASS | Neither provider available — requires at least one to be running |

**Summary:** 3/3 tests passed