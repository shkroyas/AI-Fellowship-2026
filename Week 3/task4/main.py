from __future__ import annotations

import argparse
import json

from fastapi import FastAPI
from pydantic import BaseModel, Field

from db import ping_database
from graph.workflow import TextToSQLWorkflow


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)


app = FastAPI(title="Agentic Text-to-SQL API", version="1.0.0")


@app.get("/health")
def health_check():
    return {"status": "ok", "database": ping_database()}


@app.post("/query")
def run_query(request: QueryRequest):
    workflow = TextToSQLWorkflow()
    state = workflow.run(request.question.strip())
    return {
        "user_query": state.user_query,
        "plan": state.plan,
        "generated_sql": state.generated_sql,
        "is_valid_sql": state.is_valid_sql,
        "execution_results": state.execution_results,
        "final_answer": state.final_answer,
        "errors": state.errors,
        "retry_count": state.retry_count,
    }


def run_programmatic_workflow(question: str):
    workflow = TextToSQLWorkflow()
    state = workflow.run(question)
    print(json.dumps({
        "question": state.user_query,
        "plan": state.plan,
        "generated_sql": state.generated_sql,
        "is_valid_sql": state.is_valid_sql,
        "retry_count": state.retry_count,
        "errors": state.errors,
        "rows": len(state.execution_results),
        "final_answer": state.final_answer,
    }, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Run the agentic Text-to-SQL workflow.")
    parser.add_argument("question", nargs="?", default="How many customers are from the USA?")
    args = parser.parse_args()
    run_programmatic_workflow(args.question)


if __name__ == "__main__":
    main()
