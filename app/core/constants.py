"""Application constants and default identifiers."""

# Model aliases
MODEL_AUTO = "nvirya-auto"
MODEL_CODE = "nvirya-code"
MODEL_ANALYSIS = "nvirya-analysis"
MODEL_VISION = "nvirya-vision"
MODEL_FAST = "nvirya-fast"

PUBLIC_MODELS = [
    MODEL_AUTO,
    MODEL_CODE,
    MODEL_ANALYSIS,
    MODEL_FAST,
    MODEL_VISION,
]

# Task statuses
TASK_CREATED = "created"
TASK_RUNNING = "running"
TASK_COMPLETED = "completed"
TASK_FAILED = "failed"
TASK_CANCELLED = "cancelled"
TASK_EXPIRED = "expired"

# Task event types
EVENT_TASK_CREATED = "task.created"
EVENT_TASK_STARTED = "task.started"
EVENT_MODEL_REQUESTED = "model.requested"
EVENT_TOOL_STARTED = "tool.started"
EVENT_TOOL_COMPLETED = "tool.completed"
EVENT_TOOL_FAILED = "tool.failed"
EVENT_ARTIFACT_CREATED = "artifact.created"
EVENT_TASK_COMPLETED = "task.completed"
EVENT_TASK_FAILED = "task.failed"
EVENT_TASK_CANCELLED = "task.cancelled"

# Tools
TOOL_WEB_SEARCH = "web_search"
TOOL_WEB_FETCH = "web_fetch"
TOOL_CALCULATOR = "calculator"
TOOL_FILE_CREATE = "file_create"
TOOL_FILE_READ = "file_read"

# Error Types (OpenAI-compatible)
ERR_AUTH = "authentication_error"
ERR_RATE_LIMIT = "rate_limit_error"
ERR_QUOTA = "quota_error"
ERR_INVALID_REQUEST = "invalid_request_error"
ERR_PROVIDER = "provider_error"
ERR_TOOL = "tool_error"
ERR_SEARCH = "search_error"
ERR_ARTIFACT = "artifact_error"
ERR_INTERNAL = "internal_error"
ERR_TIMEOUT = "timeout_error"

# Timezone for daily quota reset
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
