"""
Web Search Tool.

Provides web search capabilities to the AI assistant.
Uses DuckDuckGo search as a free, no-API-key-required search engine.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: str = "3") -> str:
    """
    Search the web for information.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (as string for tool calling).

    Returns:
        Formatted search results string.
    """
    try:
        max_results_int = int(max_results)
    except (ValueError, TypeError):
        max_results_int = 3

    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results_int):
                results.append(r)

        if not results:
            return f"No results found for: {query}"

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"{i}. **{r.get('title', 'No Title')}**\n"
                f"   URL: {r.get('href', 'N/A')}\n"
                f"   {r.get('body', 'No description')}"
            )

        return f"Search results for '{query}':\n\n" + "\n\n".join(formatted)

    except ImportError:
        logger.warning("duckduckgo-search not installed, using mock results")
        return (
            f"Search results for '{query}':\n\n"
            f"Note: Install 'duckduckgo-search' for real web search.\n"
            f"For now, please provide information directly in your prompt."
        )
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"Search failed: {e}"


def get_current_datetime() -> str:
    """Get the current date and time."""
    from datetime import datetime
    now = datetime.now()
    return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"


# Tool definitions for the registry
web_search_tool = {
    "name": "web_search",
    "description": (
        "Search the web for current information. Use this when the user asks about "
        "recent events, facts you're unsure about, or anything that requires up-to-date information."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string",
            },
            "max_results": {
                "type": "string",
                "description": "Maximum number of results (default: 3)",
            },
        },
        "required": ["query"],
    },
    "executor": web_search,
}

datetime_tool = {
    "name": "get_current_datetime",
    "description": "Get the current date and time. Use when the user asks about today's date or current time.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "executor": get_current_datetime,
}
