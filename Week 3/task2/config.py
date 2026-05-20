import os
from dotenv import load_dotenv

# Resolve path to the local .env file
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
load_dotenv(dotenv_path=env_path)

# Database Configurations
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "classicmodels")
DB_USER = os.getenv("DB_USER", "myuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")

# Gemini API Key
GEMINI_API_KEY = os.getenv("API_KEY") or os.getenv("GEMINI_API_KEY")

def validate_config():
    """Validates that key configurations are present."""
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY! Please configure 'API_KEY' in your .env file.")
    return True
