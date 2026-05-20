from prompts import SCHEMA_CONTEXT, GENERATOR_SYSTEM_PROMPT, CORRECTION_SYSTEM_PROMPT
from agents.llm import call_llm_with_rotation

class SQLGeneratorAgent:
    """Compiles natural language questions and plans into pure read-only PostgreSQL queries."""
    
    def generate(self, question: str, plan: str) -> str:
        """Sequential Call 2: Creates the primary PostgreSQL SELECT statement."""
        prompt = GENERATOR_SYSTEM_PROMPT.format(
            schema_context=SCHEMA_CONTEXT,
            plan=plan,
            question=question
        )
        
        raw_sql = call_llm_with_rotation(prompt, temperature=0.1)
        return self._clean_sql(raw_sql)

    def self_correct(self, question: str, plan: str, failed_sql: str, error_message: str) -> str:
        """Diagnoses SQL compilation exceptions and returns repaired queries."""
        prompt = CORRECTION_SYSTEM_PROMPT.format(
            schema_context=SCHEMA_CONTEXT,
            question=question,
            plan=plan,
            failed_sql=failed_sql,
            error_message=error_message
        )
        
        fixed_sql = call_llm_with_rotation(prompt, temperature=0.1)
        return self._clean_sql(fixed_sql)

    def _clean_sql(self, sql_string: str) -> str:
        """Trims whitespace and removes Markdown brackets if outputted by the LLM."""
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
