import os
import json
from openai import OpenAI
from prompts.templates import (
    SCHEMA_CONTEXT,
    DECOMPOSITION_PROMPT_TEMPLATE,
    GENERATION_PROMPT_TEMPLATE,
    CORRECTION_PROMPT_TEMPLATE
)

class SQLGenerator:
    """Handles the OpenAI LLM interaction for Decomposition, Generation, and Error Fixing."""
    
    def __init__(self):
        # Read API key from environment, fallback to None (it will raise standard error on call if missing)
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = "gpt-4o-mini"
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def _get_client(self):
        if not self.client:
            # Refresh client dynamically if key was loaded after init
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("Missing OPENAI_API_KEY! Please configure it in your environment or .env file.")
            self.client = OpenAI(api_key=api_key)
        return self.client

    def decompose_query(self, question: str) -> dict:
        """Sequential Call 1: Decomposes natural language query into structural JSON entities."""
        client = self._get_client()
        prompt = DECOMPOSITION_PROMPT_TEMPLATE.format(
            schema_context=SCHEMA_CONTEXT,
            question=question
        )
        
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}  # Enforce JSON mode
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            # Return empty skeleton structure if failed
            print(f"LLM Decomposition Failed: {e}")
            return {
                "Intent": "Error during decomposition",
                "Tables": [],
                "Columns": [],
                "Filters": "None",
                "Joins": "None"
            }

    def generate_sql(self, decomposed_json: dict) -> str:
        """Sequential Call 2: Converts decomposed plan into raw PostgreSQL query."""
        client = self._get_client()
        prompt = GENERATION_PROMPT_TEMPLATE.format(
            schema_context=SCHEMA_CONTEXT,
            decomposed_json=json.dumps(decomposed_json, indent=2)
        )
        
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            sql = response.choices[0].message.content.strip()
            return self._clean_sql(sql)
        except Exception as e:
            print(f"LLM SQL Generation Failed: {e}")
            return ""

    def fix_sql(self, question: str, failed_sql: str, error_message: str) -> str:
        """Sequential Call 3: Fixes a query that caused a database execution exception (1-step self-correction)."""
        client = self._get_client()
        prompt = CORRECTION_PROMPT_TEMPLATE.format(
            schema_context=SCHEMA_CONTEXT,
            question=question,
            failed_sql=failed_sql,
            error_message=error_message
        )
        
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            fixed_sql = response.choices[0].message.content.strip()
            return self._clean_sql(fixed_sql)
        except Exception as e:
            print(f"LLM SQL Self-Correction Failed: {e}")
            return failed_sql

    def _clean_sql(self, sql_string: str) -> str:
        """Strips out markdown wraps (like ```sql ... ```) and excess whitespace."""
        if not sql_string:
            return ""
        
        # Strip leading/trailing whitespaces and quotes
        cleaned = sql_string.strip()
        
        # Remove Markdown syntax wraps if present
        if cleaned.startswith("```sql"):
            cleaned = cleaned[6:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
            
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        return cleaned.strip().rstrip(";") + ";"
