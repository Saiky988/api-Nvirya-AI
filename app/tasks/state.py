from app.core.constants import (
    TASK_CREATED,
    TASK_RUNNING,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_CANCELLED,
    TASK_EXPIRED,
)

VALID_STATUSES = {
    TASK_CREATED,
    TASK_RUNNING,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_CANCELLED,
    TASK_EXPIRED,
}

TERMINAL_STATUSES = {
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_CANCELLED,
    TASK_EXPIRED,
}

def is_terminal_status(status: str) -> bool:
    return status in TERMINAL_STATUSES
