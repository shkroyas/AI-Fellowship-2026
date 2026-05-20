# Database Schema Context for Prompt generation
SCHEMA_CONTEXT = """
CREATE TABLE productlines ( 
  "productLine" VARCHAR(50) PRIMARY KEY, 
  "textDescription" VARCHAR(4000), 
  "htmlDescription" TEXT, 
  "image" BYTEA 
); 

CREATE TABLE products ( 
  "productCode" VARCHAR(15) PRIMARY KEY, 
  "productName" VARCHAR(70) NOT NULL, 
  "productLine" VARCHAR(50) NOT NULL, 
  "productScale" VARCHAR(10) NOT NULL, 
  "productVendor" VARCHAR(50) NOT NULL, 
  "productDescription" TEXT NOT NULL, 
  "quantityInStock" INTEGER NOT NULL, 
  "buyPrice" NUMERIC(10,2) NOT NULL, 
  "MSRP" NUMERIC(10,2) NOT NULL, 
  FOREIGN KEY ("productLine") REFERENCES productlines("productLine") 
); 
 
CREATE TABLE offices ( 
  "officeCode" VARCHAR(10) PRIMARY KEY, 
  "city" VARCHAR(50) NOT NULL, 
  "phone" VARCHAR(50) NOT NULL, 
  "addressLine1" VARCHAR(50) NOT NULL, 
  "addressLine2" VARCHAR(50), 
  "state" VARCHAR(50), 
  "country" VARCHAR(50) NOT NULL, 
  "postalCode" VARCHAR(15) NOT NULL, 
  "territory" VARCHAR(10) NOT NULL 
); 
 
CREATE TABLE employees ( 
  "employeeNumber" INTEGER PRIMARY KEY, 
  "lastName" VARCHAR(50) NOT NULL, 
  "firstName" VARCHAR(50) NOT NULL, 
  "extension" VARCHAR(10) NOT NULL, 
  "email" VARCHAR(100) NOT NULL, 
  "officeCode" VARCHAR(10) NOT NULL, 
  "reportsTo" INTEGER, 
  "jobTitle" VARCHAR(50) NOT NULL, 
  FOREIGN KEY ("reportsTo") REFERENCES employees("employeeNumber"), 
  FOREIGN KEY ("officeCode") REFERENCES offices("officeCode") 
); 
 
CREATE TABLE customers ( 
  "customerNumber" INTEGER PRIMARY KEY, 
  "customerName" VARCHAR(50) NOT NULL, 
  "contactLastName" VARCHAR(50) NOT NULL, 
  "contactFirstName" VARCHAR(50) NOT NULL, 
  "phone" VARCHAR(50) NOT NULL, 
  "addressLine1" VARCHAR(50) NOT NULL, 
  "addressLine2" VARCHAR(50), 
  "city" VARCHAR(50) NOT NULL, 
  "state" VARCHAR(50), 
  "postalCode" VARCHAR(15), 
  "country" VARCHAR(50) NOT NULL, 
  "salesRepEmployeeNumber" INTEGER, 
  "creditLimit" NUMERIC(10,2), 
  FOREIGN KEY ("salesRepEmployeeNumber") REFERENCES employees("employeeNumber") 
); 
 
CREATE TABLE payments ( 
  "customerNumber" INTEGER, 
  "checkNumber" VARCHAR(50), 
  "paymentDate" DATE NOT NULL, 
  "amount" NUMERIC(10,2) NOT NULL, 
  PRIMARY KEY ("customerNumber", "checkNumber"), 
  FOREIGN KEY ("customerNumber") REFERENCES customers("customerNumber") 
); 

CREATE TABLE orders ( 
  "orderNumber" INTEGER PRIMARY KEY, 
  "orderDate" DATE NOT NULL, 
  "requiredDate" DATE NOT NULL, 
  "shippedDate" DATE, 
  "status" VARCHAR(15) NOT NULL, 
  "comments" TEXT, 
  "customerNumber" INTEGER NOT NULL, 
  FOREIGN KEY ("customerNumber") REFERENCES customers("customerNumber") 
); 

CREATE TABLE orderdetails ( 
  "orderNumber" INTEGER, 
  "productCode" VARCHAR(15), 
  "quantityOrdered" INTEGER NOT NULL, 
  "priceEach" NUMERIC(10,2) NOT NULL, 
  "orderLineNumber" SMALLINT NOT NULL, 
  PRIMARY KEY ("orderNumber", "productCode"), 
  FOREIGN KEY ("orderNumber") REFERENCES orders("orderNumber"), 
  FOREIGN KEY ("productCode") REFERENCES products("productCode") 
);
"""

