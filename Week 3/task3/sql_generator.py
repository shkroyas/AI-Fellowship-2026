import os
import json
import time
import typing_extensions as typing
import google.generativeai as genai
from prompts.templates import (
    SCHEMA_CONTEXT,
    DECOMPOSITION_PROMPT_TEMPLATE,
    GENERATION_PROMPT_TEMPLATE,
    CORRECTION_PROMPT_TEMPLATE
)

class QueryDecomposition(typing.TypedDict):
    """Structured Pydantic-style TypedDict mapping for Gemini's JSON Output Schema."""
    Intent: str
    Tables: typing.List[str]
    Columns: typing.List[str]
    Filters: str
    Joins: str

class KeyRotator:
    """Manages dynamic rotation and auto-recovery for multiple Google Gemini API Keys."""
    
    def __init__(self):
        # Load from comma-separated list
        keys_str = os.getenv("GEMINI_API_KEYS", "")
        if keys_str:
            self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            # Fallback to single key definitions
            single_key = os.getenv("GEMINI_API_KEY", os.getenv("API_KEY", ""))
            self.keys = [single_key] if single_key else []
            
        self.current_index = 0
        
    def get_keys_count(self) -> int:
        return len(self.keys)
        
    def get_current_key(self) -> str:
        if not self.keys:
            raise ValueError(
                "No Gemini API Keys found! Please set GEMINI_API_KEYS or GEMINI_API_KEY "
                "in your .env file inside Week 3/task3."
            )
        return self.keys[self.current_index]
        
    def rotate(self) -> str:
        """Cycles to the next API key in the list."""
        if not self.keys:
            raise ValueError("No Gemini API Keys found to rotate!")
        self.current_index = (self.current_index + 1) % len(self.keys)
        current_key = self.keys[self.current_index]
        print(f"  [Key Rotator]: 🔄 429 Hit. Rotating to API Key at index {self.current_index}...")
        return current_key
        
    def configure_current(self):
        """Registers the active key with the google-generativeai client library."""
        key = self.get_current_key()
        genai.configure(api_key=key)

class SQLGenerator:
    """Handles prompt chaining and executions with Gemini 2.5 Flash using active key rotation."""
    
    def __init__(self):
        self.rotator = KeyRotator()
        self.model_name = "gemini-2.5-flash"

    def _execute_with_rotation(self, run_func, *args, **kwargs):
        """Helper to run a generative task with automatic key rotation on 429 quota exceptions."""
        max_attempts = max(self.rotator.get_keys_count() * 2, 5)
        base_delay = 5
        
        for attempt in range(max_attempts):
            try:
                # Ensure the generativeai package is configured with the current key
                self.rotator.configure_current()
                return run_func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)
                # Check for 429 (Resource Exhausted / Rate limit)
                if "429" in error_str or "quota" in error_str.lower() or "exhausted" in error_str.lower():
                    # Attempt key rotation
                    if self.rotator.get_keys_count() > 1:
                        self.rotator.rotate()
                    else:
                        # Fallback sleep if only a single key is configured
                        delay = base_delay * (attempt + 1)
                        print(f"  [Rate Limit]: Single key setup. Sleeping for {delay}s...")
                        time.sleep(delay)
                else:
                    # Let other functional issues cascade
                    raise e
                    
        raise RuntimeError("SQLGenerator: Failed to call LLM. All rotated keys exhausted their rate limits.")

    def decompose_query(self, question: str) -> dict:
        """Sequential Call 1: Decomposes question into structured JSON parameters."""
        prompt = DECOMPOSITION_PROMPT_TEMPLATE.format(
            schema_context=SCHEMA_CONTEXT,
            question=question
        )
        
        def _run():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=QueryDecomposition,
                    temperature=0.1
                )
            )
            return json.loads(response.text)

        try:
            return self._execute_with_rotation(_run)
        except Exception as e:
            print(f"Gemini Decomposition Failed: {e}")
            return {
                "Intent": "Error during decomposition",
                "Tables": [],
                "Columns": [],
                "Filters": "None",
                "Joins": "None"
            }

    def generate_sql(self, decomposed_json: dict) -> str:
        """Sequential Call 2: Compiles decomposed parameters and schema into a SELECT SQL query."""
        prompt = GENERATION_PROMPT_TEMPLATE.format(
            schema_context=SCHEMA_CONTEXT,
            decomposed_json=json.dumps(decomposed_json, indent=2)
        )
        
        def _run():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1
                )
            )
            return response.text.strip()

        try:
            sql = self._execute_with_rotation(_run)
            return self._clean_sql(sql)
        except Exception as e:
            print(f"Gemini SQL Generation Failed: {e}")
            return ""

    def fix_sql(self, question: str, failed_sql: str, error_message: str) -> str:
        """Sequential Call 3: Automatically diagnoses and fixes a failed SQL compilation error."""
        prompt = CORRECTION_PROMPT_TEMPLATE.format(
            schema_context=SCHEMA_CONTEXT,
            question=question,
            failed_sql=failed_sql,
            error_message=error_message
        )
        
        def _run():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1
                )
            )
            return response.text.strip()

        try:
            fixed_sql = self._execute_with_rotation(_run)
            return self._clean_sql(fixed_sql)
        except Exception as e:
            print(f"Gemini SQL Self-Correction Failed: {e}")
            return failed_sql

    def _clean_sql(self, sql_string: str) -> str:
        """Strips out markdown syntax tags and trims excess whitespace."""
        if not sql_string:
            return ""
        
        cleaned = sql_string.strip()
        
        if cleaned.startswith("```sql"):
            cleaned = cleaned[6:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
            
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        return cleaned.strip().rstrip(";") + ";"
