import json
from typing import Any, Optional
from app.tools.base import BaseTool
from app.tools.calculator import CalculatorTool
from app.tools.file_tools import FileCreateTool, FileReadTool
from app.tools.web_fetch import WebFetchTool
from app.tools.web_search import WebSearchTool

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        # Register default tools
        self.register(CalculatorTool())
        self.register(WebSearchTool())
        self.register(WebFetchTool())
        self.register(FileCreateTool())
        self.register(FileReadTool())

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def get_definitions(self, tool_names: Optional[list[str]] = None) -> list[dict[str, Any]]:
        if tool_names:
            return [self._tools[n].get_definition() for n in tool_names if n in self._tools]
        return [tool.get_definition() for tool in self._tools.values()]

    @staticmethod
    def parse_arguments(raw_args: Any) -> tuple[dict[str, Any], Optional[str]]:
        """
        Safely parses JSON tool arguments from model output.
        Returns: (parsed_dict, error_string_if_any)
        """
        if isinstance(raw_args, dict):
            return raw_args, None
        if not raw_args or not isinstance(raw_args, str):
            return {}, "Empty arguments."
        try:
            parsed = json.loads(raw_args)
            if not isinstance(parsed, dict):
                return {}, "Arguments must be a valid JSON object."
            return parsed, None
        except Exception as e:
            return {}, f"Invalid JSON arguments: {str(e)}"

tool_registry = ToolRegistry()
