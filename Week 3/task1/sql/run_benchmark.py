import csv
import os
import psycopg2

from dotenv import load_dotenv

# Resolve paths relative to the script location
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, "..", ".env")
load_dotenv(dotenv_path=env_path)

# Database connection parameters
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

# The hand-crafted SQL queries for all 50 benchmark questions
BENCHMARK_QUERIES = [
    # 1. List all products
    {
        "sql": 'SELECT * FROM products;',
        "explanation": "Retrieves all columns and all records from the `products` table to show every product in the database."
    },
    # 2. Get all customers
    {
        "sql": 'SELECT * FROM customers;',
        "explanation": "Retrieves all columns and all records from the `customers` table to show every customer in the database."
    },
    # 3. Show all orders
    {
        "sql": 'SELECT * FROM orders;',
        "explanation": "Retrieves all columns and all records from the `orders` table to display the complete list of sales orders."
    },
    # 4. List all employees
    {
        "sql": 'SELECT * FROM employees;',
        "explanation": "Retrieves all columns and all records from the `employees` table to show the complete employee roster."
    },
    # 5. Get all offices
    {
        "sql": 'SELECT * FROM offices;',
        "explanation": "Retrieves all columns and all records from the `offices` table to list all company office locations."
    },
    # 6. Show all product lines
    {
        "sql": 'SELECT * FROM productlines;',
        "explanation": "Retrieves all columns and all records from the `productlines` table to show the product lines (categories) available."
    },
    # 7. List all payments
    {
        "sql": 'SELECT * FROM payments;',
        "explanation": "Retrieves all columns and all records from the `payments` table to display all historical financial transactions."
    },
    # 8. Get product names and prices
    {
        "sql": 'SELECT "productName", "buyPrice" FROM products;',
        "explanation": "Selects the specific columns `productName` and `buyPrice` from the `products` table. Double quotes are used to preserve case-sensitivity in PostgreSQL."
    },
    # 9. Get customer names and cities
    {
        "sql": 'SELECT "customerName", "city" FROM customers;',
        "explanation": "Selects the specific columns `customerName` and `city` from the `customers` table to identify customer locations."
    },
    # 10. List employee first and last names
    {
        "sql": 'SELECT "firstName", "lastName" FROM employees;',
        "explanation": "Selects the `firstName` and `lastName` columns from the `employees` table to get employee full names."
    },
    # 11. Get all order dates
    {
        "sql": 'SELECT "orderDate" FROM orders;',
        "explanation": "Selects the `orderDate` column from the `orders` table to retrieve all transaction dates."
    },
    # 12. Show product vendor list
    {
        "sql": 'SELECT DISTINCT "productVendor" FROM products;',
        "explanation": "Retrieves unique values from the `productVendor` column in the `products` table using the `DISTINCT` keyword to list all unique product suppliers."
    },
    # 13. Get all product codes
    {
        "sql": 'SELECT "productCode" FROM products;',
        "explanation": "Selects the primary key `productCode` from the `products` table."
    },
    # 14. List all countries from offices
    {
        "sql": 'SELECT DISTINCT "country" FROM offices;',
        "explanation": "Retrieves the distinct countries where the company has a physical office using the `DISTINCT` keyword."
    },
    # 15. Show all order statuses
    {
        "sql": 'SELECT DISTINCT "status" FROM orders;',
        "explanation": "Retrieves unique order statuses (e.g., Shipped, Resolved, Cancelled, In Process, On Hold) from the `orders` table."
    },
    # 16. Get all payment amounts
    {
        "sql": 'SELECT "amount" FROM payments;',
        "explanation": "Selects the `amount` column from the `payments` table."
    },
    # 17. List all job titles
    {
        "sql": 'SELECT DISTINCT "jobTitle" FROM employees;',
        "explanation": "Retrieves the unique job titles across the entire employee database."
    },
    # 18. Get customer phone numbers
    {
        "sql": 'SELECT "customerName", "phone" FROM customers;',
        "explanation": "Selects the `customerName` and `phone` columns from the `customers` table for customer contact information."
    },
    # 19. Show product MSRP values
    {
        "sql": 'SELECT "productName", "MSRP" FROM products;',
        "explanation": "Selects the `productName` and `MSRP` columns from the `products` table to view recommended retail prices."
    },
    # 20. List order numbers
    {
        "sql": 'SELECT "orderNumber" FROM orders;',
        "explanation": "Selects the primary key `orderNumber` column from the `orders` table."
    },
    # 21. Get orders with customer names
    {
        "sql": 'SELECT o."orderNumber", o."orderDate", c."customerName" FROM orders o JOIN customers c ON o."customerNumber" = c."customerNumber";',
        "explanation": "Performs an `INNER JOIN` between the `orders` and `customers` tables using the foreign key relationship on `customerNumber` to map order data to the respective customer name."
    },
    # 22. Get employees with office city
    {
        "sql": 'SELECT e."employeeNumber", e."firstName", e."lastName", o."city" AS "officeCity" FROM employees e JOIN offices o ON e."officeCode" = o."officeCode";',
        "explanation": "Performs an `INNER JOIN` between the `employees` and `offices` tables on `officeCode` to fetch the city where each employee's office is located."
    },
    # 23. Get payments with customer names
    {
        "sql": 'SELECT p."checkNumber", p."amount", p."paymentDate", c."customerName" FROM payments p JOIN customers c ON p."customerNumber" = c."customerNumber";',
        "explanation": "Joins the `payments` table with the `customers` table on `customerNumber` to display transaction details with human-readable customer names."
    },
    # 24. Get order details with product names
    {
        "sql": 'SELECT od."orderNumber", od."productCode", p."productName", od."quantityOrdered", od."priceEach" FROM orderdetails od JOIN products p ON od."productCode" = p."productCode";',
        "explanation": "Joins the `orderdetails` table with the `products` table on `productCode` to retrieve itemized orders with their actual product names instead of just codes."
    },
    # 25. Get products with product line description
    {
        "sql": 'SELECT p."productCode", p."productName", p."productLine", pl."textDescription" FROM products p JOIN productlines pl ON p."productLine" = pl."productLine";',
        "explanation": "Joins the `products` table with the `productlines` table on `productLine` to display each product alongside its category's detailed text description."
    },
    # 26. Get customers with sales rep names
    {
        "sql": 'SELECT c."customerNumber", c."customerName", e."firstName" AS "salesRepFirstName", e."lastName" AS "salesRepLastName" FROM customers c JOIN employees e ON c."salesRepEmployeeNumber" = e."employeeNumber";',
        "explanation": "Joins the `customers` table with the `employees` table on `salesRepEmployeeNumber` to show customers and the first and last names of their designated sales representatives."
    },
    # 27. Get orders with customer city
    {
        "sql": 'SELECT o."orderNumber", o."status", c."customerName", c."city" AS "customerCity" FROM orders o JOIN customers c ON o."customerNumber" = c."customerNumber";',
        "explanation": "Joins the `orders` table with the `customers` table on `customerNumber` to fetch order status alongside the customer's name and location city."
    },
    # 28. Get employees and their manager
    {
        "sql": 'SELECT e."firstName" AS "employeeFirstName", e."lastName" AS "employeeLastName", m."firstName" AS "managerFirstName", m."lastName" AS "managerLastName" FROM employees e LEFT JOIN employees m ON e."reportsTo" = m."employeeNumber";',
        "explanation": "Performs a self-join on the `employees` table using a `LEFT JOIN` on the `reportsTo` column to match each employee to their supervisor. The `LEFT JOIN` ensures the President (who reports to no one) is still returned with a NULL manager."
    },
    # 29. Get orderdetails with product vendor
    {
        "sql": 'SELECT od."orderNumber", od."productCode", p."productName", p."productVendor" FROM orderdetails od JOIN products p ON od."productCode" = p."productCode";',
        "explanation": "Joins `orderdetails` and `products` on `productCode` to show which vendor supplied each ordered product."
    },
    # 30. Get payments with customer country
    {
        "sql": 'SELECT p."checkNumber", p."amount", c."customerName", c."country" FROM payments p JOIN customers c ON p."customerNumber" = c."customerNumber";',
        "explanation": "Joins `payments` and `customers` on `customerNumber` to display the amount paid and the country of the customer who made the payment."
    },
    # 31. Count customers per country
    {
        "sql": 'SELECT "country", COUNT(*) AS "customerCount" FROM customers GROUP BY "country" ORDER BY "customerCount" DESC;',
        "explanation": "Groups the `customers` table by the `country` column and uses the `COUNT(*)` aggregate function to calculate the number of customers per country, sorted in descending order."
    },
    # 32. Total payments per customer
    {
        "sql": 'SELECT c."customerNumber", c."customerName", SUM(p."amount") AS "totalPayments" FROM customers c JOIN payments p ON c."customerNumber" = p."customerNumber" GROUP BY c."customerNumber", c."customerName" ORDER BY "totalPayments" DESC;',
        "explanation": "Joins `customers` and `payments` on `customerNumber`, groups by customer details, and sums the `amount` column using the `SUM()` aggregate to find each customer's total spending."
    },
    # 33. Number of orders per status
    {
        "sql": 'SELECT "status", COUNT(*) AS "orderCount" FROM orders GROUP BY "status" ORDER BY "orderCount" DESC;',
        "explanation": "Groups the `orders` table by `status` and uses the `COUNT(*)` aggregate function to determine how many orders are in each status (Shipped, Cancelled, etc.)."
    },
    # 34. Products per product line
    {
        "sql": 'SELECT "productLine", COUNT(*) AS "productCount" FROM products GROUP BY "productLine" ORDER BY "productCount" DESC;',
        "explanation": "Groups the `products` table by the `productLine` category and counts the number of individual catalog products in each line."
    },
    # 35. Employees per office
    {
        "sql": 'SELECT o."officeCode", o."city", COUNT(e."employeeNumber") AS "employeeCount" FROM offices o LEFT JOIN employees e ON o."officeCode" = e."officeCode" GROUP BY o."officeCode", o."city" ORDER BY "employeeCount" DESC;',
        "explanation": "Performs a `LEFT JOIN` of `offices` with `employees` on `officeCode`, groups by office details, and counts the employee records to see staffing numbers per office location."
    },
    # 36. Total stock per product vendor
    {
        "sql": 'SELECT "productVendor", SUM("quantityInStock") AS "totalStock" FROM products GROUP BY "productVendor" ORDER BY "totalStock" DESC;',
        "explanation": "Groups products by the `productVendor` supplier and computes the sum of the `quantityInStock` column to see the total inventory volume supplied by each vendor."
    },
    # 37. Average buy price per product line
    {
        "sql": 'SELECT "productLine", ROUND(AVG("buyPrice"), 2) AS "averageBuyPrice" FROM products GROUP BY "productLine" ORDER BY "averageBuyPrice" DESC;',
        "explanation": "Groups the product catalog by `productLine` and calculates the average `buyPrice` using `AVG()`, rounding the results to two decimal places."
    },
    # 38. Orders per customer
    {
        "sql": 'SELECT c."customerNumber", c."customerName", COUNT(o."orderNumber") AS "orderCount" FROM customers c LEFT JOIN orders o ON c."customerNumber" = o."customerNumber" GROUP BY c."customerNumber", c."customerName" ORDER BY "orderCount" DESC;',
        "explanation": "Performs a `LEFT JOIN` between `customers` and `orders` on `customerNumber`, groups the data, and counts the matching orders to determine order frequency per customer (including those with 0 orders)."
    },
    # 39. Max MSRP per product line
    {
        "sql": 'SELECT "productLine", MAX("MSRP") AS "maxMSRP" FROM products GROUP BY "productLine" ORDER BY "maxMSRP" DESC;',
        "explanation": "Groups products by `productLine` and uses the `MAX()` aggregate to find the highest Manufacturer's Suggested Retail Price within each category."
    },
    # 40. Min buy price per vendor
    {
        "sql": 'SELECT "productVendor", MIN("buyPrice") AS "minBuyPrice" FROM products GROUP BY "productVendor" ORDER BY "minBuyPrice" ASC;',
        "explanation": "Groups products by `productVendor` and uses the `MIN()` aggregate to find the cheapest catalog buy price for each vendor."
    },
    # 41. Total number of customers
    {
        "sql": 'SELECT COUNT(*) AS "totalCustomers" FROM customers;',
        "explanation": "Uses the `COUNT(*)` aggregate function on the `customers` table to get the total number of registered customers."
    },
    # 42. Total number of products
    {
        "sql": 'SELECT COUNT(*) AS "totalProducts" FROM products;',
        "explanation": "Uses the `COUNT(*)` aggregate function on the `products` table to get the total number of items in the company catalog."
    },
    # 43. Total revenue from payments
    {
        "sql": 'SELECT SUM("amount") AS "totalRevenue" FROM payments;',
        "explanation": "Applies the `SUM()` aggregate function to the `amount` column in the `payments` table to calculate total historical business revenue."
    },
    # 44. Average product price
    {
        "sql": 'SELECT ROUND(AVG("buyPrice"), 2) AS "averageProductPrice" FROM products;',
        "explanation": "Applies the `AVG()` aggregate function to the `buyPrice` column in the `products` table and rounds to two decimal places."
    },
    # 45. Max payment amount
    {
        "sql": 'SELECT MAX("amount") AS "maxPayment" FROM payments;',
        "explanation": "Uses the `MAX()` aggregate function on the `amount` column in the `payments` table to find the single largest financial transaction."
    },
    # 46. Min payment amount
    {
        "sql": 'SELECT MIN("amount") AS "minPayment" FROM payments;',
        "explanation": "Uses the `MIN()` aggregate function on the `amount` column in the `payments` table to find the single smallest payment transaction."
    },
    # 47. Count total orders
    {
        "sql": 'SELECT COUNT(*) AS "totalOrders" FROM orders;',
        "explanation": "Applies the `COUNT(*)` aggregate function on the `orders` table to retrieve the total count of placed orders."
    },
    # 48. Total quantity in stock
    {
        "sql": 'SELECT SUM("quantityInStock") AS "totalQuantityInStock" FROM products;',
        "explanation": "Sums the `quantityInStock` column across the entire `products` table to find the net physical inventory in stock."
    },
    # 49. Average MSRP
    {
        "sql": 'SELECT ROUND(AVG("MSRP"), 2) AS "averageMSRP" FROM products;',
        "explanation": "Calculates the average Manufacturer's Suggested Retail Price across all catalog items, rounded to 2 decimal places."
    },
    # 50. Number of employees
    {
        "sql": 'SELECT COUNT(*) AS "totalEmployees" FROM employees;',
        "explanation": "Applies the `COUNT(*)` aggregate function on the `employees` table to find the total headcount of staff."
    }
]

