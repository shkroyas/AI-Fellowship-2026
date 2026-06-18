from __future__ import annotations

import json

from config import Config
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
        if Config.has_llm_credentials():
            try:
                results_str = json.dumps(results[:50], indent=2, default=str)
                if len(results) > 50:
                    results_str += "\n... (remaining rows truncated for brevity)"

                prompt = SUMMARIZER_SYSTEM_PROMPT.format(
                    question=question,
                    sql=sql,
                    results=results_str,
                )
                return call_llm_with_rotation(prompt, temperature=0.2)
            except Exception:
                pass

        return self._heuristic_summary(question, sql, results)

    def _heuristic_summary(self, question: str, sql: str, results: list) -> str:
        if not results:
            return f"No matching records were found for: {question}"

        first_row = results[0]
        if len(results) == 1 and len(first_row) == 1:
            value = next(iter(first_row.values()))
            return f"The answer is {value}."

        if len(results) == 1 and any(key.lower().startswith(("count", "total", "average", "avg", "sum")) for key in first_row.keys()):
            key = next(iter(first_row.keys()))
            return f"The result for {key.replace('_', ' ')} is {first_row[key]}."

        sample_rows = results[:3]
        sample_text = "; ".join(
            ", ".join(f"{key}: {value}" for key, value in row.items()) for row in sample_rows
        )
        if len(results) == 1:
            return f"I found 1 matching row: {sample_text}."
        return f"I found {len(results)} matching rows. Sample results: {sample_text}."
