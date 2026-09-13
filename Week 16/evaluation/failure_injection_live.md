Live provider: gemini-3.6-flash; delay 15.0s per call

# Failure Injection Test Report

| Test | Passed | Notes |
|------|--------|-------|
| web_search_unavailable | INCONCLUSIVE | Provider unavailable before autonomous recovery could be assessed |
| malformed_rag_output | INCONCLUSIVE | Provider unavailable before autonomous recovery could be assessed |
| provider_timeout | PASS | Injected TimeoutError into the real loop; scripted fallback invoked. This tests orchestration, not live model quality. |

**Summary:** 1/3 tests passed
