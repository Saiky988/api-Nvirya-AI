from typing import Any, Optional
import aiosqlite
from app.tools.base import ToolContext

MAX_TOOL_RESULT_CHARS = 10000

class AgentContext:
    def __init__(
        self,
        task_id: str,
        user_id: str,
        messages: list[dict[str, Any]],
        db: Optional[aiosqlite.Connection] = None,
    ):
        self.task_id = task_id
        self.user_id = user_id
        self.messages: list[dict[str, Any]] = list(messages)
        self.db = db

        # Tracking state
        self.sources: list[dict[str, str]] = []
        self.artifacts_created: list[str] = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tool_calls = 0

    @property
    def tool_context(self) -> ToolContext:
        return ToolContext(
            user_id=self.user_id,
            task_id=self.task_id,
            db=self.db,
        )

    def append_message(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    def append_tool_result(self, tool_call_id: str, tool_name: str, result_content: str) -> None:
        clean_content = result_content
        if len(clean_content) > MAX_TOOL_RESULT_CHARS:
            clean_content = clean_content[:MAX_TOOL_RESULT_CHARS] + "\n\n[tool result truncated]"

        self.messages.append({
            "role": "tool",
            "name": tool_name,
            "tool_call_id": tool_call_id,
            "content": clean_content,
        })

    def record_usage(self, usage: dict[str, Any]) -> None:
        if usage:
            self.total_prompt_tokens += usage.get("prompt_tokens", 0)
            self.total_completion_tokens += usage.get("completion_tokens", 0)
