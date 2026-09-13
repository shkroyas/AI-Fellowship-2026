# Core Assistant

The W15 assistant and Week 16 agentic feature share this package. See the [submission README](../README.md), [setup guide](../docs/SETUP.md), and [evaluation results](../evaluation/RESULTS.md).

- `app/main.py`: FastAPI routes and startup ingestion.
- `app/rag`: ingestion, chunking, embeddings and retrieval.
- `app/tools`: tool schemas, validation and executors.
- `app/agent`: bounded decisions and context management.
- `app/llm`: Gemini, OpenAI and local model adapters.
- `app/evaluation`: custom harness, query rubrics and failure injection.
- `tests`: regression and API checks.
