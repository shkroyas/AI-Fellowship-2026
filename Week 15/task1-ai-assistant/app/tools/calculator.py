"""
Calculator Tool.

Provides mathematical computation capabilities to the AI assistant.
Supports basic arithmetic, scientific functions, and unit conversions.
"""

import math
import logging

logger = logging.getLogger(__name__)


def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 3 * 4")

    Returns:
        String representation of the result.
    """
    # Safe math functions allowed in evaluation
    safe_globals = {
        "__builtins__": {},
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "int": int,
        "float": float,
        # Math module functions
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "pi": math.pi,
        "e": math.e,
        "ceil": math.ceil,
        "floor": math.floor,
        "factorial": math.factorial,
    }

    try:
        # Clean the expression
        expression = expression.strip()
        result = eval(expression, safe_globals)
        return f"Result: {result}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except (SyntaxError, NameError, TypeError) as e:
        return f"Error: Invalid expression - {e}"
    except Exception as e:
        return f"Error: {e}"


# Tool definition for the registry
calculator_tool = {
    "name": "calculator",
    "description": (
        "Evaluate mathematical expressions. Supports basic arithmetic "
        "(+, -, *, /, **, %), scientific functions (sqrt, sin, cos, tan, "
        "log, exp), and constants (pi, e). Use this for any numerical computation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression to evaluate, e.g. '2 + 3 * 4' or 'sqrt(144)'",
            }
        },
        "required": ["expression"],
    },
    "executor": calculate,
}
