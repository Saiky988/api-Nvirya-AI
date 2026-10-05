from typing import Any, Optional
from pydantic import BaseModel, Field

class ToolFunction(BaseModel):
    name: str
    arguments: str

class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: ToolFunction

class ToolFunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]

class ToolDefinition(BaseModel):
    type: str = "function"
    function: ToolFunctionDefinition