# Prompt Template 1: Decomposition Prompt
DECOMPOSITION_PROMPT_TEMPLATE = """
You are a highly structured database query analyzer. 
Your task is to take a natural language query and decompose it into structured parts based on the database schema.

Here is the Database Schema:
{schema_context}

For the user question, extract a JSON object containing:
- "Intent": Clear description of what is being requested.
- "Tables": A JSON array of string table names involved.
- "Columns": A JSON array of string column names needed. Use the exact camelCase naming from the schema.
- "Filters": Any logical constraint filters/conditions mapped to SQL (e.g. "country = 'USA'", "amount > 100"). If no filters, specify "None".
- "Joins": Explanation or clause showing how tables are linked together. If no joins, specify "None".

User Question:
"{question}"

You MUST respond with a valid JSON object ONLY. Do not include markdown wraps or introductory text.
Example format:
{{
  "Intent": "Count total customers from the USA",
  "Tables": ["customers"],
  "Columns": ["customerNumber"],
  "Filters": "country = 'USA'",
  "Joins": "None"
}}
"""

# Prompt Template 2: SQL Generation Prompt
GENERATION_PROMPT_TEMPLATE = """
You are a PostgreSQL expert SQL generation engine.
Your task is to convert a decomposed JSON query plan into a single executable read-only PostgreSQL `SELECT` query.

Here is the Database Schema Context:
{schema_context}

Here is the Decomposed JSON Structure:
{decomposed_json}

CRITICAL RULES:
1. Generate ONLY a valid `SELECT` statement. Do not include any other SQL commands.
2. CASE SAFETY: All table names and column names that have camelCase characters (e.g. productLine, productCode, customerNumber, customerName, contactLastName, contactFirstName, salesRepEmployeeNumber, quantityInStock, buyPrice, orderLineNumber, orderNumber, orderDate, requiredDate, shippedDate, checkNumber, paymentDate, quantityOrdered, priceEach) MUST be double-quoted. E.g. SELECT "customerName", "phone" FROM customers;
3. Output ONLY the raw SQL query. Do not wrap it in markdown code blocks like ```sql ... ```. No explanations or extra characters.
"""

# Prompt Template 3: SQL Auto-Correction (Fixing) Prompt
CORRECTION_PROMPT_TEMPLATE = """
You are a database diagnostic expert. An generated PostgreSQL query threw an error during execution.
Your task is to fix the SQL query so that it compiles and executes successfully without throwing any exceptions.

Here is the Database Schema Context:
{schema_context}

Here is the Original User Question:
"{question}"

Here is the Failed SQL Query:
```sql
{failed_sql}
```

Here is the Exact Database Error Message returned by PostgreSQL:
"{error_message}"

CRITICAL RULES:
1. Correct the error (e.g., add missing joins, fix case sensitivity double-quoting, correct syntax).
2. All camelCase column names MUST be double-quoted (e.g. "customerNumber", "productName").
3. Make sure the output contains ONLY a valid, read-only SELECT query. Do not include DML like DELETE, DROP, etc.
4. Output ONLY the raw corrected SQL query without wrapping in markdown blocks or comments.
"""
