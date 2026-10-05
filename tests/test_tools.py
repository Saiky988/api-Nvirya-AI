import pytest
from app.tools.base import ToolContext
from app.tools.calculator import CalculatorTool, SafeEvaluator
from app.tools.registry import tool_registry

@pytest.mark.asyncio
async def test_calculator_basic_and_complex_expressions():
    tool = CalculatorTool()
    ctx = ToolContext(user_id="u1", task_id="t1")

    # Simple arithmetic
    res = await tool.execute({"expression": "42 + 58"}, ctx)
    assert res == "100"

    # Precedence & float
    res = await tool.execute({"expression": "(12.5 * 4) / 2"}, ctx)
    assert res == "25"

    # Functions
    res = await tool.execute({"expression": "sqrt(144) + abs(-10)"}, ctx)
    assert res == "22"

    # Division by zero
    res = await tool.execute({"expression": "10 / 0"}, ctx)
    assert "division by zero" in res.lower()

@pytest.mark.asyncio
async def test_calculator_security_blocks_code_injection():
    tool = CalculatorTool()
    ctx = ToolContext(user_id="u1", task_id="t1")

    # Block imports
    res = await tool.execute({"expression": "__import__('os').system('ls')"}, ctx)
    assert "error" in res.lower()

    # Block eval
    res = await tool.execute({"expression": "eval('2+2')"}, ctx)
    assert "error" in res.lower()

    # Block attributes
    res = await tool.execute({"expression": "().__class__.__bases__"}, ctx)
    assert "error" in res.lower()

def test_tool_registry_safe_argument_parsing():
    # Valid JSON
    parsed, err = tool_registry.parse_arguments('{"query": "FastAPI"}')
    assert err is None
    assert parsed == {"query": "FastAPI"}

    # Malformed JSON (must not throw unhandled exception)
    parsed, err = tool_registry.parse_arguments('{"query": "FastAPI"')
    assert err is not None
    assert parsed == {}

    # Non-dict JSON
    parsed, err = tool_registry.parse_arguments('"string"')
    assert err is not None

def test_tool_definitions():
    defs = tool_registry.get_definitions(["calculator", "web_search"])
    assert len(defs) == 2
    names = [d["function"]["name"] for d in defs]
    assert "calculator" in names
    assert "web_search" in names
