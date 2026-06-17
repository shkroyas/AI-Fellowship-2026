# Task 3 - Modularity and Concurrency

This folder represents the table-count and concurrency stage of the assignment.

## Scope

- Separate count endpoints for each table
- Aggregated dashboard endpoint at `/overall_counts`
- Concurrent execution with `asyncio.gather()`

## Related implementation

The working implementation lives in the root `app/` package, with the count routes in `app/routers/counts.py` and the shared count helpers in `app/crud.py`.
