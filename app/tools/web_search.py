import json
from typing import Any
from app.search.service import search_service
from app.tools.base import BaseTool, ToolContext

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web when current, recent, or externally verifiable information is needed."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string.",
            }
        },
        "required": ["query"],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        query = arguments.get("query", "").strip()
        if not query:
            return "Error: 'query' parameter is required."

        try:
            results = await search_service.search(query=query, limit=5)
            items = results.get("results", [])
            if not items:
                return f"No search results found for query: '{query}'."

            formatted = []
            for i, r in enumerate(items, 1):
                formatted.append(
                    f"[{i}] {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('snippet')}\n"
                )
            return "\n".join(formatted)
        except Exception as e:
            return f"Error executing search: {str(e)}"
