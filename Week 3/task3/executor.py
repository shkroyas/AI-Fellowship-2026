import os
import json
from datetime import datetime
from database import DatabaseConnection
from sql_generator import SQLGenerator
from validator import SQLValidator, SQLValidationError

class TextToSQLPipeline:
    """Orchestrates the sequential Prompt Chaining Text-to-SQL Pipeline and error correction retry logic."""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.generator = SQLGenerator()
        
        # Ensure log directory exists
        self.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        self.log_file = os.path.join(self.log_dir, "query_logs.json")
        os.makedirs(self.log_dir, exist_ok=True)

    def _log_execution(self, log_entry: dict):
        """Appends a new execution record to the logs/query_logs.json file."""
        logs = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        logs = json.loads(content)
                        if not isinstance(logs, list):
                            logs = []
            except Exception as e:
                print(f"Warning: Failed to read existing log file: {e}")
                logs = []
        
        logs.append(log_entry)
        
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to write to log file: {e}")

    def run(self, question: str) -> dict:
        """
        Executes the sequential pipeline for a natural language question.
        
        Flow:
        1. Decompose query (LLM Call 1)
        2. Generate SQL (LLM Call 2)
        3. Validate SQL (Rule-Based blocking of DML)
        4. Execute query (PostgreSQL execution)
        5. Auto-Correction (LLM Call 3) on database exception (strictly 1 retry limit)
        6. Log and Return Structured Dictionary
        """
        timestamp = datetime.now().isoformat()
        
        # Step 1: Decomposition
        decomposed_json = self.generator.decompose_query(question)
        
        # Step 2: Generation
        generated_sql = self.generator.generate_sql(decomposed_json)
        
        is_retry_needed = False
        fixed_sql = None
        columns = None
        result = []
        status = "failed"
        error_msg = None
        final_sql = generated_sql
        
        # Step 3: Security Validation
        try:
            SQLValidator.validate(generated_sql)
            
            # Step 4: Execution
            columns, result, error_msg = self.db.execute_query(generated_sql)
            
            if error_msg:
                # Step 5: Self-Correction (strictly ONE retry)
                is_retry_needed = True
                print(f"  [DB Exception Detected]: {error_msg}. Triggering 1-step self-correction...")
                
                fixed_sql = self.generator.fix_sql(question, generated_sql, error_msg)
                final_sql = fixed_sql
                
                # Validate the fixed SQL too before execution!
                SQLValidator.validate(fixed_sql)
                
                columns, result, fix_error_msg = self.db.execute_query(fixed_sql)
                if fix_error_msg:
                    error_msg = f"Fix Attempt Failed: {fix_error_msg}"
                else:
                    error_msg = None
                    status = "success"
            else:
                status = "success"
                
        except SQLValidationError as ve:
            error_msg = f"Security Validation Blocked Query: {ve}"
            print(f"  [Security Alert]: {error_msg}")
        except Exception as e:
            error_msg = f"Pipeline Processing Error: {e}"
            print(f"  [Pipeline Failure]: {error_msg}")
            
        # Standardize results into structured row lists (list of dicts) for Streamlit integration
        rows_returned = []
        if status == "success" and columns is not None:
            # Map column headers to result tuples for standard json/streamlit consumption
            for row in result:
                rows_returned.append(dict(zip(columns, row)))
        
        # Log entry compilation
        log_entry = {
            "timestamp": timestamp,
            "question": question,
            "decomposed_json": decomposed_json,
            "generated_sql": generated_sql,
            "is_retry_needed": is_retry_needed,
            "fixed_sql": fixed_sql,
            "final_sql": final_sql,
            "status": status,
            "rows_returned_count": len(rows_returned),
            "error_message": error_msg
        }
        self._log_execution(log_entry)
        
        # Final Pipeline Output Dictionary
        return {
            "question": question,
            "sql": final_sql,
            "result": rows_returned,
            "columns": columns if columns else [],
            "status": status,
            "retry_needed": is_retry_needed,
            "fixed_sql": fixed_sql,
            "error": error_msg
        }
