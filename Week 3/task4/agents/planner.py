from prompts import SCHEMA_CONTEXT, PLANNER_SYSTEM_PROMPT
from agents.llm import call_llm_with_rotation

class PlannerAgent:
    """Analyzes the user question and the database schema to outline a step-by-step query strategy."""
    
    def plan(self, user_query: str) -> str:
        """
        Generates a semantic query plan.
        
        Args:
            user_query (str): Natural language user question.
            
        Returns:
            str: Strategic execution plan.
        """
        # Formulate planning context prompt
        prompt = PLANNER_SYSTEM_PROMPT.format(
            schema_context=SCHEMA_CONTEXT,
            question=user_query
        )
        
        # Execute prompt via Gemini Key Rotator
        plan_output = call_llm_with_rotation(prompt, temperature=0.1)
        return plan_output
