from config import Config
from agents.llm import call_llm_with_rotation
from prompts import PLANNER_SYSTEM_PROMPT, SCHEMA_CONTEXT

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
        if Config.has_llm_credentials():
            try:
                prompt = PLANNER_SYSTEM_PROMPT.format(
                    schema_context=SCHEMA_CONTEXT,
                    question=user_query,
                )
                return call_llm_with_rotation(prompt, temperature=0.1)
            except Exception:
                pass

        return self._heuristic_plan(user_query)

    def _heuristic_plan(self, user_query: str) -> str:
        question = user_query.lower()
        plan_lines = []

        if any(token in question for token in ["payment", "revenue", "amount", "paid"]):
            plan_lines.append("- Use payments as the primary fact table and join customers when customer context is needed.")
        elif any(token in question for token in ["order", "shipped", "status", "delivery"]):
            plan_lines.append("- Use orders as the primary fact table and join customers for customer names or geography.")
        elif any(token in question for token in ["product", "stock", "price", "msrp", "buy price", "product line"]):
            plan_lines.append("- Use products as the primary table and join productlines when grouping by product line.")
        elif any(token in question for token in ["employee", "sales rep", "office", "territory"]):
            plan_lines.append("- Use employees as the primary table and join offices for office and region data.")
        else:
            plan_lines.append("- Start from the most relevant base table, then join related tables only if the question requires extra context.")

        if any(token in question for token in ["how many", "count", "number of"]):
            plan_lines.append("- Aggregate with COUNT(*) and apply any requested filters before grouping.")
        if any(token in question for token in ["average", "avg", "mean"]):
            plan_lines.append("- Aggregate numeric fields with AVG and group by the requested dimension.")
        if any(token in question for token in ["top", "highest", "largest", "most"]):
            plan_lines.append("- Order by the relevant metric descending and limit the result set.")

        plan_lines.append("- Keep the query read-only and select only the columns needed to answer the question.")
        return "\n".join(plan_lines)
