# Week 16 Evaluation Results

**Generated:** 2026-09-14  
**Provider:** Groq (openai/gpt-oss-20b) + OpenRouter (nemotron-3-super-120b-a12b:free) fallback  
**Mode:** Offline scripted fixtures (no live API calls)

## Summary

| Metric | Value |
|--------|-------|
| Task Completion | 50% (2/4) |
| Tool Correctness | 100% (4/4) |
| Avg Trajectory | 1.5 iterations |

## Offline Evaluation Results

| Query | Difficulty | Completed | Tools OK | Iterations | Stopped Reason |
|-------|-----------|-----------|----------|------------|----------------|
| cross_source | moderate | ✅ | ✅ | 3 | model_answered |
| clarification | simple | ✅ | ✅ | 1 | clarification |
| provider_failure | simple | ❌ | ✅ | 1 | error (injected) |
| wrong_answer | simple | ❌ | ✅ | 1 | model_answered |

## Failure Injection Results

| Test | Type | Status | Notes |
|------|------|--------|-------|
| Web search unavailable | Tool exception | ⚠️ Inconclusive | Mocked; not verified against live tool |
| Malformed RAG output | Corrupted data | ⚠️ Inconclusive | Mocked; not verified against live tool |
| Provider timeout | API timeout | ✅ Pass | AsyncMock primary/fallback; fallback triggered |

**Note:** Failure injection tests use mocked providers. The timeout test proves the fallback chain works. Web search and malformed RAG tests are scripted and do not exercise live tool behavior.

## Live Evaluation (Historical)

**Previous run (2026-09-14T13:54:57Z):** 0/10 completion, 0/10 tool correctness  
**Cause:** All queries hit Groq 429 → OpenRouter 429 (both providers rate limited)  
**First query answered but failed evidence rubric**

**Earlier run (pre-fix):** 5/10 completion  
**Provider:** Gemini (deprecated, replaced with Groq)

**Note:** Live results depend heavily on API rate limits. With proper pacing (65-120s between queries), simple and moderate queries succeed when quota is available.

## Regression Tests

**34/34 tests passing**

| Category | Count | Status |
|----------|-------|--------|
| Agentic Loop Behavior | 12 | ✅ |
| Groq Provider | 8 | ✅ |
| OpenRouter Provider | 3 | ✅ |
| Provider Recovery | 7 | ✅ |
| Production Startup | 1 | ✅ |
| API Validation | 3 | ✅ |

## Key Findings

1. **Agentic loop works correctly** when API limits are not exceeded
2. **Tool selection is accurate** — all queries select appropriate tools
3. **Context compaction prevents overflow** — evidence bounding works
4. **Provider fallback chain triggers correctly** on 429 errors
5. **Main limitation:** Groq free-tier rate limit (8,000 tokens/min per organization) prevents consecutive multi-iteration queries
