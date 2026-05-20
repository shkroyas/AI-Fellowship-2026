import sys
from graph.workflow import TextToSQLWorkflow

def run_programmatic_workflow(question: str):
    """Executes the complete Agentic Text-to-SQL Workflow for a given query."""
    print("=" * 90)
    print("🚀  TRIGGERING AGENTIC TEXT-TO-SQL STATE WORKFLOW")
    print("=" * 90)
    print(f"User Input Question: \"{question}\"\n")
    
    workflow = TextToSQLWorkflow()
    final_state = workflow.run(question)
    
    print("\n" + "-" * 40 + " EXECUTION STATE DETAILS " + "-" * 40)
    print(f"1. Strategic Plan:\n{final_state.plan}\n")
    print(f"2. Final Generated SQL:\n   {final_state.generated_sql}\n")
    print(f"3. Security Validation Passed: {final_state.is_valid_sql}")
    print(f"4. Self-Correction Cures Triggered: {final_state.retry_count > 0}")
    print(f"5. Total Result Records Retrieved: {len(final_state.execution_results) if final_state.execution_results else 0}")
    
    if final_state.errors:
        print(f"6. Captures Exceptions: {final_state.errors}")
        
    print("\n" + "=" * 38 + " FINAL NL SUMMARY ANSWER " + "=" * 38)
    print(final_state.final_answer)
    print("=" * 90 + "\n")

if __name__ == "__main__":
    # Retrieve user input from CLI args or run default benchmark question
    default_q = "How many customers are from the USA?"
    query = sys.argv[1] if len(sys.argv) > 1 else default_q
    run_programmatic_workflow(query)
