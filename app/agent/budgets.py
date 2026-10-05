import time
from app.core.config import settings
from app.core.constants import TOOL_WEB_SEARCH, TOOL_WEB_FETCH, TOOL_FILE_CREATE

class ExecutionBudget:
    def __init__(
        self,
        max_steps: int = settings.MAX_AGENT_STEPS,
        max_tool_calls: int = settings.MAX_TOOL_CALLS_PER_TASK,
        max_search: int = settings.MAX_SEARCH_CALLS,
        max_fetch: int = settings.MAX_FETCH_CALLS,
        max_artifacts: int = settings.MAX_ARTIFACTS,
        max_seconds: float = float(settings.MAX_TASK_SECONDS),
    ):
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.max_search = max_search
        self.max_fetch = max_fetch
        self.max_artifacts = max_artifacts
        self.max_seconds = max_seconds

        self.steps_taken = 0
        self.tool_calls_count = 0
        self.search_count = 0
        self.fetch_count = 0
        self.artifacts_count = 0
        self.start_time = time.time()

    def check_time(self) -> None:
        if time.time() - self.start_time > self.max_seconds:
            raise TimeoutError(f"Task exceeded maximum execution time of {self.max_seconds} seconds.")

    def can_take_step(self) -> bool:
        self.check_time()
        return self.steps_taken < self.max_steps

    def record_step(self) -> None:
        self.steps_taken += 1

    def can_call_tool(self, tool_name: str) -> tuple[bool, str]:
        self.check_time()
        if self.tool_calls_count >= self.max_tool_calls:
            return False, f"Maximum tool calls budget ({self.max_tool_calls}) reached."

        if tool_name == TOOL_WEB_SEARCH and self.search_count >= self.max_search:
            return False, f"Maximum web search budget ({self.max_search}) reached."

        if tool_name == TOOL_WEB_FETCH and self.fetch_count >= self.max_fetch:
            return False, f"Maximum web fetch budget ({self.max_fetch}) reached."

        if tool_name == TOOL_FILE_CREATE and self.artifacts_count >= self.max_artifacts:
            return False, f"Maximum file artifacts budget ({self.max_artifacts}) reached."

        return True, ""

    def record_tool_call(self, tool_name: str) -> None:
        self.tool_calls_count += 1
        if tool_name == TOOL_WEB_SEARCH:
            self.search_count += 1
        elif tool_name == TOOL_WEB_FETCH:
            self.fetch_count += 1
        elif tool_name == TOOL_FILE_CREATE:
            self.artifacts_count += 1
