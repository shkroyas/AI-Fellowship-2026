import os
import psycopg2
from dotenv import load_dotenv

# Load environmental variables (if running locally without docker)
load_dotenv()

class DatabaseConnection:
    """Manages connections and safe read-only queries against the PostgreSQL database."""
    
    def __init__(self):
        # Read from environment variables
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME", "classicmodels")
        self.db_user = os.getenv("DB_USER", "myuser")
        self.db_password = os.getenv("DB_PASSWORD", "mypassword")
        self.database_url = os.getenv("DATABASE_URL")

    def _get_connection(self):
        """Helper to establish and return a new psycopg2 connection."""
        if self.database_url:
            return psycopg2.connect(self.database_url)
        else:
            return psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )

    def execute_query(self, sql_query: str) -> tuple:
        """
        Executes a SQL query against the database.
        
        Returns:
            tuple: (columns_list, rows_list, error_message)
            - If execution is successful: (list of column names, list of row tuples, None)
            - If execution fails: (None, None, detailed error message string)
        """
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(sql_query)
            
            # Fetch columns from cursor description
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch all matching row tuples
            rows = cursor.fetchall() if cursor.description else []
            
            return columns, rows, None
            
        except Exception as e:
            # Capture exact PostgreSQL compilation/database error description
            error_msg = str(e)
            return None, None, error_msg
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
