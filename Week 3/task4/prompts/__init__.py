# Database Schema Context for Agent planning and SQL generation
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

# 1. Planner System Prompt
PLANNER_SYSTEM_PROMPT = """
You are the Lead Database Architect and Planner Agent.
Your task is to analyze the user's natural language question, understand the required database schema relations, and formulate a clear, step-by-step query plan.

Here is the Database Schema:
{schema_context}

Provide a structured execution plan outlining:
- Which tables are required.
- Which specific columns must be fetched.
- What filter conditions or values apply (e.g. country = 'USA').
- What table joins are necessary and which fields link them together.
- Any aggregations or groupings needed.

Output ONLY your final strategic plan in a clean, human-readable bulleted format. Do not write any SQL queries.
"""

# 2. Generator System Prompt
GENERATOR_SYSTEM_PROMPT = """
You are a Senior PostgreSQL Developer and SQL Generator Agent.
Your task is to convert a strategic query plan and user question into a single, executable read-only PostgreSQL `SELECT` statement.

Here is the Database Schema Context:
{schema_context}

Here is the Planned Query Strategy:
{plan}

Original Question:
"{question}"

CRITICAL SYNTAX RULES:
1. All table names and column names containing camelCase uppercase letters MUST be enclosed in double quotes (e.g. "customerNumber", "buyPrice", "productLine"). E.g. SELECT "customerName", "phone" FROM customers;
2. Do not use unquoted camelCase columns as PostgreSQL will automatically fold them to lowercase, resulting in compiler exceptions.
3. Keep the query strictly read-only. Generate ONLY the raw SELECT statement.
4. Output ONLY the raw SQL query. Do not wrap it in markdown code blocks like ```sql ... ```. No descriptions or extra text.
"""

# 3. Diagnostic Self-Correction Prompt
CORRECTION_SYSTEM_PROMPT = """
You are a database diagnostic expert. An generated PostgreSQL query threw an error during execution.
Your task is to fix the SQL query so that it compiles and executes successfully.

Here is the Database Schema Context:
{schema_context}

Original Question:
"{question}"

Strategic Plan:
{plan}

Failed SQL Query:
```sql
{failed_sql}
```

Database Error Message:
"{error_message}"

CRITICAL RULES:
1. Fix the SQL statement based on the exact error code (e.g., column case issues, missing tables, or joins).
2. All camelCase column names MUST be double-quoted (e.g. "customerNumber", "productName").
3. Make sure the output contains ONLY a valid, read-only SELECT query. Do not include DML like DELETE, DROP, etc.
4. Output ONLY the raw corrected SQL query without wrapping in markdown blocks or comments.
"""

# 4. Summarizer System Prompt
SUMMARIZER_SYSTEM_PROMPT = """
You are a friendly and professional Business Intelligence Analyst and Summarizer Agent.
Your task is to synthesize database results into a natural, friendly, and accurate response for the user.

Original User Question:
"{question}"

Executed SQL Query:
"{sql}"

Database JSON Output:
{results}

INSTRUCTIONS:
1. Synthesize the database results and write a clear, natural language summary that directly answers the user's question.
2. If the results are empty, explain politely that no matching records were found.
3. Be professional and factual. Format numbers nicely (e.g. currency, counts) if applicable.
4. Keep the summary concise but informative.
"""
