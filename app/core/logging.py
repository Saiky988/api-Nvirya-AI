import logging
import sys
from typing import Any, Optional

def setup_logger(name: str = "nvirya") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = setup_logger()

def log_event(
    event: str,
    request_id: Optional[str] = None,
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    duration_ms: Optional[float] = None,
    extra: Optional[dict[str, Any]] = None,
    level: int = logging.INFO,
) -> None:
    parts = [f"event={event}"]
    if request_id:
        parts.append(f"req_id={request_id}")
    if task_id:
        parts.append(f"task_id={task_id}")
    if user_id:
        parts.append(f"user_id={user_id}")
    if endpoint:
        parts.append(f"endpoint={endpoint}")
    if model:
        parts.append(f"model={model}")
    if status:
        parts.append(f"status={status}")
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms:.1f}")
    if extra:
        for k, v in extra.items():
            if "key" not in k.lower() and "token" not in k.lower() and "secret" not in k.lower():
                parts.append(f"{k}={v}")
    
    logger.log(level, " ".join(parts))
