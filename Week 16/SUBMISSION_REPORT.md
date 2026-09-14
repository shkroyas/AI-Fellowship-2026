# Week 16 — Agentify the Assistant

## Complete Project Report

**Author:** Royas Shakya  
**Date:** 2026-09-14  
**Assignment:** AI Fellowship — Task 3  
**Repository:** `task1-ai-assistant/`

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Implementation Process](#3-implementation-process)
4. [Context Engineering](#4-context-engineering)
5. [Agentic Pattern](#5-agentic-pattern)
6. [Evaluation Harness](#6-evaluation-harness)
7. [APIs Used and Tried](#7-apis-used-and-tried)
8. [Challenges and Solutions](#8-challenges-and-solutions)
9. [Results](#9-results)
10. [Conclusion](#10-conclusion)

---

## 1. Project Overview

### Objective

Agentify the existing Week 15 RAG assistant by adding an agentic loop that can:
- Decide which tools to use at each iteration
- Accumulate evidence across multiple sources
- Verify claims using cross-source comparison
- Synthesize answers with source citations

### Key Requirements

| Requirement | Description |
|-------------|-------------|
| Context Engineering | Compaction to manage token budget across iterations |
| Agentic Pattern | Single-agent bounded loop with tool selection |
| Evaluation Harness | Custom framework measuring task completion, tool correctness, trajectory |
| Failure Injection | Controlled tests for error handling |
| Token Accounting | Per-query token tracking |

### Deliverables

- Updated source code with agentic loop
- README with sections a, b, c + additional requirements
- Architecture diagram
- Evaluation harness with results
- 34 regression tests (all passing)

---

## 2. Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                     │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │   Streamlit UI   │    │    curl/HTTP     │    │   Postman        │      │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘      │
│           └───────────────────────┼───────────────────────┘                │
│                                   │                                         │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                     │
│                          (app/main.py)                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Endpoints:                                                         │   │
│  │  • GET  /health           → Service health check                    │   │
│  │  • POST /chat             → Standard chat with RAG                  │   │
│  │  • POST /chat/agentic     → Agentic cross-source verification       │   │
│  │  • POST /chat/structured  → Structured JSON output                  │   │
│  │  • POST /documents/ingest → Ingest text into KB                     │   │
│  │  • POST /documents/upload → Upload and ingest document              │   │
│  │  • GET  /documents/stats  → RAG pipeline statistics                 │   │
│  │  • GET  /tools            → List available tools                    │   │
│  │  • GET  /config           → Current configuration                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENTIC LOOP                                        │
│                    (app/agent/loop.py)                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ┌──────────────────────┐                         │   │
│  │                    │   LLM Provider       │                         │   │
│  │                    │   (Groq / OpenRouter)│                         │   │
│  │                    └──────────┬───────────┘                         │   │
│  │                               │                                      │   │
│  │                               ▼                                      │   │
│  │                    ┌──────────────────────┐                         │   │
│  │                    │   Decision Engine    │                         │   │
│  │                    │   (Model-directed)   │                         │   │
│  │                    └──────────┬───────────┘                         │   │
│  │                               │                                      │   │
│  │          ┌────────────────────┼────────────────────┐                │   │
│  │          ▼                    ▼                    ▼                │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │   │
│  │  │   search_    │    │  web_search  │    │  calculator  │         │   │
│  │  │  knowledge   │    │              │    │              │         │   │
│  │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘         │   │
│  │         │                    │                    │                 │   │
│  │         ▼                    ▼                    ▼                 │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │                    Tool Registry                            │  │   │
│  │  │              (app/tools/registry.py)                        │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  │                               │                                      │   │
│  │                               ▼                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │              Context Manager                                │  │   │
│  │  │         (app/agent/context_manager.py)                      │  │   │
│  │  │  • Evidence bounding (3000 chars/item)                       │  │   │
│  │  │  • Compaction threshold (6000 chars)                         │  │   │
│  │  │  • LLM summarizer with fallback                             │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  │                               │                                      │   │
│  │                               ▼                                      │   │
│  │                    ┌──────────────────────┐                         │   │
│  │                    │   Stopping Logic     │                         │   │
│  │                    │  • answer → done     │                         │   │
│  │                    │  • ask_user → done   │                         │   │
│  │                    │  • error → fallback  │                         │   │
│  │                    │  • max_iters → done  │                         │   │
│  │                    └──────────────────────┘                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│    GROQ API      │    │  OPENROUTER API  │    │   TOOL LAYER     │
│    (Primary)     │    │   (Fallback)     │    │                  │
├──────────────────┤    ├──────────────────┤    ├──────────────────┤
│ Model:           │    │ Model:           │    │ • calculator     │
│ openai/gpt-oss-  │    │ nemotron-3-super │    │ • web_search     │
│ 20b              │    │ -120b-a12b:free  │    │ • datetime       │
│                  │    │                  │    │ • knowledge_     │
│ 5-key rotation   │    │ Single key       │    │   search         │
│                  │    │                  │    │                  │
│ Rate limiting:   │    │ Rate limiting:   │    │                  │
│ • retry-after    │    │ • 30s minimum    │    │                  │
│ • 120s cooldown  │    │   interval       │    │                  │
│ • key rotation   │    │                  │    │                  │
│ • exponential    │    │                  │    │                  │
│   backoff        │    │                  │    │                  │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAG PIPELINE                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  app/rag/                                                           │   │
│  │  ├── retriever.py      → Vector similarity search                   │   │
│  │  ├── chunking.py       → Document chunking (500 chars, 50 overlap)  │   │
│  │  ├── embeddings.py     → Sentence-Transformers (all-MiniLM-L6-v2)   │   │
│  │  └── ingestion.py      → Document ingestion pipeline                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      ChromaDB                                        │   │
│  │  • 19 chunks from 3 documents                                       │   │
│  │  • Persistent storage at ./data/chroma_db                           │   │
│  │  • 384-dimensional embeddings                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ User Query  │────▶│ Agentic     │────▶│ LLM         │────▶│ Tool        │
│             │     │ Loop        │     │ Provider    │     │ Execution   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                         │                     │                     │
                         │                     │                     │
                         ▼                     ▼                     ▼
                    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                    │ Context     │     │ Evidence    │     │ Results     │
                    │ Manager     │     │ Accumulator │     │ Cache       │
                    └─────────────┘     └─────────────┘     └─────────────┘
                         │                     │                     │
                         │                     │                     │
                         ▼                     ▼                     ▼
                    ┌─────────────────────────────────────────────────────┐
                    │              Final Answer with Citations            │
                    └─────────────────────────────────────────────────────┘
```

### Rate Limit Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Send Request│────▶│ Groq API    │────▶│ Check       │
│ to Groq     │     │             │     │ Status Code │
└─────────────┘     └─────────────┘     └─────────────┘
                         │                     │
                         │                     ▼
                         │              ┌─────────────┐
                         │              │ 200 OK?     │
                         │              └─────────────┘
                         │                     │
                         │         ┌───────────┴───────────┐
                         │         │                       │
                         │         ▼                       ▼
                         │  ┌─────────────┐        ┌─────────────┐
                         │  │ Yes: Return │        │ No: Check   │
                         │  │ Response    │        │ Error Code  │
                         │  └─────────────┘        └─────────────┘
                         │                             │
                         │                    ┌────────┴────────┐
                         │                    │                 │
                         │                    ▼                 ▼
                         │             ┌─────────────┐  ┌─────────────┐
                         │             │ 429: Rate   │  │ 5xx: Rotate │
                         │             │ Limited     │  │ Key         │
                         │             └─────────────┘  └─────────────┘
                         │                    │                 │
                         │                    ▼                 ▼
                         │             ┌─────────────┐  ┌─────────────┐
                         │             │ Read        │  │ Backoff     │
                         │             │ retry-after │  │ 2-8 seconds │
                         │             │ (120s)      │  │             │
                         │             └─────────────┘  └─────────────┘
                         │                    │                 │
                         │                    ▼                 │
                         │             ┌─────────────┐         │
                         │             │ Cooldown    │         │
                         │             │ Wait        │         │
                         │             └─────────────┘         │
                         │                    │                 │
                         │                    ▼                 │
                         │             ┌─────────────┐         │
                         │             │ Try Open-   │◀────────┘
                         │             │ Router      │
                         │             │ Fallback    │
                         │             └─────────────┘
```

---

## 3. Implementation Process

### Phase 1: Provider Setup

**Objective:** Replace broken Gemini setup with Groq + OpenRouter.

**Steps:**
1. Created `app/llm/groq.py` with 5-key rotation
2. Created `app/llm/openrouter.py` as fallback
3. Updated `app/config.py` for new providers
4. Updated `app/llm/provider.py` factory
5. Removed `gemini.py`, `local_vllm.py`, `local_transformers.py`

**Outcome:** Both providers working with tool calling support.

### Phase 2: Agentic Loop

**Objective:** Implement single-agent bounded loop with tool selection.

**Steps:**
1. Created `app/agent/loop.py` with iteration control
2. Implemented tool decision logic (search_knowledge, web_search, calculator, datetime, answer, ask_user)
3. Added context manager for compaction
4. Implemented duplicate call prevention
5. Added similar query detection (>70% word overlap)

**Outcome:** Loop correctly selects tools, accumulates evidence, and produces answers.

### Phase 3: Rate Limit Handling

**Objective:** Handle Groq and OpenRouter rate limits gracefully.

**Steps:**
1. Implemented exponential backoff (2s/4s/8s)
2. Added `retry-after` header parsing
3. Added token-aware pacing with sliding window
4. Implemented OpenRouter 30s minimum interval
5. Added HTTP 400 recovery (text protocol fallback)

**Outcome:** System gracefully handles429 errors with fallback to OpenRouter.

### Phase 4: Evaluation Harness

**Objective:** Build custom evaluation framework.

**Steps:**
1. Created `app/evaluation/harness.py` with query execution and scoring
2. Created `app/evaluation/test_queries.py` with 10 test queries
3. Created `app/evaluation/failure_injection.py` with 3 failure tests
4. Created `app/evaluation/run_evaluation.py` CLI runner
5. Added progress tracking and report generation

**Outcome:** Complete evaluation framework measuring task completion, tool correctness, and trajectory.

### Phase 5: Testing and Validation

**Objective:** Ensure all components work correctly.

**Steps:**
1. Created 34 regression tests covering all components
2. Ran offline evaluation with scripted fixtures
3. Ran live evaluation with real API calls
4. Ran failure injection tests
5. Documented results and challenges

**Outcome:** 34/34 tests passing, 4/10 live queries succeeding.

---

## 4. Context Engineering

### Technique: Compaction with Evidence Bounding

**Implementation:** `app/agent/context_manager.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                    Context Manager                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input: Tool results from each iteration                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Stage 1: Evidence Bounding                                │ │
│  │ • Each finding capped at 3,000 characters                 │ │
│  │ • Prevents single source from dominating context          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Stage 2: Threshold Check                                  │ │
│  │ • Total evidence > 6,000 characters?                      │ │
│  │ • If yes → trigger compaction                             │ │
│  │ • If no → continue accumulating                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Stage 3: Compaction                                       │ │
│  │ • LLM summarizer compresses to 2,000 characters          │ │
│  │ • Preserves: source IDs, disagreements, errors            │ │
│  │ • Fallback: deterministic truncation if summarizer fails  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  Output: Compacted context for next iteration                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Parameters:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max finding size | 3,000 chars | Individual tool result cap |
| Compaction threshold | 6,000 chars | Trigger compaction when exceeded |
| Summary target | 2,000 chars | Target size after compaction |

**Why This Works:**

1. **Prevents overflow**: No single source can fill the entire context window
2. **Preserves key information**: Summarizer retains source IDs and disagreements
3. **Error notes retained separately**: Failed tool calls are stored in a separate error log, not mixed with successful evidence
4. **Rebuilds from original question**: Each iteration reconstructs the prompt from the original query + current findings, avoiding verbose history
5. **Graceful degradation**: Deterministic truncation if LLM summarizer fails
6. **Token efficiency**: Reduces prompt tokens for subsequent iterations

**Trade-off:**

Compaction can lose detail from earlier iterations. This is acceptable because:
- The model re-reads summarized findings each iteration
- Source IDs are preserved for citation
- Key disagreements are explicitly retained

---

## 5. Agentic Pattern

### Pattern: Single-Agent Bounded Loop

**Implementation:** `app/agent/loop.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agentic Loop                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Iteration 1                                               │ │
│  │ • Initial RAG context loaded                               │ │
│  │ • LLM decides: search_knowledge OR web_search              │ │
│  │ • Tool executes, returns evidence                          │ │
│  │ • Evidence added to context                                │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Iteration 2                                               │ │
│  │ • Context includes previous evidence                       │ │
│  │ • LLM decides: search_knowledge OR web_search OR answer    │ │
│  │ • If answer → break loop, return response                  │ │
│  │ • If tool → execute, add to context                        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Iteration 3-5 (if needed)                                 │ │
│  │ • Continue gathering evidence                              │ │
│  │ • Duplicate detection prevents redundant calls             │ │
│  │ • Similar query detection (>70% word overlap)              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Final Iteration (max_iterations)                           │ │
│  │ • Only answer/ask_user tools available                     │ │
│  │ • Forces model to synthesize from available evidence       │ │
│  │ • Reports limitations if evidence insufficient             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Available Tools:**

| Tool | Description | Returns |
|------|-------------|---------|
| `search_knowledge` | Vector search over ingested documents | Chunks with relevance scores |
| `web_search` | Real-time web search (DuckDuckGo/Startpage/Yahoo) | URLs and snippets |
| `calculator` | Evaluate mathematical expressions | Numeric result |
| `get_current_datetime` | Get current date and time | Formatted datetime string |
| `answer` | Synthesize evidence into final response | User-facing answer |
| `ask_user` | Request missing information | Clarification question |

**Stopping Conditions:**

| Condition | Action | Result |
|-----------|--------|--------|
| Model calls `answer` | Break loop | Return synthesized response |
| Model calls `ask_user` | Break loop | **Clarification ends the request**; user resubmits with missing information |
| Provider error | Try fallback | If fallback fails, report error |
| Max iterations reached | **Exhaustion → incomplete verification** | Force answer from available evidence; report what could not be verified |

**Clarification flow:** When the model calls `ask_user`, the loop terminates immediately. The user receives a clarification question and must resubmit the query with the missing information. The agent does not continue searching after requesting clarification.

---

## 6. Evaluation Harness

### Framework Structure

```
app/evaluation/
├── __init__.py
├── harness.py          # Core evaluation logic
├── test_queries.py     # 10 test queries
├── failure_injection.py # 3 failure injection tests
├── run_evaluation.py   # CLI runner
├── RESULTS.md          # Detailed results report
├── progress_live.json  # Live evaluation progress
├── progress_offline.json # Offline evaluation progress
├── evaluation_live.json # Live evaluation results
├── evaluation_offline.json # Offline evaluation results
└── failure_injection_live.json # Failure injection results
```

### Metrics Measured

| Metric | Definition | How Measured |
|--------|------------|--------------|
| Task Completion | Agent successfully answers the query | Rubric-based (answer_contains_any) |
| Tool Correctness | Agent selects appropriate tools | Expected tools list comparison |
| Trajectory Length | Number of iterations per query | Count of loop iterations |
| Token Usage | Total tokens consumed | Prompt + completion tokens from API |
| Duration | End-to-end time | Wall-clock time measurement |

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

### Test Queries (10 Total)

| ID | Difficulty | Query | Expected Tools | Answer Rubric |
|----|-----------|-------|----------------|---------------|
| simple_01 | simple | What is Retrieval-Augmented Generation (RAG)? | search_knowledge, web_search | Contains "rag" OR "retrieval" |
| simple_02 | simple | What is the current date and time? | get_current_datetime | Contains current date |
| simple_03 | simple | Calculate 15% of 340 | calculator | Contains "51" |
| moderate_01 | moderate | Python best practices: KB vs industry | search_knowledge, web_search | Contains "python" OR "pep" |
| moderate_02 | moderate | Is AI info in docs still accurate? | search_knowledge, web_search | Contains "ai" OR "accurate" |
| moderate_03 | moderate | Sentence vs recursive chunking | search_knowledge | Contains "sentence" OR "recursive" |
| complex_01 | complex | RAG vs fine-tuning for enterprise | search_knowledge, web_search | Contains "rag" AND "cost" |
| complex_02 | complex | Security: local LLMs vs cloud APIs | search_knowledge, web_search | Contains "security" |
| complex_03 | complex | Embedding models in knowledge base | search_knowledge | Contains "embedding" |
| complex_04 | complex | Recommended chunk size for RAG | search_knowledge, web_search | Contains "chunk" |

### Failure Injection Tests

| Test | Failure Type | How Injected | Expected Behavior |
|------|-------------|--------------|-------------------|
| Web search unavailable | Tool exception | Mock executor raises RuntimeError | Agent acknowledges limited sources, uses KB only |
| Malformed RAG output | Corrupted data | Mock retriever returns garbage | Agent falls back to web search |
| Provider timeout | API timeout | Mock transport raises TimeoutError | Fallback to OpenRouter triggered |

### Running Evaluations

```bash
# Offline (scripted, no API calls)
python -m app.evaluation.run_evaluation --mode offline

# Live (real API calls)
python -m app.evaluation.run_evaluation --mode live --delay 65

# Specific queries
python -m app.evaluation.run_evaluation --mode live --ids simple_01 simple_02

# Failure injection
python -m app.evaluation.run_evaluation --mode live --failure-injection

# Regression tests
python -m unittest discover -s tests -v
```

---

## 7. APIs Used and Tried

### Primary: Groq API

| Property | Value |
|----------|-------|
| Endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| Model | `openai/gpt-oss-20b` |
| Authentication | API key (5 keys for rotation) |
| Rate Limit | 8,000 tokens/min per organization |
| Request Limit | 1,000 requests/2 hours per key |
| retry-after | 120 seconds |

**Configuration:**
```python
# .env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_API_KEY_2=gsk_...
GROQ_API_KEY_3=gsk_...
GROQ_API_KEY_4=gsk_...
GROQ_API_KEY_5=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
GROQ_TOKENS_PER_MINUTE=8000
```

### Fallback: OpenRouter API

| Property | Value |
|----------|-------|
| Endpoint | `https://openrouter.ai/api/v1/chat/completions` |
| Model | `nvidia/nemotron-3-super-120b-a12b:free` |
| Authentication | API key |
| Rate Limit | Free tier (strict per-request limits) |
| Minimum Interval | 30 seconds |

**Configuration:**
```python
# .env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free
```

### Embedding Model

| Property | Value |
|----------|-------|
| Model | `all-MiniLM-L6-v2` (Sentence-Transformers) |
| Dimensions | 384 |
| Library | `sentence-transformers` via `chromadb` |

### APIs Tried and Rejected

| API | Reason for Rejection |
|-----|---------------------|
| Google Gemini | Deprecated SDK; replaced with Groq |
| Local vLLM | Requires GPU; not available |
| Local Transformers | Slow inference; not suitable for real-time |
| `nemotron-3.5-lightning:free` | Emits chain-of-thought reasoning |
| `llama-3.1-8b-instruct:free` | No longer free on OpenRouter |

---

## 8. Challenges and Solutions

### Challenge 1: Groq Shared Organization Quota

**Problem:** 5 API keys share one organization quota; rotation doesn't multiply capacity.

**Impact:** After the first query, subsequent queries hit 429 immediately.

**Solution:** Evidence-based pacing using `retry-after` header (120s between queries).

```python
# groq.py
retry_after = response.headers.get("retry-after", "")
delay = max(1, float(retry_after)) if retry_after else 60
```

### Challenge 2: Chain-of-Thought Model

**Problem:** `nemotron-3.5-lightning:free` emits visible reasoning instead of direct answers.

**Impact:** Answers contained thinking steps instead of final responses.

**Solution:** Swapped to `nemotron-3-super-120b-a12b:free` (instruct-style).

### Challenge 3: OpenRouter Rate Limiting

**Problem:** OpenRouter free tier has strict per-request rate limits.

**Impact:** When Groq fails and we fall back to OpenRouter, consecutive requests get 429.

**Solution:** Added 30-second minimum interval between OpenRouter requests.

```python
# openrouter.py
self._min_interval = 30.0  # Minimum 30s between requests
```

### Challenge 4: HTTP 400 Tool Call Failures

**Problem:** Groq occasionally returns HTTP 400 with `tool_use_failed` code.

**Impact:** Agentic loop breaks on tool calling errors.

**Solution:** Three-tier recovery:
1. Retry with text decision protocol (ACTION:/ANSWER:/CLARIFY:)
2. Retry without tools (text-only)
3. Raise error if both fail

```python
# groq.py
if response.status_code == 400:
    if err_code == "tool_use_failed":
        # Retry with text protocol
        text_payload["messages"] = payload["messages"] + [...]
    elif payload.get("tools"):
        # Retry without tools
        text_payload = {k: v for k, v in payload.items() 
                       if k not in ("tools", "tool_choice")}
```

### Challenge 5: Answer Truncation

**Problem:** `max_tokens=768` too low for cross-source synthesis.

**Impact:** Answers cut off mid-sentence.

**Solution:** Increased `max_tokens` to 1024.

### Challenge 6: Duplicate Tool Calls

**Problem:** Model rephrases queries slightly, bypassing exact-match dedup.

**Impact:** Redundant API calls waste tokens and time.

**Solution:** Word-overlap detection (>70% shared words = duplicate).

```python
# loop.py
words1 = set(normalized.split())
words2 = set(prev_query.split())
overlap = len(words1 & words2) / max(len(words1 | words2), 1)
if overlap > 0.7:
    # Treat as duplicate, reuse cached result
```

### Challenge 7: Model Not Using Expected Tools

**Problem:** Model answers directly from initial RAG context without calling tools.

**Impact:** Evaluation marks query as "tools=False" even though answer is correct.

**Solution:** Updated system prompt to require tool verification, added short-circuit for simple queries.

---

## 9. Results

### Regression Tests

**Result: 34/34 tests passing (100%)**

| Category | Tests | Status |
|----------|-------|--------|
| Agentic Loop | 12 | ✅ All Pass |
| Groq Provider | 8 | ✅ All Pass |
| OpenRouter Provider | 3 | ✅ All Pass |
| Provider Recovery | 7 | ✅ All Pass |
| Production Startup | 1 | ✅ All Pass |
| API Validation | 3 | ✅ All Pass |

### Offline Evaluation (Scripted Fixtures)

**Result: 50% task completion, 100% tool correctness**

| Query | Difficulty | Completed | Tools OK | Iterations | Stopped Reason |
|-------|-----------|-----------|----------|------------|----------------|
| cross_source | moderate | ✅ | ✅ | 3 | model_answered |
| clarification | simple | ✅ | ✅ | 1 | clarification |
| provider_failure | simple | ❌ | ✅ | 1 | error (injected) |
| wrong_answer | simple | ❌ | ✅ | 1 | model_answered |

### Live Evaluation (Groq + OpenRouter)

**Result: 40% task completion, 75% tool correctness**

| Query ID | Difficulty | Completed | Tools OK | Iterations | Tokens (P/C) | Duration |
|----------|-----------|-----------|----------|------------|--------------|----------|
| simple_01 | simple | ✅ | ✅ | 3 | 2,735 / 235 | 5.2s |
| simple_02 | simple | ✅ | ✅ | 2 | 3,092 / 844 | 68.8s |
| simple_03 | simple | ✅ | ✅ | 2 | 3,140 / 348 | 107.2s |
| moderate_02 | moderate | ✅ | ✅ | 5 | 5,102 / 338 | 44.9s |
| moderate_01 | moderate | ❌ | ❌ | 2 | 1,584 / 20 | 26.6s |
| moderate_03 | moderate | ❌ | ❌ | 1 | 0 / 0 | 0s |
| complex_01 | complex | ❌ | ❌ | 1 | 0 / 0 | 0s |
| complex_02 | complex | ❌ | ❌ | 1 | 0 / 0 | 0s |
| complex_03 | complex | ❌ | ❌ | 1 | 0 / 0 | 0s |
| complex_04 | complex | ❌ | ❌ | 1 | 0 / 0 | 0s |

### Successful Query Details

#### simple_01: What is RAG?

```
Step 1: search_knowledge("Retrieval-Augmented Generation RAG")
        → Retrieved 5 chunks from rag_guide.md, ai_overview.md
Step 2: web_search("RAG definition overview")
        → Found 5 results including IBM, Wikipedia
Step 3: answer(synthesized comparison)
        → "RAG is a technique that enhances LLMs by providing external knowledge..."
```

**Sources consulted:** search_knowledge, web_search  
**Trajectory:** 3 iterations (reasonable for cross-source verification)

#### moderate_02: Is AI info still accurate?

```
Step 1: web_search("major AI developments 2024")
        → Found GPT-4 Turbo, AI regulation results
Step 2: web_search("artificial general intelligence not yet exists")
        → Confirmed AGI status
Step 3: search_knowledge("AI 2024")
        → Retrieved ai_overview.md content
Step 4: web_search("AI developments 2024 new models")
        → Additional verification
Step 5: answer(synthesized comparison)
        → "The documents provide a foundational overview..."
```

**Sources consulted:** web_search, search_knowledge  
**Trajectory:** 5 iterations (thorough cross-source verification)

### Aggregate Metrics

| Metric | Value |
|--------|-------|
| Total Queries | 10 |
| Task Completion Rate | 40% (4/10) |
| Tool Correctness Rate | 75% (3/4 successful) |
| Average Trajectory Length | 3.0 iterations (successful queries) |
| Total Tokens (successful) | 14,069 prompt + 1,665 completion |
| Total Duration (successful) | 226.1 seconds |

### Failure Analysis

| Query | Primary Failure | Secondary Failure | Root Cause |
|-------|----------------|-------------------|------------|
| moderate_01 | Groq 429 | — | Rate limit on 2nd iteration |
| moderate_03 | Groq 429 | OpenRouter 429 | Both providers exhausted |
| complex_01-04 | Groq 429 | OpenRouter 429 | Both providers exhausted |

**Key Finding:** All failures are due to API rate limiting, not application bugs. The agentic loop correctly detects 429 errors, triggers fallback, and reports the failure.

### Failure Injection Tests

**Result: 3/3 tests passing**

| Test | Failure Type | Expected Behavior | Actual Behavior | Status |
|------|-------------|-------------------|-----------------|--------|
| Web search unavailable | Tool exception | Acknowledge limited sources | Used KB only, noted web unavailable | ✅ |
| Malformed RAG output | Corrupted data | Fall back to web search | Web search used, KB skipped | ✅ |
| Provider timeout | API timeout | Trigger OpenRouter fallback | Fallback correctly triggered | ✅ |

**Note:** Scripted behavior (mocked exceptions) is not presented as autonomous live recovery. The failure injection tests verify that the loop correctly propagates errors, excludes failed sources, and triggers the configured fallback. Live injection tests verify model behavior when tools are unavailable.

### Token and Cost Accounting

**Accounting method:** Totals include every successful decision and compaction response. Local generation uses the model tokenizer; API totals include reported usage from the provider. Failed calls can have unreported consumption, making recorded totals a lower bound.

**Offline tokens:** Synthetic (generated by test fixtures, not real API calls).

**Multi-agent baseline:** Not applicable — single-agent architecture used.

**No dollar cost claimed:** All providers used free-tier access; no unmeasured overhead multiplier is claimed.

| Query | Prompt Tokens | Completion Tokens | Total | Cost (Groq Free) |
|-------|--------------|-------------------|-------|------------------|
| simple_01 | 2,735 | 235 | 2,970 | $0.00 |
| simple_02 | 3,092 | 844 | 3,936 | $0.00 |
| simple_03 | 3,140 | 348 | 3,488 | $0.00 |
| moderate_02 | 5,102 | 338 | 5,440 | $0.00 |
| **Total** | **14,069** | **1,665** | **15,734** | **$0.00** |

### Tool vs. Agent Boundary

**Web search is a tool, not an agent:**

| Property | Value |
|----------|-------|
| Request type | Single bounded DDGS request |
| Max results | 5 |
| Client timeout | 10 seconds |
| Internal behavior | Service may consult multiple engines |
| State ownership | Assistant owns research state and next decision |
| Autonomy | No delegated autonomous goal |
| Communication | No agent-to-agent conversation |

The assistant decides what to search, processes the results, and decides the next action. The web search service does not make autonomous decisions or communicate with other agents — it is a stateless data retrieval tool.

### What Was Built

A complete agentic cross-source verification assistant with:

1. **Single-agent bounded loop** that decides which tools to use at each iteration
2. **Context engineering** with compaction to manage token budget
3. **Multi-provider support** with Groq (primary) and OpenRouter (fallback)
4. **Comprehensive evaluation harness** measuring task completion, tool correctness, and trajectory
5. **34 regression tests** ensuring all components work correctly

### Key Achievements

| Achievement | Status |
|-------------|--------|
| Agentic loop correctly selects tools | ✅ |
| Context compaction prevents overflow | ✅ |
| Duplicate call detection works | ✅ |
| Fallback chain triggers on errors | ✅ |
| Evaluation harness produces reports | ✅ |
| All regression tests pass | ✅ |

### Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Groq free-tier rate limit | 40% live completion | Document as free-tier constraint |
| OpenRouter rate limit | Fallback sometimes fails | 30s minimum interval |
| Model sometimes skips tools | Some queries marked as "no tools" | Updated system prompt |

### Recommendations

1. **For full evaluation**: Use paid Groq tier or increase delay to 120s between queries
2. **For production**: Implement request queuing and response caching
3. **For accuracy**: Fine-tune model on agentic patterns

---

*Report generated: 2026-09-14*  
*Evaluation harness version: 1.0*  
*Test framework: Custom Python (unittest + httpx MockTransport)*  
*Total tests: 34 (all passing)*  
*Live evaluation: 4/10 queries successful*
