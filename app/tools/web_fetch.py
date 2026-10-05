from typing import Any
from app.search.fetcher import web_fetcher
from app.tools.base import BaseTool, ToolContext

class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch and extract readable text from a web URL. Only use after identifying relevant URLs."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The HTTP or HTTPS URL to fetch.",
            }
        },
        "required": ["url"],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        url = arguments.get("url", "").strip()
        if not url:
            return "Error: 'url' parameter is required."

        try:
            data = await web_fetcher.fetch(url)
            title = data.get("title", "Untitled")
            text = data.get("text", "")
            return f"Source: {url}\nTitle: {title}\n\nContent:\n{text}"
        except Exception as e:
            return f"Error fetching URL '{url}': {str(e)}"
