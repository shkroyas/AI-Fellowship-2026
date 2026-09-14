# Setup and Reproduction

From `Week 16/task1-ai-assistant`, use Python 3.12:

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Preserve an existing `.env`. Set `GROQ_API_KEY` and optionally `OPENROUTER_API_KEY` to your own credentials. Leave unused slots blank. Credentials are excluded from the submission. The evaluated models are `openai/gpt-oss-20b` on Groq and `nvidia/nemotron-3.5-lightning:free` on OpenRouter; availability depends on the account. Use:

```dotenv
LLM_PROVIDER=groq
GROQ_MODEL=openai/gpt-oss-20b
GROQ_TOKENS_PER_MINUTE=6000
MAX_TOKENS=768
OPENROUTER_MODEL=nvidia/nemotron-3.5-lightning:free
```

`GROQ_API_KEY_2` through `_5` are optional operational failover credentials. They do not increase organization quota. Restart after configuration changes; providers are cached per worker. Do not run live evaluations alongside API traffic using the same organization unless you coordinate their aggregate allowance.

## Run

```bash
DEBUG=false python -m uvicorn app.main:app --port 8000 --workers 1
```

Visit `http://localhost:8000/docs`. Startup ingests the sample documents into ChromaDB and initially downloads the embedding model if not cached. Agentic responses include an answer, execution trace, source tool names, iterations, tokens, duration, compaction flag and stop reason. Clarification ends the request; submit a new request with the missing information. The original W15 chat/ingestion endpoints are also available.

```bash
curl --max-time 900 http://localhost:8000/chat/agentic \
  -H 'Content-Type: application/json' \
  -d '{"message":"Compare RAG and fine-tuning using our documents and web evidence.","max_iterations":5}'
```

## Verify

```bash
DEBUG=false python -m unittest discover -s tests -v
DEBUG=false python -m app.evaluation.run_evaluation --mode offline
DEBUG=false python -m app.evaluation.run_evaluation --mode live --delay 0
DEBUG=false python -m app.evaluation.run_evaluation --mode live --failure-injection --delay 0
```

`--delay` is an optional pause before each query. Provider pacing independently covers every Groq call, including compaction; zero does not disable that pacing. Live runs may take many minutes. They consume account quota, and daily exhaustion cannot be solved by waiting one minute. Provider-reported tokens exclude unknown consumption on unsuccessful requests.

Raw results are saved in `app/evaluation/`; `progress_live.json` checkpoints completed queries. Submitted snapshots are in `../evaluation/`. To diagnose a subset without replacing the full result:

```bash
DEBUG=false python -m app.evaluation.run_evaluation --mode live --ids complex_01 --delay 0
```

Expected answer rubrics remain unchanged. Their lexical checks and source/tool traces are proxies; independently review citation support and factual claims. Controlled negative tests are expected to fail the completion rubric and must not be relabeled successful live tasks.

## Production and diagrams

From `Week 16/task2-production`, run `docker compose up --build`. Compose reads the core `.env`. The UI is on port 8501 and API on 8000; enable Agentic Mode. The core and production agentic endpoints use the same provider, loop and fallback behavior. The UI allows 900 seconds for a paced request. Docker deployment and multi-worker operation are not certified by the local regression suite.

The architecture is in `../architecture/diagram.md` (Mermaid) and `agentic-loop.svg`. To rebuild documentation PDFs from the current Markdown, install `fpdf2` then run `python app/evaluation/generate_pdf.py` from this directory.

References: [Groq limits](https://console.groq.com/docs/rate-limits), [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits).

GPT-OSS requests use low reasoning effort. A rejected native tool generation (`tool_use_failed`) receives one retry using the existing text decision protocol; rejected arguments are never executed. OpenRouter allows up to 180 seconds for a response (15 seconds to connect). Routine `/health` calls do not send model prompts; use `?probe_model=true` only for an explicit provider check.
