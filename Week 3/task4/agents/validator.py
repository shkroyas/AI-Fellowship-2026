import re

class ValidatorAgent:
    """Security scanner enforcing read-only execution by blocking DML and DDL commands."""
    
    def validate(self, sql_query: str) -> tuple:
        """
        Scans a SQL string to enforce read-only policies.
        
        Args:
            sql_query (str): Generated SQL statement.
            
        Returns:
            tuple: (is_valid: bool, error_message_if_any: str)
        """
        if not sql_query or not sql_query.strip():
            return False, "SQL query is empty or null."

        cleaned_no_comments = re.sub(r'(--.*?$)|(/\*.*?\*/)', '', sql_query, flags=re.MULTILINE | re.DOTALL)
        normalized = re.sub(r'\s+', ' ', cleaned_no_comments).strip()
        upper_query = normalized.upper()

        if upper_query.count(';') > 1:
            return False, "Security Violation: Multiple SQL statements are not allowed."

        statement = normalized.rstrip(';').strip()
        upper_statement = statement.upper()
        
        if not upper_statement.startswith("SELECT") and not upper_statement.startswith("WITH"):
            return False, "Security Violation: Statement must be a read-only SELECT or WITH statement."

        blocked_keywords = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "COMMENT", "GRANT", "REVOKE", "VACUUM", "COPY", "CALL", "EXEC", "DO"]
        pattern = re.compile(r'\b(' + '|'.join(blocked_keywords) + r')\b', re.IGNORECASE)
        
        match = pattern.search(statement)
        if match:
            violated_keyword = match.group(0).upper()
            return False, f"Security Violation: Blocked modification command '{violated_keyword}' detected."

        if re.search(r'\bSELECT\s+INTO\b', upper_statement):
            return False, "Security Violation: SELECT INTO is not allowed because it creates a table."

        if re.search(r'\bFOR\s+UPDATE\b|\bFOR\s+SHARE\b', upper_statement):
            return False, "Security Violation: Row-locking clauses are not allowed in this read-only workflow."

        return True, None
