import json
from prompts import SUMMARIZER_SYSTEM_PROMPT
from agents.llm import call_llm_with_rotation

class SummarizerAgent:
    """Business Intelligence analyst that translates database records into natural human responses."""
    
    def summarize(self, question: str, sql: str, results: list) -> str:
        """
        Synthesizes list of dictionaries into a friendly summary.
        
        Args:
            question (str): User question.
            sql (str): SQL statement that generated the results.
            results (list): List of row dictionaries.
            
        Returns:
            str: Friendly synthesized summary.
        """
        # Convert results to clean JSON string representation
        results_str = json.dumps(results[:50], indent=2, default=str) # Limit to first 50 rows for prompt safety
        if len(results) > 50:
            results_str += "\n... (remaining rows truncated for brevity)"
            
        prompt = SUMMARIZER_SYSTEM_PROMPT.format(
            question=question,
            sql=sql,
            results=results_str
        )
        
        summary = call_llm_with_rotation(prompt, temperature=0.2)
        return summary