def format_cell(val):
    if val is None:
        return "NULL"
    # Format bytes to string representation
    if isinstance(val, bytes) or isinstance(val, bytearray):
        return f"<binary data: {len(val)} bytes>"
    # Convert decimals/floats/dates to standard strings
    return str(val)

def run_benchmarks():
    csv_path = r"c:\Users\Royas Shakya\Downloads\AI_Fellowship\AI-Fellowship-2026\Week 3\task1\sql\sql_questions_only.csv"
    output_md_path = r"c:\Users\Royas Shakya\Downloads\AI_Fellowship\AI-Fellowship-2026\Week 3\task1\sql_benchmark_results.md"
    
    print(f"Reading questions from {csv_path}...")
    questions = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        for row in reader:
            if row:
                questions.append(row[0].strip())
    
    print(f"Found {len(questions)} questions in CSV.")
    if len(questions) != len(BENCHMARK_QUERIES):
        print(f"Warning: CSV has {len(questions)} questions but code defines {len(BENCHMARK_QUERIES)} queries. We will map them by index.")
    
    # Establish connection
    print("Connecting to database...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    report_lines = []
    report_lines.append("# Task 1: SQL Benchmark Dataset - Query Execution & Verification Report")
    report_lines.append(f"\n- **Database:** PostgreSQL 16 (`classicmodels`)")
    report_lines.append(f"- **Total Benchmark Questions:** {len(BENCHMARK_QUERIES)}")
    report_lines.append(f"- **Execution System:** Automated Python Benchmark Runner")
    report_lines.append(f"- **Date Generated:** 2026-05-20")
    report_lines.append("\n---\n")
    
    for i, benchmark in enumerate(BENCHMARK_QUERIES):
        q_idx = i + 1
        # Use question from CSV if available, otherwise fallback
        question_text = questions[i] if i < len(questions) else f"Question {q_idx}"
        sql_query = benchmark["sql"]
        explanation = benchmark["explanation"]
        
        print(f"Executing Q{q_idx}: {question_text}")
        
        try:
            cursor.execute(sql_query)
            # Retrieve metadata
            colnames = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall() if cursor.description else []
            row_count = len(rows)
            
            # Format sample rows
            sample_rows = rows[:5]
            
            report_lines.append(f"## Q{q_idx}: {question_text}")
            report_lines.append(f"\n### Ground Truth SQL Query\n```sql\n{sql_query}\n```")
            report_lines.append(f"\n### Query Explanation\n{explanation}")
            report_lines.append(f"\n### Execution Results Summary")
            report_lines.append(f"- **Execution Status:** `SUCCESS` ✅")
            report_lines.append(f"- **Total Rows Returned:** `{row_count}` rows")
            
            if colnames:
                report_lines.append(f"- **Columns Returned:** `[" + ", ".join([f'"{col}"' for col in colnames]) + "]`")
                report_lines.append(f"\n### Sample Output (Top {len(sample_rows)} rows)")
                # Generate markdown table
                md_table_header = "| " + " | ".join(colnames) + " |"
                md_table_divider = "| " + " | ".join(["---"] * len(colnames)) + " |"
                report_lines.append(md_table_header)
                report_lines.append(md_table_divider)
                for r in sample_rows:
                    md_table_row = "| " + " | ".join([format_cell(cell) for cell in r]) + " |"
                    report_lines.append(md_table_row)
            else:
                report_lines.append(f"\n*No columns/rows returned by this SELECT statement (empty description).*")
            
            report_lines.append("\n---\n")
            
        except Exception as e:
            print(f"ERROR executing Q{q_idx}: {e}")
            conn.rollback()
            report_lines.append(f"## Q{q_idx}: {question_text}")
            report_lines.append(f"\n### Ground Truth SQL Query\n```sql\n{sql_query}\n```")
            report_lines.append(f"\n### Query Explanation\n{explanation}")
            report_lines.append(f"\n### Execution Results Summary")
            report_lines.append(f"- **Execution Status:** `FAILED` ❌")
            report_lines.append(f"- **Error Message:** `{str(e)}`")
            report_lines.append("\n---\n")
            
    cursor.close()
    conn.close()
    
    # Save the output file
    print(f"Writing report to {output_md_path}...")
    with open(output_md_path, mode="w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print("Benchmark generation complete!")

if __name__ == "__main__":
    run_benchmarks()
