from typing import Any, Optional
from pydantic import BaseModel, Field
from app.schemas.chat import ChatMessage, UsageInfo

class TaskCreateRequest(BaseModel):
    model: str = "nvirya-auto"
    messages: list[ChatMessage]

class TaskResponse(BaseModel):
    id: str
    object: str = "task"
    model: str
    selected_model: Optional[str] = None
    status: str
    current_step: int = 0
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[str] = None
    usage: Optional[UsageInfo] = None

class TaskCancelResponse(BaseModel):
    id: str
    status: str = "cancelled"

class TaskEventItem(BaseModel):
    id: str
    task_id: str
    event_type: str
    event_data: dict[str, Any]
    created_at: str
