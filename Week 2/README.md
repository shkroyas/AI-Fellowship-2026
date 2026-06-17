# Week 2 - AI Fellowship 2026

This project is a small FastAPI and PostgreSQL application built around the Classic Models sample dataset. It covers database bootstrapping, a customer API, and concurrent table statistics in a way that is easy to run locally and easy to review in GitHub.

## What Is Included

- `task1/` contains the Docker setup for PostgreSQL and the database seed workflow.
- `task2/` documents the customer API portion of the project.
- `task3/` documents the table-count and concurrency portion of the project.
- `app/` contains the runnable FastAPI implementation that supports all later tasks.

## Project Structure

- `app/core/` holds configuration, logging, and database setup.
- `app/models.py` defines the SQLAlchemy ORM models.
- `app/schemas.py` defines the Pydantic request and response models.
- `app/crud.py` contains the database operations.
- `app/routers/` contains the API routes.
- `task1/docker-compose.yml` runs PostgreSQL and loads the seed script automatically.

## Requirements

- Python 3.11
- Docker Desktop
- PostgreSQL client tools if you want to inspect the database manually

## Environment Setup

Copy `.env.template` to `.env` and update the values for your machine.

Required variables:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_PORT`
- `POSTGRES_HOST`

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Task 1: Start PostgreSQL

From inside `task1/`, run:

```bash
docker compose up -d
```

The database starts with the seed script mounted at startup, so the tables and sample data are created automatically.

To verify the database:

```bash
docker exec -it postgres_database psql -U %POSTGRES_USER% -d %POSTGRES_DB%
\dt
SELECT COUNT(*) FROM customers;
```

## Task 2: Run the Customer API

Start the FastAPI app from the repository root:

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to explore the API.

Customer endpoints:

- `GET /customers`
- `GET /customers/{customer_id}`
- `POST /customers`
- `PUT /customers/{customer_id}`
- `DELETE /customers/{customer_id}`

## Task 3: Table Counts and Concurrency

The API also exposes individual count endpoints for each table and an aggregated dashboard endpoint:

- `GET /customers/count`
- `GET /orders/count`
- `GET /products/count`
- `GET /employees/count`
- `GET /offices/count`
- `GET /payments/count`
- `GET /orderdetails/count`
- `GET /productlines/count`
- `GET /overall_counts`

The aggregated endpoint uses `asyncio.gather()` and separate database sessions so the count queries run concurrently.

## Notes

- Logging is centralized through `app/core/logger.py` and writes to `app.log`.
- The repository keeps task-specific README files under `task1/`, `task2/`, and `task3/` for quick navigation.
