from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: str
    username: str
    email: Optional[str]
    created_at: str

@dataclass
class ApiKey:
    id: str
    key_hash: str
    key_prefix: str
    user_id: str
    label: Optional[str]
    created_at: str
    revoked_at: Optional[str] = None
    last_used_at: Optional[str] = None

@dataclass
class UsageRecord:
    id: str
    request_id: str
    user_id: str
    api_key_id: str
    model_alias: str
    upstream_model: str
    endpoint: str
    status: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tool_calls: int
    duration_ms: float
    created_at: str

@dataclass
class TaskRecord:
    id: str
    user_id: str
    model_alias: str
    selected_model: str
    status: str
    current_step: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    error: Optional[str]
    result: Optional[str]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

@dataclass
class TaskEventRecord:
    id: str
    task_id: str
    event_type: str
    event_data: str
    created_at: str

@dataclass
class ArtifactRecord:
    id: str
    user_id: str
    task_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    created_at: str
