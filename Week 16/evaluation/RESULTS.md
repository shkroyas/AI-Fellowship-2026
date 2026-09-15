# Week 16 Evaluation Results

**Last Updated:** 2026-09-15

## Summary

| Metric | Offline | Live (Best — Gemini) | Live (Groq) |
|--------|---------|----------------------|-------------|
| Task Completion | 50% (2/4) | 50% (5/10) | 0–30% (0–3/10) |
| Tool Correctness | 100% (4/4) | 60% (6/10) | N/A |
| Regression Tests | 24/24 | — | — |

## Offline Evaluation Results

| Query | Difficulty | Completed | Tools OK | Iterations | Stopped Reason |
|-------|-----------|-----------|----------|------------|----------------|
| cross_source | moderate | ✅ | ✅ | 3 | model_answered |
| clarification | simple | ✅ | ✅ | 1 | clarification |
| provider_failure | simple | ❌ | ✅ | 1 | error (injected) |
| wrong_answer | simple | ❌ | ✅ | 1 | model_answered |

## Live Evaluation — Best Run (Gemini 3.6-flash)

**Date:** 2026-09-13T04:25:16 UTC  
**Provider:** Gemini 3.6-flash  
**Pacing:** 15s between queries  
**Duration:** 523.3s  

| Query | Difficulty | Completed | Tools Used | Iterations | Notes |
|-------|-----------|-----------|------------|------------|-------|
| simple_01 — "What is RAG?" | simple | ✅ | search_knowledge | 3 | Detailed answer |
| simple_02 — "Current datetime?" | simple | ✅ | get_current_datetime | 2 | Perfect |
| simple_03 — "Calculate 15% of 340" | simple | ✅ | calculator | 2 | Correct (51.0) |
| moderate_01 — "Python best practices" | moderate | ✅ | search_knowledge + web_search | 4 | Cross-source |
| moderate_02 — "AI docs accuracy" | moderate | ✅ | search_knowledge + web_search | 3 | Cross-source |
| moderate_03 — "Chunking strategies" | moderate | ❌ | search_knowledge | 5 | Hit max iterations |
| complex_01 — "RAG vs fine-tuning" | complex | ❌ | — | — | HTTP 429 |
| complex_02 — "Local vs cloud LLMs" | complex | ❌ | — | — | HTTP 429 |
| complex_03 — "Embedding models" | complex | ❌ | — | — | HTTP 429 |
| complex_04 — "Chunk size" | complex | ❌ | — | — | HTTP 429 |

**Root cause of failures:** Gemini free-tier quota exhausted after 5 successful queries. All 4 complex queries hit HTTP 429 immediately.

## Live Evaluation — Groq Runs

**Best Groq result:** 30% (3/10) — simple_01, simple_02, simple_03 completed  
**Full Groq run:** 0/10 — all queries hit Groq 429 → OpenRouter 429  
**Limitation:** Groq free-tier (8,000 tokens/min) exhausted by multi-iteration queries

## Failure Injection Results

| Test | Type | Status | Notes |
|------|------|--------|-------|
| Web search unavailable | Tool exception | ⚠️ Inconclusive | Mocked; provider failed before injection test |
| Malformed RAG output | Corrupted data | ⚠️ Inconclusive | Mocked; provider failed before injection test |
| Provider timeout | API timeout | ✅ Pass | AsyncMock primary/fallback; fallback triggered |

## Regression Tests

**24/24 tests passing**

| Category | Count | Status |
|----------|-------|--------|
| Agentic Loop Behavior | 12 | ✅ |
| Provider Recovery | 7 | ✅ |
| API Validation | 3 | ✅ |
| Production Startup | 1 | ✅ |
| Tool Registry | 1 | ✅ |

## Key Findings

1. **Agentic loop works correctly** — all tool selection and evidence accumulation logic verified
2. **Tool correctness is high** — 60–100% depending on provider availability
3. **Context compaction prevents overflow** — 6K threshold with 2K summaries works
4. **Provider fallback chain triggers correctly** on 429 errors
5. **Main limitation:** Free-tier rate limits (Groq 8K tokens/min, Gemini daily quota) prevent full 10-query live evaluation with complex queries
6. **Complex queries never succeeded live** — they require 3+ LLM iterations which exhaust the free-tier budget after simpler queries consume it
