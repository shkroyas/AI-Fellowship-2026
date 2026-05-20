import csv
import json
import os
import sys
import typing_extensions as typing
import google.generativeai as genai

# Import configurations
try:
    import config
    config.validate_config()
except ImportError:
    print("Error: Could not import config.py. Please ensure it is present in the same directory.")
    sys.exit(1)
except ValueError as e:
    print(f"Configuration Error: {e}")
    sys.exit(1)

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)

# Define the classicmodels Database Schema to provide accurate context to the model
DATABASE_SCHEMA_CONTEXT = """
The database is PostgreSQL 16 named 'classicmodels'. Below is the exact schema:

1. Table: productlines
   - "productLine" VARCHAR(50) PRIMARY KEY
   - "textDescription" VARCHAR(4000)
   - "htmlDescription" TEXT
   - "image" BYTEA

2. Table: products
   - "productCode" VARCHAR(15) PRIMARY KEY
   - "productName" VARCHAR(70) NOT NULL
   - "productLine" VARCHAR(50) NOT NULL (Foreign Key referencing productlines."productLine")
   - "productScale" VARCHAR(10) NOT NULL
   - "productVendor" VARCHAR(50) NOT NULL
   - "productDescription" TEXT NOT NULL
   - "quantityInStock" INTEGER NOT NULL
   - "buyPrice" NUMERIC(10,2) NOT NULL
   - "MSRP" NUMERIC(10,2) NOT NULL

3. Table: offices
   - "officeCode" VARCHAR(10) PRIMARY KEY
   - "city" VARCHAR(50) NOT NULL
   - "phone" VARCHAR(50) NOT NULL
   - "addressLine1" VARCHAR(50) NOT NULL
   - "addressLine2" VARCHAR(50)
   - "state" VARCHAR(50)
   - "country" VARCHAR(50) NOT NULL
   - "postalCode" VARCHAR(15) NOT NULL
   - "territory" VARCHAR(10) NOT NULL

4. Table: employees
   - "employeeNumber" INTEGER PRIMARY KEY
   - "lastName" VARCHAR(50) NOT NULL
   - "firstName" VARCHAR(50) NOT NULL
   - "extension" VARCHAR(10) NOT NULL
   - "email" VARCHAR(100) NOT NULL
   - "officeCode" VARCHAR(10) NOT NULL (Foreign Key referencing offices."officeCode")
   - "reportsTo" INTEGER (Self-referential Foreign Key referencing employees."employeeNumber")
   - "jobTitle" VARCHAR(50) NOT NULL

5. Table: customers
   - "customerNumber" INTEGER PRIMARY KEY
   - "customerName" VARCHAR(50) NOT NULL
   - "contactLastName" VARCHAR(50) NOT NULL
   - "contactFirstName" VARCHAR(50) NOT NULL
   - "phone" VARCHAR(50) NOT NULL
   - "addressLine1" VARCHAR(50) NOT NULL
   - "addressLine2" VARCHAR(50)
   - "city" VARCHAR(50) NOT NULL
   - "state" VARCHAR(50)
   - "postalCode" VARCHAR(15)
   - "country" VARCHAR(50) NOT NULL
   - "salesRepEmployeeNumber" INTEGER (Foreign Key referencing employees."employeeNumber")
   - "creditLimit" NUMERIC(10,2)

6. Table: payments
   - "customerNumber" INTEGER NOT NULL (Foreign Key referencing customers."customerNumber")
   - "checkNumber" VARCHAR(50) NOT NULL
   - "paymentDate" DATE NOT NULL
   - "amount" NUMERIC(10,2) NOT NULL
   - Primary Key: ("customerNumber", "checkNumber")

7. Table: orders
   - "orderNumber" INTEGER PRIMARY KEY
   - "orderDate" DATE NOT NULL
   - "requiredDate" DATE NOT NULL
   - "shippedDate" DATE
   - "status" VARCHAR(15) NOT NULL
   - "comments" TEXT
   - "customerNumber" INTEGER NOT NULL (Foreign Key referencing customers."customerNumber")

8. Table: orderdetails
   - "orderNumber" INTEGER NOT NULL (Foreign Key referencing orders."orderNumber")
   - "productCode" VARCHAR(15) NOT NULL (Foreign Key referencing products."productCode")
   - "quantityOrdered" INTEGER NOT NULL
   - "priceEach" NUMERIC(10,2) NOT NULL
   - "orderLineNumber" SMALLINT NOT NULL
   - Primary Key: ("orderNumber", "productCode")

Case Sensitivity Note: All column names that are camelCase (like customerNumber, customerName) must be double-quoted in SQL queries.
"""

# Define the Structured Output format using Python Type Hints for Gemini
class QueryDecomposition(typing.TypedDict):
    intent: str
    tables: typing.List[str]
    columns: typing.List[str]
    filters: str
    joins: str

import time

