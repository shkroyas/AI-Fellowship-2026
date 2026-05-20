from dataclasses import dataclass, field
from typing import List, Dict, Any

from agents.planner import PlannerAgent
from agents.sql_generator import SQLGeneratorAgent
from agents.validator import ValidatorAgent
from agents.executor import ExecutorAgent
from agents.summarizer import SummarizerAgent

@dataclass
class AgentState:
    """Carries the state parameters flowing between agents in the workflow machine."""
    user_query: str
    plan: str = ""
    generated_sql: str = ""
    is_valid_sql: bool = False
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    final_answer: str = ""
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0

class TextToSQLWorkflow:
    """State-based Orchestrator machine routing agents through planner, generator, validator, executor, and summarizer."""
    
    def __init__(self):
        self.planner = PlannerAgent()
        self.generator = SQLGeneratorAgent()
        self.validator = ValidatorAgent()
        self.executor = ExecutorAgent()
        self.summarizer = SummarizerAgent()

    def run(self, user_query: str) -> AgentState:
        """
        Runs the complete agent state transition flow.
        
        Transitions:
        Planner ➔ Generator ➔ Validator (➔ Self-Correction on Fail) ➔ Executor (➔ Self-Correction on Fail) ➔ Summarizer
        """
        # Initialize empty state context
        state = AgentState(user_query=user_query)
        
        # 1. Planner Node
        print(f"\n[Planner Node]: Analyzing query '{state.user_query}'...")
        state.plan = self.planner.plan(state.user_query)
        
        # 2. Generator Node
        print("[Generator Node]: Synthesizing PostgreSQL statement plan...")
        state.generated_sql = self.generator.generate(state.user_query, state.plan)
        
        # 3. Validator Node
        print("[Validator Node]: Scanning query security parameters...")
        is_valid, val_error = self.validator.validate(state.generated_sql)
        state.is_valid_sql = is_valid
        
        if not is_valid:
            state.errors.append(val_error)
            print(f"  [Security Exception]: {val_error}")
            # Try to trigger self-correction
            self._handle_self_correction(state, val_error)
        else:
            # 4. Executor Node
            print("[Executor Node]: Running validated SQL against PostgreSQL container...")
            cols, rows, db_error = self.executor.execute(state.generated_sql)
            
            if db_error:
                state.errors.append(db_error)
                print(f"  [Database Exception]: {db_error}")
                # Try to trigger self-correction
                self._handle_self_correction(state, db_error)
            else:
                state.columns = cols
                state.execution_results = rows
                
        # 5. Summarizer Node
        if state.execution_results:
            print("[Summarizer Node]: Compiling human-friendly summary response...")
            state.final_answer = self.summarizer.summarize(
                state.user_query,
                state.generated_sql,
                state.execution_results
            )
        else:
            # Fallback error mapping if no results succeeded
            err_msg = state.errors[-1] if state.errors else "Execution failed without detailed trace logs."
            state.final_answer = f"I encountered an error during database processing: {err_msg}"
            
        print("[Workflow Complete]: Final answer generated successfully.")
        return state

    def _handle_self_correction(self, state: AgentState, error_msg: str):
        """Dynamic feedback loop node executing exactly 1 correction retry."""
        if state.retry_count < 1:
            state.retry_count += 1
            print(f"  [Self-Correction Node]: Retry {state.retry_count}/1. Curing failed query...")
            
            # Generator diagnoses error and cures query
            fixed_sql = self.generator.self_correct(
                state.user_query,
                state.plan,
                state.generated_sql,
                error_msg
            )
            state.generated_sql = fixed_sql
            
            # Re-Validate SQL
            is_valid, val_error = self.validator.validate(fixed_sql)
            state.is_valid_sql = is_valid
            
            if not is_valid:
                state.errors.append(f"Fixed SQL failed security: {val_error}")
                print(f"    [Correction Failed - Security Exception]: {val_error}")
            else:
                # Re-Execute cured SQL
                cols, rows, db_error = self.executor.execute(fixed_sql)
                if db_error:
                    state.errors.append(f"Fixed SQL failed execution: {db_error}")
                    print(f"    [Correction Failed - Database Exception]: {db_error}")
                else:
                    state.columns = cols
                    state.execution_results = rows
                    print("    [Correction Success]: Fixed SQL executed successfully!")
        else:
            print("  [Self-Correction Node]: Retry limit exceeded. Aborting.")
