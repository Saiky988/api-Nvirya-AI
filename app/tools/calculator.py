import ast
import math
import operator
from typing import Any
from app.tools.base import BaseTool, ToolContext

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "pow": pow,
    "sqrt": math.sqrt,
    "ceil": math.ceil,
    "floor": math.floor,
}

class SafeEvaluator:
    @classmethod
    def evaluate(cls, expression: str) -> float | int:
        clean_expr = expression.strip()
        if not clean_expr:
            raise ValueError("Empty expression.")
        if len(clean_expr) > 200:
            raise ValueError("Expression is too long.")

        node = ast.parse(clean_expr, mode="eval")
        return cls._eval_node(node.body)

    @classmethod
    def _eval_node(cls, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            
            # Guard against massive exponents
            if op_type is ast.Pow:
                if right > 1000 or (isinstance(left, (int, float)) and abs(left) > 1000 and right > 10):
                    raise ValueError("Power exponent is too large.")
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division by zero.")

            return SAFE_OPERATORS[op_type](left, right)

        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            return SAFE_OPERATORS[op_type](operand)

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only standard math function calls are allowed.")
            func_name = node.func.id
            if func_name not in SAFE_FUNCTIONS:
                raise ValueError(f"Function '{func_name}' is not permitted.")
            args = [cls._eval_node(arg) for arg in node.args]
            return SAFE_FUNCTIONS[func_name](*args)

        else:
            raise ValueError(f"Unsupported expression construct: {type(node).__name__}")


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Safely evaluate mathematical expressions. Use this for arithmetic and basic mathematical calculations."
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression to evaluate (e.g. '42 + 58', '(12.5 * 4) / 2', 'sqrt(144)').",
            }
        },
        "required": ["expression"],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        expression = arguments.get("expression", "")
        if not expression:
            return "Error: 'expression' parameter is required."
        try:
            result = SafeEvaluator.evaluate(str(expression))
            # Format nicely
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return str(result)
        except ZeroDivisionError:
            return "Error: Division by zero."
        except Exception as e:
            return f"Error evaluating expression: {str(e)}"
