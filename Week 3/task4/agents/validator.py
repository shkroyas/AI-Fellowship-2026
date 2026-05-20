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
        if not sql_query:
            return False, "SQL query is empty or null."

        # Clean query comments and trailing lines to isolate SQL tokens
        cleaned_no_comments = re.sub(r'(--.*?\n)|(/\*.*?\*/)', '', sql_query, flags=re.DOTALL).strip().upper()
        
        # Rule 1: Query must start with read-only operations SELECT or WITH
        if not cleaned_no_comments.startswith("SELECT") and not cleaned_no_comments.startswith("WITH"):
            return False, "Security Violation: Statement must be a read-only SELECT or WITH statement."

        # Rule 2: Block DML and DDL commands using regex word boundaries (\b)
        blocked_keywords = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
        pattern = re.compile(r'\b(' + '|'.join(blocked_keywords) + r')\b', re.IGNORECASE)
        
        match = pattern.search(sql_query)
        if match:
            violated_keyword = match.group(0).upper()
            return False, f"Security Violation: Blocked modification command '{violated_keyword}' detected."

        return True, None
