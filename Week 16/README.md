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
7. [Methodologies and Problem-Solving](#methodologies-and-problem-solving)
8. [Challenges Faced](#challenges-faced)
9. [Setup and Running](#setup-and-running)
10. [Results Summary](#results-summary)

---

## A. Context Engineering Technique

**Technique: Compaction with Evidence Bounding**

### Implementation

The `ContextManager` (`app/agent/context_manager.py`) implements a two-stage context management strategy:

1. **Evidence Bounding**: Each tool result is capped at 3,000 characters on insertion. This prevents any single source from dominating the context window.

2. **Compaction**: When accumulated evidence exceeds 6,000 characters, the manager invokes an LLM summarizer to compress findings into a 2,000-character summary. The summary preserves:
   - Source identifiers (document names, URLs)
   - Disagreements between sources
   - Error notes and unavailable sources

3. **Fallback**: If the summarizer fails, deterministic truncation is applied as a safe fallback.

### Where It Applies

Compaction runs at the start of each agentic loop iteration, before the model decides its next action. This prevents context window overflow during multi-step verification where the agent searches the knowledge base, web, and runs calculations.

### Problem Solved

Without compaction, a 5-iteration cross-source verification query would accumulate 10,000+ characters of tool outputs, exceeding the model's effective context window and degrading response quality. Compaction bounds context growth while retaining the most relevant evidence.

### Code Reference

```python
# app/agent/context_manager.py
class ContextManager:
    def add_finding(self, source, text):
        # Cap individual findings at 3000 chars
        if len(text) > 3000:
            text = text[:3000] + "...[truncated]"
        self._findings.append({"source": source, "text": text, "timestamp": time.time()})
    
    def should_compact(self):
        return self.total_chars() > self._compact_threshold
    
    async def compact(self, summarizer):
        # LLM-based summarization with fallback to truncation
        ...
```

---

## B. Agentic Pattern

**Pattern: Single-Agent Bounded Loop**

### Why Single-Agent

The implementation uses a single-agent bounded loop (`app/agent/loop.py`) where the LLM decides at each iteration whether to:

1. **Search the knowledge base** (`search_knowledge`) — vector similarity search over ingested documents
2. **Search the web** (`web_search`) — real-time web search via DuckDuckGo/Startpage/Yahoo
3. **Use a calculator** (`calculator`) — evaluate mathematical expressions
4. **Get current datetime** (`get_current_datetime`) — retrieve current date and time
5. **Provide a final answer** (`answer`) — synthesize evidence into a response
6. **Ask for clarification** (`ask_user`) — request missing information

### Design Rationale

| Consideration | Decision |
|--------------|----------|
| Task type | Sequential reasoning over sources — no parallelization benefit |
| Context isolation | Not needed — single agent maintains coherent context |
| Specialization | Tool selection handled by the single agent's reasoning |
| Coordination cost | Multi-agent would add overhead without improving results |

### Self-Verification Limitation

The same model that gathers evidence also evaluates it. This is acceptable because:
- Each source provides independent information (no circular reasoning)
- Tool outputs are factual (search results, calculations) not model-generated
- Cross-source comparison is explicit (sources are labeled in findings)

However, the agent cannot detect subtle hallucinations within a single source — only disagreements *between* sources.

### Stopping Conditions

The loop stops when:
- The model calls `answer` (successful completion)
- The model calls `ask_user` (clarification needed)
- An unrecovered error occurs (provider failure)
- Maximum iterations reached (configurable 1-5, default 5)

At the final iteration, only `answer` and `ask_user` tools are available, forcing the model to produce a response rather than continue researching.

### Duplicate Call Prevention

The loop tracks successful calls and prevents:
1. **Exact duplicates**: Same tool + same arguments → reuses cached result
2. **Similar queries**: For `search_knowledge` and `web_search`, queries sharing >70% of words are treated as duplicates

---

## C. Evaluation Harness

### Framework Design

A custom Python evaluation framework (`app/evaluation/`) built from scratch without external evaluation libraries.

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Harness | `harness.py` | Runs queries, evaluates against rubrics, produces reports |
| Test Queries | `test_queries.py` | 10 test queries across 3 difficulty levels |
| Failure Injection | `failure_injection.py` | 3 controlled failure injection tests |
| Runner | `run_evaluation.py` | CLI with `--mode offline|live`, `--delay`, `--ids` options |

### Expected Stop States

| Query | Expected Stop | Reason |
|-------|--------------|--------|
| simple_01 (RAG) | `answer` | Cross-source verification complete |
| simple_02 (datetime) | `answer` | Single tool, immediate answer |
| simple_03 (calculator) | `answer` | Single tool, immediate answer |
| moderate_01 (Python) | `answer` | KB + web comparison |
| moderate_02 (AI accuracy) | `answer` | Multi-source verification |
| moderate_03 (chunking) | `answer` | KB search sufficient |
| complex_01-04 | `answer` | Multi-source synthesis |

Queries that hit max iterations stop at iteration 5 even if verification is incomplete.

### Metrics Measured

1. **Task Completion Rate**: Does the agent successfully answer the query?
2. **Tool-Call Correctness**: Does the agent select appropriate tools with valid arguments?
3. **Trajectory Length**: How many iterations does each query require?
4. **Token Usage**: Total prompt and completion tokens per query
5. **Duration**: End-to-end time per query

### Evaluation Taxonomy

| Failure Type | Definition | Example |
|-------------|------------|---------|
| **Hard failure** | Execution failure — agent crashes, throws exception, or returns error | Provider timeout with no fallback |
| **Soft failure** | Misses a rubric criterion or trajectory expectation | Correct answer but wrong tool used |
| **Cascading-soft** | Tool failure → later tool actions → unmet rubric | web_search fails → agent uses only KB → misses web-specific info |

**Human review** is required to establish causality and verify citation support. Automated scoring catches rubric misses but not subtle reasoning errors.

### Rubric Design

- **Flat argument schemas**: Tools expect simple key-value arguments (no nested objects)
- **Lexical answer rubrics**: Each query has expected keywords/phrases; answer must contain at least one
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

### Failure Injection Tests

| Test | Failure Type | Expected Behavior |
|------|-------------|-------------------|
| Web search unavailable | Tool exception | Agent acknowledges limited sources, uses KB only |
| Malformed RAG output | Corrupted data | Agent falls back to web search |
| Provider timeout | API timeout | Fallback to secondary provider triggered |

---

## Additional Requirements

### 1. Skill vs. Agent

**Decision: Agent (not Skill)**

A Skill could describe verification instructions, but needs an execution host to retrieve data and branch on results. This project provides that host as a bounded loop and wraps the existing retriever as `search_knowledge`. The `answer` and `ask_user` are control actions, not additional agents.

**Key Distinction:**
- **Skill**: Static instructions for how to perform a task
- **Agent**: Dynamic execution with tool use, state management, and decision-making

This implementation is an agent because it:
- Maintains state across iterations (accumulated evidence)
- Makes dynamic decisions (which tool to call next)
- Handles errors and retries
- Has stopping conditions based on evidence quality

### 2. Token and Cost Accounting

Query totals include successful decision and compaction responses. Local generation uses the tokenizer; API totals include reported usage from the provider.

| Query | Prompt Tokens | Completion Tokens | Total |
|-------|--------------|-------------------|-------|
| simple_01 | 2,735 | 235 | 2,970 |
| simple_02 | 3,092 | 844 | 3,936 |
| simple_03 | 3,140 | 348 | 3,488 |
| moderate_02 | 5,102 | 338 | 5,440 |

**Note**: Failed calls can have unknown consumption, making recorded totals a lower bound.

### 3. Failure Injection Test

Tests inject exceptions into the actual search executor and verify:
1. The next decision sees the error
2. The error is excluded from successful sources
3. A scripted response acknowledges inability to verify

A separate test forces a provider timeout and checks that the configured fallback (OpenRouter) is triggered correctly.

### 4. Tool vs. Agent Boundary

**Web search is modeled as a tool, not an agent:**

- Single bounded request with at most 5 results
- 10-second client timeout
- Returns one consolidated result to the assistant
- The assistant owns research state and chooses the next action
- No delegated autonomous goal or agent-to-agent conversation

---

## Architecture

### Visual Diagrams

| Diagram | Description | File |
|---------|-------------|------|
| System Architecture | Complete system overview with all components | [architecture/images/system-architecture.png](architecture/images/system-architecture.png) |
| Data Flow | Request/response flow through the system | [architecture/images/data-flow.png](architecture/images/data-flow.png) |
| Rate Limit Flow | Provider fallback and rate limit handling | [architecture/images/rate-limit-flow.png](architecture/images/rate-limit-flow.png) |

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│                     (Streamlit / curl)                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │ POST /chat/agentic
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                            │
│                     (app/main.py)                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agentic Loop                                 │
│                   (app/agent/loop.py)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Iteration 1..5                                          │  │
│  │  ┌─────────┐    ┌──────────────┐    ┌────────────────┐  │  │
│  │  │  LLM    │───▶│ Tool Decision │───▶│ Tool Execution │  │  │
│  │  │ Provider │◀───│   (model)    │◀───│   (registry)   │  │  │
│  │  └─────────┘    └──────────────┘    └────────────────┘  │  │
│  │       │                                  │               │  │
│  │       ▼                                  ▼               │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │         Context Manager (compaction)             │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Groq API    │ │ OpenRouter   │ │   Tools      │
│  (Primary)   │ │ (Fallback)   │ │  Registry    │
│  5-key       │ │ Free-tier    │ │              │
│  rotation    │ │ model        │ │ ┌──────────┐ │
└──────┬───────┘ └──────────────┘ │ │calculator│ │
       │                          │ │web_search│ │
       ▼                          │ │datetime  │ │
┌──────────────┐                  │ │knowledge │ │
│  Rate Limit  │                  │ └──────────┘ │
│  Management  │                  └──────────────┘
│  - retry-after│                        │
│  - key rotate │                        ▼
│  - backoff    │                  ┌──────────────┐
└──────────────┘                  │ RAG Pipeline │
                                   │ ChromaDB     │
                                   │ embeddings   │
                                   └──────────────┘
```

### Data Flow

```
User Query
    │
    ▼
Agentic Loop (iteration 1)
    │
    ├──▶ LLM Decision: search_knowledge("RAG best practices")
    │        │
    │        ▼
    │    ChromaDB Vector Search
    │        │
    │        ▼
    │    Evidence: [Source 1: rag_guide.md, Source 2: ...]
    │
    ├──▶ LLM Decision: web_search("RAG vs fine-tuning 2024")
    │        │
    │        ▼
    │    DuckDuckGo / Startpage / Yahoo
    │        │
    │        ▼
    │    Evidence: [URL 1: ibm.com, URL 2: ...]
    │
    ├──▶ Context Manager: compact if > 6000 chars
    │
    ▼
Agentic Loop (iteration 2)
    │
    ├──▶ LLM Decision: answer(synthesized response)
    │
    ▼
Final Answer with source citations
```

---

## APIs Used and Tried

### Primary: Groq API

| Property | Value |
|----------|-------|
| Endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| Model | `openai/gpt-oss-20b` |
| Authentication | API key (5 keys for rotation) |
| Rate Limit | 8,000 tokens/min per organization |
| Request Limit | 1,000 requests/2 hours per key |

**Key Features Used:**
- OpenAI-compatible chat completions
- Native tool/function calling
- `retry-after` header for rate limit handling
- `reasoning_effort` parameter for model control

### Fallback: OpenRouter API

| Property | Value |
|----------|-------|
| Endpoint | `https://openrouter.ai/api/v1/chat/completions` |
| Model | `nvidia/nemotron-3-super-120b-a12b:free` |
| Authentication | API key |
| Rate Limit | Free tier (strict per-request limits) |

**Key Features Used:**
- OpenAI-compatible format
- Tool calling support
- Free-tier model routing

### APIs Tried and Rejected

| API | Reason for Rejection |
|-----|---------------------|
| Google Gemini | Deprecated `google-generativeai` SDK; replaced with Groq |
| Local vLLM | Requires GPU; not available in assignment environment |
| Local Transformers | Slow inference; not suitable for real-time agentic loop |
| `nvidia/nemotron-3.5-lightning:free` | Emits chain-of-thought reasoning in responses; not suitable for clean answer extraction |

### Embedding API

| Property | Value |
|----------|-------|
| Model | `all-MiniLM-L6-v2` (Sentence-Transformers) |
| Dimensions | 384 |
| Library | `sentence-transformers` via `chromadb` |

---

## Methodologies and Problem-Solving

### 1. Multi-Key Rotation with Exponential Backoff

**Problem**: Single API key quickly exhausts rate limits.

**Solution**: 5-key rotation with exponential backoff (2s → 4s → 8s).

```python
# groq.py
BACKOFF_SEQUENCE = [2, 4, 8]  # seconds between rotations

for offset in range(num_keys):
    slot = (self._active + offset) % num_keys
    if offset > 0:
        await self._sleep(backoff)
    response = await self._post_with_rate_retry(client, payload, slot)
```

**Key Design Decisions:**
- 429 (quota) never triggers credential rotation — respects organization-level limits
- 5xx errors trigger rotation — handles transient server issues
- 4xx auth errors stop immediately — prevents key leakage

### 2. Evidence-Based Rate Limit Handling

**Problem**: Hardcoded delays don't match actual API limits.

**Solution**: Read `retry-after` and `x-ratelimit-reset-*` headers from 429 responses.

```python
# groq.py
retry_after = response.headers.get("retry-after", "")
rate_limit_reset = response.headers.get("x-ratelimit-reset-tokens", "")

# Use retry-after if available, otherwise default to 60s
delay = max(1, float(retry_after)) if retry_after else 60
```

### 3. Token-Aware Pacing

**Problem**: Fixed delays waste time or exceed limits.

**Solution**: Track token usage in a sliding window and pace accordingly.

```python
# groq.py
async def _pace(self, payload, actual_tokens=0):
    cost = actual_tokens if actual_tokens > 0 else self._estimate_tokens(payload)
    while True:
        # Purge old reservations (>61s)
        while self._reservations and self._reservations[0][0] <= now - 61:
            self._reservations.popleft()
        if sum(c for _, c in self._reservations) + cost <= self._budget:
            self._reservations.append((now, cost))
            return
        await self._sleep(delay)
```

### 4. Similar Query Deduplication

**Problem**: Model rephrases queries slightly, bypassing exact-match dedup.

**Solution**: Word-overlap detection (>70% shared words = duplicate).

```python
# loop.py
words1 = set(normalized.split())
words2 = set(prev_query.split())
overlap = len(words1 & words2) / max(len(words1 | words2), 1)
if overlap > 0.7:
    # Treat as duplicate, reuse cached result
```

### 5. Fallback Chain with Tool Recovery

**Problem**: Fallback provider may not support tool calling.

**Solution**: Three-tier recovery:
1. Try with tools (native function calling)
2. On HTTP 400: retry without tools (text-only)
3. On plain text response: adapt to answer tool call

```python
# openrouter.py
if response.status_code == 400:
    # Retry without tools
    text_payload = {k: v for k, v in payload.items() 
                    if k not in ("tools", "tool_choice")}
    retry_response = await client.post(..., json=text_payload)

# loop.py
if response.content and not response.tool_calls:
    # Treat plain text as answer
    calls = [ToolCall(name="answer", arguments={"answer": response.content})]
```

### 6. HTTP 400 Diagnostic Logging

**Problem**: Groq returns 400 but error details are lost.

**Solution**: Log full error body and payload keys for diagnosis.

```python
# groq.py
if response.status_code == 400:
    err_body = response.json()
    err_code = err_body.get("error", {}).get("code")
    err_msg = err_body.get("error", {}).get("message", "")
    logger.error("Groq HTTP 400: code=%s msg=%s payload_keys=%s",
                 err_code, err_msg[:200], list(payload.keys()))
```

---

## Challenges Faced

### 1. Groq Shared Organization Quota

**Challenge**: 5 API keys don't provide 5× the capacity. Groq limits are per-organization, not per-key.

**Impact**: After the first query, subsequent queries hit 429 immediately.

**Mitigation**: 
- Evidence-based pacing using `retry-after` header (120s)
- Fallback to OpenRouter when Groq is exhausted
- Documented as a free-tier limitation

### 2. OpenRouter Chain-of-Thought Model

**Challenge**: `nvidia/nemotron-3.5-lightning:free` emits visible reasoning ("Here's a thinking process:") instead of direct answers.

**Impact**: Answers contained thinking steps instead of final responses.

**Solution**: Swapped to `nvidia/nemotron-3-super-120b-a12b:free` which produces clean instruct-style outputs.

### 3. OpenRouter Rate Limiting

**Challenge**: OpenRouter free tier also has strict per-request rate limits.

**Impact**: When Groq fails and we fall back to OpenRouter, consecutive requests get 429.

**Solution**: Added 30-second minimum interval between OpenRouter requests.

### 4. Tool Call Format Rejection

**Challenge**: Groq occasionally returns HTTP 400 with `tool_use_failed` code.

**Impact**: Agentic loop breaks on tool calling errors.

**Solution**: Three-tier recovery:
1. Retry with text decision protocol (ACTION:/ANSWER:/CLARIFY:)
2. Retry without tools (text-only)
3. Raise error if both fail

### 5. Answer Truncation on Complex Queries

**Challenge**: `max_tokens=768` too low for cross-source synthesis.

**Impact**: Answers cut off mid-sentence.

**Solution**: Increased `max_tokens` to 1024.

### 6. Model Not Using Expected Tools

**Challenge**: Model answers directly from initial RAG context without calling tools.

**Impact**: Evaluation marks query as "tools=False" even though answer is correct.

**Solution**: Updated system prompt to require tool verification, added short-circuit for simple queries.

---

## Setup and Running

### Prerequisites

- Python 3.12+
- 5 Groq API keys (free tier)
- 1 OpenRouter API key (free tier)

### Installation

```bash
cd task1-ai-assistant
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
```

### Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### Running Evaluations

```bash
# Offline scripted tests (no API calls)
python -m app.evaluation.run_evaluation --mode offline

# Live evaluation with Groq (requires API keys)
python -m app.evaluation.run_evaluation --mode live --delay 65

# Run specific queries
python -m app.evaluation.run_evaluation --mode live --ids simple_01 simple_02 simple_03

# Failure injection tests
python -m app.evaluation.run_evaluation --mode live --failure-injection

# Regression tests
python -m unittest discover -s tests -v
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/chat` | POST | Standard chat with RAG |
| `/chat/agentic` | POST | Agentic cross-source verification |
| `/chat/structured` | POST | Structured JSON output |
| `/documents/ingest` | POST | Ingest text into knowledge base |
| `/documents/upload` | POST | Upload and ingest document |
| `/documents/stats` | GET | RAG pipeline statistics |
| `/tools` | GET | List available tools |
| `/config` | GET | Current configuration |

---

## Results Summary

### Regression Tests

**34/34 tests passing**

| Test Category | Count | Status |
|--------------|-------|--------|
| Agentic Loop Behavior | 12 | ✅ All Pass |
| Groq Provider | 8 | ✅ All Pass |
| OpenRouter Provider | 3 | ✅ All Pass |
| Provider Recovery | 7 | ✅ All Pass |
| Production Startup | 1 | ✅ All Pass |
| API Validation | 3 | ✅ All Pass |

### Offline Evaluation (Scripted Fixtures)

| Metric | Value |
|--------|-------|
| Total Queries | 4 |
| Task Completion | 50% |
| Tool Correctness | 100% |
| Avg Trajectory | 1.5 iterations |

### Live Evaluation (Groq + OpenRouter)

| Query | Difficulty | Status | Tools | Iterations | Notes |
|-------|-----------|--------|-------|------------|-------|
| simple_01 | simple | ✅ PASS | search_knowledge, web_search | 3 | Cross-source verification works |
| simple_02 | simple | ✅ PASS | get_current_datetime | 2 | Single-tool query succeeds |
| simple_03 | simple | ✅ PASS | calculator | 2 | Single-tool query succeeds |
| moderate_02 | moderate | ✅ PASS | web_search, search_knowledge | 5 | Multi-iteration works when API available |
| moderate_01 | moderate | ❌ FAIL | — | — | Groq 429 on 2nd iteration |
| moderate_03 | moderate | ❌ FAIL | — | — | Both providers rate limited |
| complex_01-04 | complex | ❌ FAIL | — | — | Both providers rate limited |

### Overall Metrics

| Metric | Value |
|--------|-------|
| Task Completion (Live) | 40% (4/10) |
| Tool Correctness (Live) | 75% (3/4 successful) |
| Regression Tests | 34/34 (100%) |
| Offline Evaluation | 50% completion, 100% tool correctness |

### Key Finding

The agentic loop works correctly when API limits are not exceeded. The primary limitation is Groq's free-tier rate limit (8,000 tokens/min per organization), which prevents multi-iteration queries from completing consecutively. With proper pacing (65-120s between queries), simple and moderate queries succeed.

---

## File Structure

```
task1-ai-assistant/
├── app/
│   ├── __init__.py
│   ├── config.py              # Settings and environment variables
│   ├── main.py                # FastAPI application
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── loop.py            # Agentic loop implementation
│   │   └── context_manager.py # Context compaction
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py        # Base provider and factory
│   │   ├── groq.py            # Groq API provider
│   │   ├── openrouter.py      # OpenRouter fallback provider
│   │   └── openai_client.py   # OpenAI-compatible client
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py        # Tool registry
│   │   ├── calculator.py      # Math calculations
│   │   ├── web_search.py      # Web search + datetime
│   │   └── knowledge_search.py # RAG knowledge base search
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── retriever.py       # RAG retriever
│   │   ├── chunking.py        # Document chunking
│   │   ├── embeddings.py      # Sentence embeddings
│   │   └── ingestion.py       # Document ingestion
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── system_prompts.py  # System prompts
│   └── evaluation/
│       ├── __init__.py
│       ├── harness.py         # Evaluation harness
│       ├── test_queries.py    # 10 test queries
│       ├── failure_injection.py # Failure injection tests
│       ├── run_evaluation.py  # CLI runner
│       └── RESULTS.md         # Results report
├── tests/
│   ├── test_week16.py         # Behavioral tests
│   ├── test_agentic_api.py    # API endpoint tests
│   ├── test_gemini_keys.py    # Groq provider tests
│   └── test_provider_recovery.py # Recovery tests
├── data/
│   └── sample_docs/           # Ingested documents
├── .env.example               # Environment template
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container build
└── README.md                  # This file
```
