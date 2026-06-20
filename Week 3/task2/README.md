# Task 2: Query Understanding (Decomposition Task)

## Assignment Expectation
The objective is to build a system that breaks natural language questions into structured components before writing SQL. For each question, the system must identify the Intent, Tables involved, Columns needed, Filters/conditions, and Joins. This simulates the Query Understanding phase of a modern AI backend system.

## What Has Been Done
As detailed in the `query_decomposition_report.md`:
- **Decomposition Engine**: Developed a Python-based decomposition module (`query_decomposition.py`) that uses Gemini 2.5 Flash to extract the structured components (Intent, Tables, Columns, Filters, Joins).
- **Resilience**: Implemented automatic exponential backoff and rate-limiting handling to support Gemini Free Tier API limits seamlessly.
- **Output Artifacts**: Processed the 50 benchmark queries and exported the structured decomposition records into `decomposed_queries.json` and `decomposed_queries.csv`.
