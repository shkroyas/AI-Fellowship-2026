# Evaluation environment

Python 3.12 on Linux; evaluation date 2026-09-13. Model: gemini-3.6-flash. The live runner uses a 15-second pause between every model call. Keys and account identifiers are excluded.

| Package | Installed version |
|---|---|
| FastAPI | 0.115.0 |
| Pydantic | 2.9.0 |
| ChromaDB | 0.5.5 |
| sentence-transformers | 3.1.0 |
| httpx | 0.27.0 |
| DDGS | 9.16.0 |

ChromaDB emitted PostHog telemetry-signature errors during startup/query telemetry. Retrieval nevertheless executed and returned document chunks. No claim of a clean Docker build or remote deployment is made; the measured tests run against the source package in the local Python environment.
