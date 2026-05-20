import re

class SQLValidationError(Exception):
    """Custom exception raised when SQL security rules are violated."""
    pass

class SQLValidator:
    """Performs rule-based security scanning to verify query safety."""
    
    @staticmethod
    def validate(sql_query: str) -> bool:
        """
        Scans a SQL string to enforce read-only execution constraints.
        
        Rules:
        1. Query must contain and start with 'SELECT' (ignoring whitespace).
        2. Query must NOT contain DML/DDL commands: DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE.
        
        Args:
            sql_query (str): The compiled SQL statement to validate.
            
        Returns:
            bool: True if safe.
            
        Raises:
            SQLValidationError: If the statement violates safety policies.
        """
        if not sql_query:
            raise SQLValidationError("SQL query is empty or null.")

        # Clean query: strip whitespace and convert to uppercase for standard checks
        cleaned = sql_query.strip().upper()
        
        # Rule 1: Must start with SELECT (ignoring comments)
        # Strip block and inline comments first
        cleaned_no_comments = re.sub(r'(--.*?\n)|(/\*.*?\*/)', '', sql_query, flags=re.DOTALL).strip().upper()
        
        if not cleaned_no_comments.startswith("SELECT") and not cleaned_no_comments.startswith("WITH"):
            raise SQLValidationError("Security violation: Statement must be a read-only SELECT or WITH statement.")

        # Rule 2: Block DML and DDL commands
        # Use regex word boundaries (\b) to prevent false-positives on fields like "updated_at"
        blocked_keywords = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
        pattern = re.compile(r'\b(' + '|'.join(blocked_keywords) + r')\b', re.IGNORECASE)
        
        match = pattern.search(sql_query)
        if match:
            violated_keyword = match.group(0).upper()
            raise SQLValidationError(f"Security violation: Blocked command keyword '{violated_keyword}' detected.")

        return True
