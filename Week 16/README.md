# Week 16 — Agentify the Assistant

**Royas Shakya · AI Fellowship 2026 · Task 3**

## Context Engineering

The `ContextManager` (`app/agent/context_manager.py`) bounds each evidence item at 3,000 characters and compacts accumulated findings above 6,000 characters before the next decision. Summaries preserve source IDs and disagreements; error notes are retained separately. Summary output is capped at 2,000 characters; truncation fallback on summarizer failure. Identical successful tool calls reuse their result.

## Agentic Pattern

A single agent (`app/agent/loop.py`) selects search_knowledge, web_search, calculator, get_current_datetime, answer, or ask_user. Later searches depend on earlier evidence, so separate specialists are not justified. The loop stops on answer, clarification, unrecovered error, or five iterations. Exhaustion reports incomplete verification.

## Evaluation Harness

A custom Python framework (`app/evaluation/`) tests ten queries across three difficulty levels. It measures task completion, tool correctness, trajectory length, and per-query tokens. Failure taxonomy: hard (execution failure), soft (rubric miss), cascading-soft (tool failure leading to rubric miss).

## Additional Requirements

**Skill vs Agent:** A Skill requires an execution host. This project supplies that host as a bounded loop. `answer` and `ask_user` are terminal control actions, not agents.

**Token Accounting:** Totals include successful decisions and compaction responses. Failed calls have unreported consumption. Offline tokens are synthetic. No dollar cost claimed.

**Failure Injection:** Controlled tests inject search exceptions and provider timeout. Timeout test passes; web search and malformed RAG tests are scripted (inconclusive against live tools).

**Tool vs Agent Boundary:** Web search is a bounded DDGS request (max 5 results, 10s timeout). The assistant owns research state. No agent-to-agent conversation.

## Results

| Metric | Offline | Live (Best Run — Gemini) |
|--------|---------|--------------------------|
| Task Completion | 50% (2/4) | 50% (5/10) |
| Tool Correctness | 100% (4/4) | 60% (6/10 tool calls correct) |
| Regression Tests | 24/24 | — |

**Live run details:** Best run used Gemini 3.6-flash with 15s pacing. All 3 simple queries and 2 of 3 moderate queries completed successfully. All 4 complex queries failed due to rate limiting (HTTP 429) after the free-tier quota was exhausted by earlier queries. Groq-based runs achieved 0–30% completion under the same rate-limit constraints (8,000 tokens/min free tier).

## Architecture

| Component | File | Purpose |
|-----------|------|---------|
| Agentic Loop | `app/agent/loop.py` | Tool selection, evidence accumulation |
| Context Manager | `app/agent/context_manager.py` | Compaction, evidence bounding |
| Groq Provider | `app/llm/groq.py` | 5-key rotation, rate limit handling |
| OpenRouter | `app/llm/openrouter.py` | Free-tier fallback |
| Tools | `app/tools/registry.py` | calculator, web_search, datetime, knowledge_search |
| RAG | `app/rag/retriever.py` | ChromaDB vector search |
| Evaluation | `app/evaluation/harness.py` | Query execution, rubric scoring |

## Setup

```bash
cd task1-ai-assistant
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add API keys
uvicorn app.main:app --reload --port 8000
```

## Running

```bash
# Offline evaluation
python -m app.evaluation.run_evaluation --mode offline

# Regression tests
python -m unittest discover -s tests -v
```

## Limitations

- Groq free-tier rate limit (8,000 tokens/min per organization) prevents consecutive live queries
- Compaction can lose detail from earlier iterations
- Lexical rubrics may miss semantically correct but differently worded answers
