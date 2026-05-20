from sqlalchemy import text
from db import engine

def execute_sql(sql_query: str) -> tuple:
    """
    Executes a SQL select statement against the configured SQLAlchemy database engine.
    
    Returns:
        tuple: (columns, results_list, error_message)
        - If success: (list of string columns, list of dict row records, None)
        - If failure: (None, None, detailed exception message string)
    """
    try:
        with engine.connect() as conn:
            # Wrap standard raw query string in SQLAlchemy text compiler
            result = conn.execute(text(sql_query))
            
            # Extract header columns
            columns = list(result.keys()) if result.returns_rows else []
            
            # Parse row records as dictionary mappings
            rows_dict = []
            if result.returns_rows:
                rows = result.fetchall()
                for row in rows:
                    rows_dict.append(dict(zip(columns, row)))
            
            return columns, rows_dict, None
            
    except Exception as e:
        error_msg = str(e)
        return None, None, error_msg