def decompose_question(question: str) -> dict:
    """Uses Gemini 2.5 Flash to decompose a natural language question based on the database schema."""
    
    prompt = f"""
You are an expert database AI architect. Your task is to perform **Query Decomposition** on a natural language user question.
You must analyze the question and the database schema to break the question down into logical parts.

Database Schema Context:
{DATABASE_SCHEMA_CONTEXT}

User Natural Language Question:
"{question}"

Analyze the question carefully:
1. Identify the 'intent' (what is being asked, e.g., "Count total customers", "List employees working in Paris").
2. Identify the exact 'tables' involved. Choose only from the tables present in the database schema.
3. Identify the exact 'columns' needed. Use the correct camelCase column names from the schema.
4. Identify any 'filters' or conditional clauses (e.g., "country = 'USA'", "buyPrice > 50").
5. Identify the exact 'joins' required, specifying the matching foreign keys (e.g., "Join orders and customers on orders.customerNumber = customers.customerNumber", or "None").

You must return the output matching the requested schema structure.
"""

    max_retries = 5
    base_delay = 12  # Sleep base duration (Gemini free tier resets requests per minute)

    for attempt in range(max_retries):
        try:
            # Initialize Gemini 2.5 Flash model
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Request a structured JSON output
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=QueryDecomposition,
                    temperature=0.1 # Low temperature for high precision schema linking
                )
            )
            
            # Parse the JSON response
            result = json.loads(response.text)
            return result
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower() or "limit" in error_str.lower():
                delay = base_delay * (attempt + 1)
                print(f"  [Rate Limit hit] Gemini API 429 warning. Sleeping for {delay} seconds before retrying (Attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)
            else:
                print(f"Error during API call: {e}")
                break
                
    return {}

def print_decomposition(question: str, decomposition: dict):
    """Formats and prints the decomposition in a beautiful, structured CLI interface."""
    if not decomposition:
        print("Failed to decompose the query.")
        return

    print("\n" + "="*60)
    print(f"Natural Language Question:\n  \"{question}\"")
    print("="*60)
    print(f"- Intent: {decomposition.get('intent', 'N/A')}")
    print(f"- Tables: {', '.join(decomposition.get('tables', []))}")
    print(f"- Columns: {', '.join(decomposition.get('columns', []))}")
    print(f"- Filters: {decomposition.get('filters', 'None')}")
    print(f"- Joins: {decomposition.get('joins', 'None')}")
    print("="*60 + "\n")

def batch_decompose_csv():
    """Reads questions from the benchmark CSV, decomposes each using Gemini, and saves outputs in JSON and CSV formats."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(script_dir, "sql", "sql_questions_only.csv")
    output_json = os.path.join(script_dir, "decomposed_queries.json")
    output_csv = os.path.join(script_dir, "decomposed_queries.csv")
    
    if not os.path.exists(input_csv):
        print(f"Error: Input CSV not found at {input_csv}")
        return
        
    print(f"Reading questions from {input_csv}...")
    questions = []
    with open(input_csv, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader) # Skip header
        for row in reader:
            if row:
                questions.append(row[0].strip())
                
    total_questions = len(questions)
    print(f"Found {total_questions} questions. Starting batch decomposition with Gemini 2.5 Flash...")
    
    decompositions = []
    
    for idx, question in enumerate(questions, 1):
        print(f"[{idx}/{total_questions}] Decomposing: \"{question}\"")
        decomp = decompose_question(question)
        if decomp:
            record = {
                "question": question,
                "intent": decomp.get("intent", ""),
                "tables": ", ".join(decomp.get("tables", [])),
                "columns": ", ".join(decomp.get("columns", [])),
                "filters": decomp.get("filters", "None"),
                "joins": decomp.get("joins", "None")
            }
            decompositions.append(record)
        else:
            print(f"  Warning: Failed to decompose question {idx}")
            decompositions.append({
                "question": question,
                "intent": "ERROR",
                "tables": "",
                "columns": "",
                "filters": "",
                "joins": ""
            })
            
    # Write JSON output
    print(f"Saving JSON output to {output_json}...")
    with open(output_json, mode="w", encoding="utf-8") as f:
        json.dump(decompositions, f, indent=2)
        
    # Write CSV output
    print(f"Saving CSV output to {output_csv}...")
    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "intent", "tables", "columns", "filters", "joins"])
        writer.writeheader()
        writer.writerows(decompositions)
        
    print("Batch processing complete! JSON and CSV outputs generated successfully.")

def main():
    print("=== Text-to-SQL Agent: Query Decomposition Tool ===")
    
    # If --batch CLI argument is passed, run batch processing immediately
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        batch_decompose_csv()
        return

    # If a generic question is passed as CLI argument, decompose it immediately
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(f"Decomposing CLI query: '{question}'...")
        decomp = decompose_question(question)
        print_decomposition(question, decomp)
        return

    # Interactive CLI loop
    print("Enter a natural language question to decompose.")
    print("Or type 'batch' to process all questions in the CSV.")
    print("Or type 'exit' to quit.")
    
    example_questions = [
        "How many customers are from the USA?",
        "Get all orders with customer names.",
        "List employee first and last names working in Boston.",
        "What is the total payments per customer?"
    ]
    print("\nExample questions you can copy-paste:")
    for idx, eq in enumerate(example_questions, 1):
        print(f"  {idx}. {eq}")
    
    while True:
        try:
            user_input = input("\nQuery > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Exiting tool. Good luck with Task 2!")
                break
            if user_input.lower() == 'batch':
                batch_decompose_csv()
                continue
            
            print("Analyzing with Gemini 2.5 Flash...")
            decomp = decompose_question(user_input)
            print_decomposition(user_input, decomp)
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting tool.")
            break

if __name__ == "__main__":
    main()
