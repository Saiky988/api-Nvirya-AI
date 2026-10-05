from typing import Any, Optional, Union
from pydantic import BaseModel, Field
from app.schemas.tools import ToolCall, ToolDefinition

class ChatMessage(BaseModel):
    role: str
    content: Optional[Union[str, list[dict[str, Any]]]] = None
    name: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stop: Optional[Union[str, list[str]]] = None
    stream: Optional[bool] = False
    stream_options: Optional[dict[str, Any]] = None
    tools: Optional[list[Union[ToolDefinition, dict[str, Any]]]] = None
    tool_choice: Optional[Union[str, dict[str, Any]]] = None
    response_format: Optional[dict[str, Any]] = None
    user: Optional[str] = None

class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatCompletionChoiceMessage(BaseModel):
    role: str = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None

class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatCompletionChoiceMessage
    finish_reason: Optional[str] = "stop"

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageInfo

class ChatCompletionChunkDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None

class ChatCompletionChunkChoice(BaseModel):
    index: int = 0
    delta: ChatCompletionChunkDelta
    finish_reason: Optional[str] = None

class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChatCompletionChunkChoice]
    usage: Optional[UsageInfo] = None
