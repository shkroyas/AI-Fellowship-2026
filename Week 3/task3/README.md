# Task 3: Text-to-SQL Pipeline and Query Execution System

## Assignment Expectation
The goal is to build a pure, vanilla Python prompt-chaining pipeline (without using frameworks like LangChain or LangGraph) that takes the structured understanding from Task 2 and transforms it into executable SQL. The pipeline must generate SQL, validate it (blocking non-SELECT queries), execute it against PostgreSQL, handle errors with exactly one retry, and return a structured output.

## What Has Been Done
As detailed in the `submission_report.md`:
- **Prompt Chaining Pipeline**: Built a sequential execution chain: Decompose -> Generate SQL -> Security Filter -> Execute -> Auto-Fix on Error -> Log JSON.
- **Security & Reliability**: Implemented a rule-based regex security validator to block destructive DML/DDL queries. Added a dynamic API Key Rotator to cycle through Gemini keys upon hitting rate limits.
- **User Interface**: Developed a high-fidelity Streamlit chat dashboard (`streamlit_app.py`) that visually traces the pipeline steps in real-time, displays interactive data tables, and provides JSON logs.
- **Evaluation**: Integrated the evaluation framework from Task 1 to measure Execution Equivalence (EX-EQ) and Execution Success Rate (ESR).
