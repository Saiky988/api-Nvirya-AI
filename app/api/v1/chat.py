import time
import uuid
from typing import Any
import aiosqlite
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.agent.orchestrator import agent_orchestrator
from app.api.dependencies import enforce_generation_quotas, get_request_id
from app.auth.dependencies import AuthContext
from app.db.database import get_db
from app.quotas.usage import UsageService
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse

router = APIRouter()

@router.post("/chat/completions")
async def create_chat_completion(
    payload: ChatCompletionRequest,
    request: Request,
    auth: AuthContext = Depends(enforce_generation_quotas),
    db: aiosqlite.Connection = Depends(get_db),
    req_id: str = Depends(get_request_id),
):
    """
    OpenAI-compatible chat completions endpoint with integrated server-side agent runtime.
    """
    start_time = time.time()
    task_id = f"task_{uuid.uuid4().hex[:16]}"
    messages_dicts = [m.model_dump(exclude_none=True) for m in payload.messages]

    # Handle streaming
    if payload.stream:
        # Background usage tracking is captured after stream completion or within stream
        stream_gen = agent_orchestrator.stream_execute_task(
            task_id=task_id,
            user_id=auth.user.id,
            model_name=payload.model,
            messages=messages_dicts,
            db=db,
            temperature=payload.temperature,
            top_p=payload.top_p,
            max_tokens=payload.max_tokens,
            tool_choice=payload.tool_choice or "auto",
        )

        response = StreamingResponse(stream_gen, media_type="text/event-stream")
        response.headers["X-Request-ID"] = req_id
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        return response

    # Non-streaming
    result = await agent_orchestrator.execute_task(
        task_id=task_id,
        user_id=auth.user.id,
        model_name=payload.model,
        messages=messages_dicts,
        db=db,
        temperature=payload.temperature,
        top_p=payload.top_p,
        max_tokens=payload.max_tokens,
        tool_choice=payload.tool_choice or "auto",
    )

    duration_ms = (time.time() - start_time) * 1000.0
    tool_calls_count = result.pop("_tool_calls", 0)
    upstream_model = result.pop("_upstream_model", payload.model)

    # Record usage
    usage = result.get("usage", {})
    await UsageService.record(
        db=db,
        request_id=req_id,
        user_id=auth.user.id,
        api_key_id=auth.api_key.id,
        model_alias=payload.model,
        upstream_model=upstream_model,
        endpoint="/v1/chat/completions",
        status="success",
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        tool_calls=tool_calls_count,
        duration_ms=duration_ms,
    )

    return result
