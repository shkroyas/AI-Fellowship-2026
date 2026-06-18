from __future__ import annotations

from sqlalchemy import text

from config import Config
from db import engine


def execute_sql(sql_query: str, max_rows: int | None = None) -> tuple:
    """
    Executes a SQL select statement against the configured SQLAlchemy database engine.
    
    Returns:
        tuple: (columns, results_list, error_message)
        - If success: (list of string columns, list of dict row records, None)
        - If failure: (None, None, detailed exception message string)
    """
    limit = max_rows or Config.MAX_QUERY_ROWS

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))

            if not result.returns_rows:
                return [], [], None

            columns = list(result.keys())
            fetched_rows = result.fetchmany(limit)
            rows_dict = [dict(row._mapping) for row in fetched_rows]
            return columns, rows_dict, None

    except Exception as exc:
        return None, None, str(exc)


def query_scalar(sql_query: str):
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql_query)).scalar_one_or_none()
    except Exception:
        return None


def get_schema_overview() -> dict[str, list[str]]:
    return {
        "productlines": ["productLine", "textDescription", "htmlDescription", "image"],
        "products": ["productCode", "productName", "productLine", "productScale", "productVendor", "productDescription", "quantityInStock", "buyPrice", "MSRP"],
        "offices": ["officeCode", "city", "phone", "addressLine1", "addressLine2", "state", "country", "postalCode", "territory"],
        "employees": ["employeeNumber", "lastName", "firstName", "extension", "email", "officeCode", "reportsTo", "jobTitle"],
        "customers": ["customerNumber", "customerName", "contactLastName", "contactFirstName", "phone", "addressLine1", "addressLine2", "city", "state", "postalCode", "country", "salesRepEmployeeNumber", "creditLimit"],
        "payments": ["customerNumber", "checkNumber", "paymentDate", "amount"],
        "orders": ["orderNumber", "orderDate", "requiredDate", "shippedDate", "status", "comments", "customerNumber"],
        "orderdetails": ["orderNumber", "productCode", "quantityOrdered", "priceEach", "orderLineNumber"],
    }
