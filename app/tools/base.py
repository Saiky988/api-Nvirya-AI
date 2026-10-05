from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
import aiosqlite

@dataclass
class ToolContext:
    user_id: str
    task_id: str
    db: Optional[aiosqlite.Connection] = None

class BaseTool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]

    def get_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @abstractmethod
    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        """Executes the tool and returns the result string."""
        pass
