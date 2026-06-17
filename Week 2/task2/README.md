# Task 2 - FastAPI Customer API

This folder represents the customer API stage of the assignment.

## Scope

- ORM-backed access to the `customers` table
- Pydantic request and response schemas
- Customer list, detail, create, update, and delete endpoints

## Related implementation

The working FastAPI implementation is organized in the root `app/` package, with customer logic in `app/routers/customers.py`, schemas in `app/schemas.py`, CRUD operations in `app/crud.py`, and the FastAPI app in `app/main.py`.
