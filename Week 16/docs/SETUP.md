# Setup and Reproduction

## Requirements

Python 3.12, internet access for initial embedding downloads, and a supported model account with available quota. Tests use the standard-library `unittest` runner; the project does not use an external evaluation framework. The submitted sample documents are under `task1-ai-assistant/data/sample_docs`.

## Core assistant

From the `Week 16` directory:

```bash
cd task1-ai-assistant
python3 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill in your own `GOOGLE_API_KEY` and set `GEMINI_MODEL` to a model available to your account. The submitted default is the model used for evaluation; access is account-dependent. `.env` is intentionally excluded from Git. Keep an existing `.env` rather than overwriting it.

```bash
DEBUG=false python -m uvicorn app.main:app --port 8000
```

Open `http://localhost:8000/docs`. Startup ingests the sample documents into local ChromaDB. Use this working directory so the default data paths resolve. The `DEBUG=false` override avoids a conflicting shell setting such as `DEBUG=release`.

```bash
curl http://localhost:8000/chat/agentic \
  -H 'Content-Type: application/json' \
  -d '{"message":"Compare our Python practices with external standards and cite sources.","max_iterations":5}'
```

The response includes `answer`, `sources_consulted`, `iterations_used`, `total_tokens`, `duration_ms`, `compacted`, `stopped_reason` and `steps`. `sources_consulted` lists successful tool names; document/URL references are part of the evidence and answer. Stop reasons are `model_answered`, `clarification`, `max_iterations` and `error`. A clarification pauses the task and requires a new request containing the missing details. Agentic requests have no persistent conversation store.

The W15 `/chat`, ingestion and structured-output routes remain available. Provider choice uses the request override when supplied, otherwise `LLM_PROVIDER`; the agentic route sends no extra billable health prompt. The legacy `local_vllm` identifier currently selects the local Transformers implementation. The repository also includes the older vLLM client source; it is not the factory's active local backend.

## Tests and evaluations

From `task1-ai-assistant` with the virtual environment active:

```bash
python -m unittest discover -s tests -v
python -m app.evaluation.run_evaluation --mode offline
DEBUG=false python -m app.evaluation.run_evaluation --mode live --delay 15
DEBUG=false python -m app.evaluation.run_evaluation --mode live --failure-injection --delay 15
```

Live mode uses the configured credentials and can consume quota. The delay applies to each model call, including compaction. It reduces request frequency but cannot restore exhausted daily quota. Results are written beside the runner as Markdown and JSON; the `evaluation/` directory contains the submitted snapshot. `progress_live.json` checkpoints completed queries. To investigate selected failures without overwriting the full run:

```bash
DEBUG=false python -m app.evaluation.run_evaluation --mode live --ids simple_02 simple_03 --delay 15
```

Subset output is named `evaluation_live_subset`. Historical 2024 comparison questions in the query set are intentional. Lexical rubrics are transparent proxies, not factual correctness proofs. Review citations, missing-evidence statements and traces before interpreting a completion score. Error strings or unsupported answers must not be counted as successes.

## Production API and Streamlit

From `Week 16/task2-production`:

```bash
docker compose up --build
```

Compose reads `../task1-ai-assistant/.env`. The frontend is at port 8501 and API at port 8000. Enable Agentic Mode in the sidebar. The optional GPU service is behind the `gpu` profile and is not needed for Gemini. The frontend health check uses Python/httpx, which is installed in its image. The production API resolves sample-document paths from the shared core package and registers knowledge search after retriever initialization.

Docker deployment has not been inferred from local tests. Persistent storage, cross-worker rate limits and multi-instance coordination require separate deployment validation. The production single-pass cache/fallback middleware does not imply identical caching/fallback behavior for agentic requests.

## Optional credential slots

The provider accepts `GOOGLE_API_KEY` plus optional `_2` through `_5`. Fill slots sequentially; `GEMINI_ACTIVE_KEY` selects the one-based position among nonempty slots. Restart after changes. Keys are sent in headers and excluded from settings exports. Transient transport or HTTP 500/502/503/504 failures can try the next slot once; HTTP 429 does not rotate credentials and applies a cooldown. Authentication errors stop. Several keys do not increase a project's quota.

Provider reference: [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [generateContent API](https://ai.google.dev/api/generate-content). Web-search reference: [DDGS package documentation](https://pypi.org/project/ddgs/).

## Regenerate the submission PDF

From `Week 16`:

```bash
task1-ai-assistant/venv/bin/python -m pip install fpdf2
task1-ai-assistant/venv/bin/python task1-ai-assistant/app/evaluation/generate_pdf.py
```

The PDF is generated from current Markdown sources. No scores are hard-coded by the renderer.
