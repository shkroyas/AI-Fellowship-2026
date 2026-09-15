"""Calculator tool."""
import math

def calculate(expression: str) -> str:
    safe_globals = {
        "__builtins__": {}, "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "pow": pow, "int": int, "float": float,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
        "pi": math.pi, "e": math.e, "ceil": math.ceil, "floor": math.floor,
    }
    try:
        result = eval(expression.strip(), safe_globals)
        return f"Result: {result}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except (SyntaxError, NameError, TypeError) as e:
        return f"Error: Invalid expression - {e}"
    except Exception as e:
        return f"Error: {e}"


calculator_tool = {
    "name": "calculator",
    "description": "Evaluate mathematical expressions. Supports basic arithmetic (+, -, *, /, **, %), scientific functions (sqrt, sin, cos, tan, log, exp), and constants (pi, e).",
    "parameters": {"type": "object", "properties": {"expression": {"type": "string", "description": "The mathematical expression to evaluate"}}, "required": ["expression"]},
    "executor": calculate,
}
