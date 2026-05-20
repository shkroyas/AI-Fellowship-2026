from tools.db_tools import execute_sql

class ExecutorAgent:
    """Executes the verified read-only SQL statement against the PostgreSQL database container."""
    
    def execute(self, sql_query: str) -> tuple:
        """
        Runs query and captures output records.
        
        Args:
            sql_query (str): Validated SQL query string.
            
        Returns:
            tuple: (columns_list, result_rows_as_dicts, error_message_if_any)
        """
        # Outsource execution to optimized DB operational tools
        return execute_sql(sql_query)
