# Task 1 - PostgreSQL Setup with Docker

This folder contains the Docker-based database bootstrap for the assignment.

## What is here

- `docker-compose.yml` for PostgreSQL 16
- `.env.template` for local configuration values
- The database seed is mounted from `../app/seed.sql`

## Run

Copy the root `.env.template` to `.env` if needed, then run this folder's compose file from inside `task1/`:

```bash
docker compose up -d
```

## Verify

After the container starts, enter PostgreSQL and check the tables:

```bash
docker exec -it postgres_database psql -U %POSTGRES_USER% -d %POSTGRES_DB%
\dt
SELECT COUNT(*) FROM customers;
```
