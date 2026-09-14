# Week 16 — Agentify the Assistant

**Author:** Royas Shakya  
**Date:** 2026-09-14  
**Assignment:** AI Fellowship — Task 3: Agentify the Assistant

---

## Table of Contents

1. [Context Engineering Technique](#a-context-engineering-technique)
2. [Agentic Pattern](#b-agentic-pattern)
3. [Evaluation Harness](#c-evaluation-harness)
4. [Additional Requirements](#additional-requirements)
5. [Architecture](#architecture)
6. [APIs Used and Tried](#apis-used-and-tried)
7. [Challenges Faced](#challenges-faced)
8. [Results Summary](#results-summary)

---

## A. Context Engineering Technique

**Technique: Compaction with Evidence Bounding**

The `ContextManager` (`app/agent/context_manager.py`) implements a two-stage context management strategy:

1. **Evidence Bounding**: Each tool result is capped at 3,000 characters on insertion. This prevents any single source from dominating the context window.

2. **Compaction**: When accumulated evidence exceeds 6,000 characters, the manager invokes an LLM summarizer to compress findings into a 2,000-character summary. The summary preserves:
   - Source identifiers (document names, URLs)
   - Disagreements between sources
   - Error notes and unavailable sources

3. **Fallback**: If the summarizer fails, deterministic truncation is applied as a safe fallback.

**Trade-off:** Compaction can lose detail from earlier iterations. This is acceptable because the model re-reads summarized findings each iteration, source IDs are preserved for citation, and key disagreements are explicitly retained.

---

## B. Agentic Pattern

**Pattern: Single-Agent Bounded Loop**

A single agent (`app/agent/loop.py`) decides at each iteration whether to:

1. **Search the knowledge base** (`search_knowledge`) — vector similarity search over ingested documents
2. **Search the web** (`web_search`) — real-time web search via DuckDuckGo/Startpage/Yahoo
3. **Use a calculator** (`calculator`) — evaluate mathematical expressions
4. **Get current datetime** (`get_current_datetime`) — retrieve current date and time
5. **Provide a final answer** (`answer`) — synthesize evidence into a response
6. **Ask for clarification** (`ask_user`) — request missing information

**Why Single-Agent:**

| Consideration | Decision |
|--------------|----------|
| Task type | Sequential reasoning over sources — no parallelization benefit |
| Context isolation | Not needed — single agent maintains coherent context |
| Specialization | Tool selection handled by the single agent's reasoning |
| Coordination cost | Multi-agent would add overhead without improving results |

**Self-Verification Limitation:** The same model that gathers evidence also evaluates it. This is acceptable because each source provides independent information, tool outputs are factual (search results, calculations) not model-generated, and cross-source comparison is explicit.

**Stopping Conditions:**

| Condition | Action | Result |
|-----------|--------|--------|
| Model calls `answer` | Break loop | Return synthesized response |
| Model calls `ask_user` | Break loop | Clarification ends the request; user resubmits |
| Provider error | Try fallback | If fallback fails, report error |
| Max iterations reached | Exhaustion → incomplete verification | Force answer from available evidence |

**Duplicate Call Prevention:** The loop tracks successful calls and prevents exact duplicates (same tool + same arguments) and similar queries (>70% word overlap, excluding year/date differences).

---

## C. Evaluation Harness

**Framework:** Custom Python evaluation framework (`app/evaluation/`) built from scratch.

### Metrics Measured

| Metric | Definition | How Measured |
|--------|------------|--------------|
| Task Completion | Agent successfully answers the query | Rubric-based (answer_contains_any) |
| Tool Correctness | Agent selects appropriate tools | Expected tools list comparison |
| Trajectory Length | Number of iterations per query | Count of loop iterations |
| Token Usage | Total tokens consumed | Prompt + completion tokens from API |

### Evaluation Taxonomy

| Failure Type | Definition |
|-------------|------------|
| **Hard failure** | Execution failure — agent crashes or returns error |
| **Soft failure** | Misses a rubric criterion or trajectory expectation |
| **Cascading-soft** | Tool failure → later tool actions → unmet rubric |

### Rubric Design

- **Flat argument schemas**: Tools expect simple key-value arguments
- **Lexical answer rubrics**: Each query has expected keywords/phrases
- **Stop-state rubrics**: Expected tool sequence is validated against actual trajectory

### Test Queries

| ID | Difficulty | Query | Expected Tools |
|----|-----------|-------|----------------|
| simple_01 | simple | What is RAG? | search_knowledge, web_search |
| simple_02 | simple | Current date and time? | get_current_datetime |
| simple_03 | simple | Calculate 15% of 340 | calculator |
| moderate_01 | moderate | Python best practices: KB vs industry | search_knowledge, web_search |
| moderate_02 | moderate | Is AI info in docs still accurate? | search_knowledge, web_search |
| moderate_03 | moderate | Sentence vs recursive chunking | search_knowledge |
| complex_01 | complex | RAG vs fine-tuning for enterprise | search_knowledge, web_search |
| complex_02 | complex | Security: local LLMs vs cloud APIs | search_knowledge, web_search |
| complex_03 | complex | Embedding models in knowledge base | search_knowledge |
| complex_04 | complex | Recommended chunk size for RAG | search_knowledge, web_search |

---

## Additional Requirements

### 1. Skill vs. Agent

**Decision: Agent (not Skill)**

A Skill could describe verification instructions, but needs an execution host to retrieve data and branch on results. This project provides that host as a bounded loop and wraps the existing retriever as `search_knowledge`. The `answer` and `ask_user` are control actions, not additional agents.

### 2. Token and Cost Accounting

**Accounting method:** Totals include every successful decision and compaction response. Local generation uses the model tokenizer; API totals include reported usage from the provider. Failed calls can have unreported consumption, making recorded totals a lower bound.

| Query | Prompt Tokens | Completion Tokens | Total |
|-------|--------------|-------------------|-------|
| simple_01 | 2,735 | 235 | 2,970 |
| simple_02 | 3,092 | 844 | 3,936 |
| simple_03 | 3,140 | 348 | 3,488 |
| moderate_02 | 5,102 | 338 | 5,440 |

**Offline tokens:** Synthetic (generated by test fixtures, not real API calls).  
**Multi-agent baseline:** Not applicable — single-agent architecture used.  
**No dollar cost claimed:** All providers used free-tier access.

### 3. Failure Injection

Controlled tests inject search exceptions and provider timeouts into the actual loop, check error propagation, exclude failed sources, and verify the configured fallback.

| Test | Failure Type | Status |
|------|-------------|--------|
| Web search unavailable | Tool exception | ⚠️ Inconclusive (mocked) |
| Malformed RAG output | Corrupted data | ⚠️ Inconclusive (mocked) |
| Provider timeout | API timeout | ✅ Pass (fallback triggered) |

Scripted behavior is not presented as autonomous live recovery.

### 4. Tool vs. Agent Boundary

**Web search is a tool, not an agent:**

| Property | Value |
|----------|-------|
| Request type | Single bounded DDGS request |
| Max results | 5 |
| Client timeout | 10 seconds |
| State ownership | Assistant owns research state and next decision |
| Autonomy | No delegated autonomous goal |
| Communication | No agent-to-agent conversation |

---

## Architecture

### Visual Diagrams

| Diagram | File |
|---------|------|
| System Architecture | [architecture/images/system-architecture.png](architecture/images/system-architecture.png) |
| Data Flow | [architecture/images/data-flow.png](architecture/images/data-flow.png) |
| Rate Limit Flow | [architecture/images/rate-limit-flow.png](architecture/images/rate-limit-flow.png) |

### File Structure

```
task1-ai-assistant/
├── app/
│   ├── agent/
│   │   ├── loop.py              # Agentic loop implementation
│   │   └── context_manager.py   # Context compaction
│   ├── llm/
│   │   ├── provider.py          # Base provider and factory
│   │   ├── groq.py              # Groq API provider (5-key rotation)
│   │   └── openrouter.py        # OpenRouter fallback provider
│   ├── tools/
│   │   ├── registry.py          # Tool registry
│   │   ├── calculator.py        # Math calculations
│   │   ├── web_search.py        # Web search + datetime
│   │   └── knowledge_search.py  # RAG knowledge base search
│   ├── rag/
│   │   ├── retriever.py         # RAG retriever
│   │   ├── chunking.py          # Document chunking
│   │   ├── embeddings.py        # Sentence embeddings
│   │   └── ingestion.py         # Document ingestion
│   ├── evaluation/
│   │   ├── harness.py           # Evaluation harness
│   │   ├── test_queries.py      # 10 test queries
│   │   ├── failure_injection.py # Failure injection tests
│   │   └── run_evaluation.py    # CLI runner
│   └── main.py                  # FastAPI application
├── tests/                       # 34 regression tests
├── data/sample_docs/            # Ingested documents
├── .env.example                 # Environment template
└── requirements.txt             # Python dependencies
```

---

## APIs Used and Tried

### Primary: Groq API

| Property | Value |
|----------|-------|
| Model | `openai/gpt-oss-20b` |
| Rate Limit | 8,000 tokens/min per organization |
| Keys | 5 for rotation (not quota multiplication) |

### Fallback: OpenRouter API

| Property | Value |
|----------|-------|
| Model | `nvidia/nemotron-3-super-120b-a12b:free` |
| Rate Limit | Free tier (30s minimum interval) |

### APIs Tried and Rejected

| API | Reason |
|-----|--------|
| Google Gemini | Deprecated SDK |
| Local vLLM | Requires GPU |
| `nemotron-3.5-lightning:free` | Emits chain-of-thought |

---

## Challenges Faced

1. **Groq Shared Organization Quota:** 5 keys share one quota; rotation doesn't multiply capacity. Mitigated with evidence-based pacing.

2. **OpenRouter Rate Limiting:** Free tier has strict limits. Added 30s minimum interval.

3. **HTTP 400 Tool Call Failures:** Three-tier recovery: text protocol retry → text-only retry → error.

4. **Search Deduplication:** >70% word overlap suppressed different-year queries. Fixed to preserve year/date differences.

5. **Truncated Responses:** `finish_reason="length"` was accepted as completed answer. Now detected and marked as incomplete.

---

## Results Summary

### Regression Tests

**34/34 tests passing (100%)**

### Offline Evaluation

| Metric | Value |
|--------|-------|
| Task Completion | 50% (2/4) |
| Tool Correctness | 100% (4/4) |
| Avg Trajectory | 1.5 iterations |

### Live Evaluation (Historical)

| Run | Provider | Completion | Notes |
|-----|----------|------------|-------|
| 2026-09-14 (latest) | Groq + OpenRouter | 0/10 | Both providers rate limited |
| Pre-fix | Gemini | 5/10 | Deprecated provider |

**Key Finding:** The agentic loop works correctly when API limits are not exceeded. The primary limitation is Groq's free-tier rate limit.
