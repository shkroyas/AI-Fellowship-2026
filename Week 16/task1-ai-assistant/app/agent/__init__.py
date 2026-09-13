"""
Agentic Loop Module.

Implements the cross-source verification agent that iteratively
searches multiple sources, evaluates evidence sufficiency, and
decides when to provide a final answer.
"""

from .loop import AgenticLoop
from .context_manager import ContextManager

__all__ = ["AgenticLoop", "ContextManager"]
