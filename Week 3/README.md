# Week 3 Assignment

This workspace contains the Week 3 AI Fellowship assignment deliverables for SQL benchmarking, query decomposition, and two text-to-SQL application builds.

## Contents

- [task1](task1) - SQL benchmark and evaluation framework
- [task2](task2) - Query decomposition pipeline
- [task3](task3) - Vanilla prompt-chaining text-to-SQL app with Streamlit
- [task4](task4) - Agentic text-to-SQL app with Streamlit and FastAPI
- [report](report) - Submitted PDF reports
- [assignment](assignment) - Assignment brief

## Prerequisites

- Python 3.11 or newer
- Docker Desktop if you want to run the containerized stacks
- PostgreSQL 16 if you plan to run outside Docker
- A Gemini API key for the LLM-backed flows in task2 and task3
- Optional OpenAI or Gemini credentials for task4 if you want model-backed generation instead of deterministic fallback logic

## Installation

Each task has its own dependencies. Install only the one you want to run.

### Task 1

```powershell
cd task1
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Task 2

```powershell
cd task2
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Task 3

```powershell
cd task3
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Task 4

```powershell
cd task4
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Setup

Before running any task, copy the example environment file into a local `.env` file in that task folder.

### Task 1 environment variables

Create `task1/.env` with the database settings used by the benchmark runner:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=classicmodels
DB_USER=myuser
DB_PASSWORD=mypassword
```

### Task 2 environment variables

Create `task2/.env` with the database settings and Gemini key:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=classicmodels
DB_USER=myuser
DB_PASSWORD=mypassword
API_KEY=your_gemini_api_key
```

You can also use `GEMINI_API_KEY` instead of `API_KEY` if you prefer that naming convention.

### Task 3 environment variables

Create `task3/.env` from `task3/.env.example`.

Required values for the app to connect to PostgreSQL:

```env
DB_HOST=postgres_db
DB_PORT=5432
DB_NAME=classicmodels
DB_USER=myuser
DB_PASSWORD=mypassword
```

For Gemini-backed generation, add at least one key:

```env
GEMINI_API_KEYS=key1,key2,key3
```

### Task 4 environment variables

Create `task4/.env` from `task4/.env.example`.

Required values for database access:

```env
DB_HOST=postgres_db
DB_PORT=5432
DB_NAME=classicmodels
DB_USER=myuser
DB_PASSWORD=mypassword
```

Alternatively, you can provide a full connection string:

```env
DATABASE_URL=postgresql+psycopg://myuser:mypassword@postgres_db:5432/classicmodels
```

Optional model settings:

```env
LLM_PROVIDER=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
GEMINI_API_KEY=
GEMINI_API_KEYS=
MAX_QUERY_ROWS=500
```

Task 4 uses centralized configuration in [task4/config.py](task4/config.py), which loads `.env` automatically and keeps database, LLM, and runtime settings in one place. The example file [task4/.env.example](task4/.env.example) mirrors those settings so the runtime contract stays clear and maintainable.

## Usage

### Task 1: Benchmark SQL queries

```powershell
cd task1
python sql/run_benchmark.py
```

This runs the benchmark suite against the ClassicModels database and writes the evaluation results into the task 1 outputs.

### Task 2: Query decomposition

```powershell
cd task2
python query_decomposition.py
```

This generates the decomposed query artifacts saved in `decomposed_queries.csv` and `decomposed_queries.json`.

### Task 3: Streamlit text-to-SQL app

Docker Compose:

```powershell
cd task3
docker compose up --build
```

Local Streamlit run:

```powershell
cd task3
streamlit run streamlit_app.py
```

Task 3 launches a PostgreSQL container seeded from `task3/sql/seed.sql` and a Streamlit UI for the prompt-chaining pipeline.

### Task 4: Agentic text-to-SQL app

Docker Compose:

```powershell
cd task4
docker compose up --build
```

Local Streamlit run:

```powershell
cd task4
streamlit run streamlit_app.py
```

FastAPI API:

```powershell
cd task4
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Task 4 exposes both a Streamlit front end and a FastAPI backend. If no LLM credentials are set, the workflow falls back to deterministic agents so the app still runs locally.

## Reports

The written submission files are stored in [report](report). The per-task markdown reports in each task folder describe the architecture, validation, and design decisions used for the assignment.

## Notes

- Keep `.env` files out of version control.
- Prefer the task-specific `.env.example` file instead of inventing new variable names.
- If you change configuration behavior in code, update the matching example file and this README together so they stay aligned.