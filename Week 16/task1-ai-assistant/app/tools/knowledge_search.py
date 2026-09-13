"""
Knowledge Search Tool.

Wraps the RAG retriever as a callable tool so the agentic loop can
search the knowledge base alongside web search. This enables the
cross-source verification pattern: the agent queries both the
knowledge base and the web, then compares findings.
"""

import logging
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)


def create_knowledge_search_tool(retriever) -> dict:
    """
    Create a knowledge search tool bound to a RAG retriever instance.

    Args:
        retriever: A RAGRetriever instance with a build_context() method.

    Returns:
        A tool definition dict compatible with the ToolRegistry.
    """

    def search_knowledge(query: str, top_k: str = "5") -> str:
        """
        Search the knowledge base for documents relevant to the query.

        Args:
            query: The search query.
            top_k: Number of results to return (as string for tool calling).

        Returns:
            Formatted context from the knowledge base.
        """
        try:
            k = int(top_k)
        except (ValueError, TypeError):
            k = 5

        try:
            context = retriever.build_context(query, top_k=max(1, min(k, 5)))
            if not isinstance(context, str) or not context.strip() or "No relevant documents found" in context:
                return (
                    "Error: No relevant documents found in the knowledge base "
                    "for this query. Consider searching the web instead."
                )
            return f"Knowledge base results for '{query}':\n\n{context}"
        except Exception as e:
            logger.error(f"Knowledge search error: {e}")
            return f"Error: Knowledge base search failed: {e}"

    return {
        "name": "search_knowledge",
        "description": (
            "Search the internal knowledge base for documents relevant to a query. "
            "Use this to find information from ingested documents. If results are "
            "insufficient, also try web_search for external verification."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant documents",
                },
                "top_k": {
                    "type": "string",
                    "description": "Number of results to return (default: 5)",
                },
            },
            "required": ["query"],
        },
        "executor": search_knowledge,
    }
