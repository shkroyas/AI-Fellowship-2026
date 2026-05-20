import os
from dotenv import load_dotenv

# Load local environment configurations
load_dotenv()

class Config:
    """Manages system configurations and custom parses list-based API keys."""
    
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "classicmodels")
    DB_USER = os.getenv("DB_USER", "myuser")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")
    DATABASE_URL = os.getenv("DATABASE_URL")

    @classmethod
    def get_gemini_api_keys(cls) -> list:
        """
        Parses list-based and standard bracket formats for API_KEY environment variable.
        E.g. parses: '[key_1, key_2, key_3]' or 'key_1, key_2' or single keys.
        """
        api_key_raw = os.getenv("API_KEY", "").strip()
        if not api_key_raw:
            # Fallback check for standard GEMINI_API_KEYS
            api_key_raw = os.getenv("GEMINI_API_KEYS", "").strip()
            
        if not api_key_raw:
            return []

        # If enclosed in brackets like '[key1, key2]'
        if api_key_raw.startswith("[") and api_key_raw.endswith("]"):
            inner = api_key_raw[1:-1].strip()
            return [k.strip().strip("'").strip('"') for k in inner.split(",") if k.strip()]
            
        # If standard comma separated without brackets
        if "," in api_key_raw:
            return [k.strip().strip("'").strip('"') for k in api_key_raw.split(",") if k.strip()]
            
        # Single key format
        return [api_key_raw.strip().strip("'").strip('"')]
