import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.api.dependencies import enforce_generation_quotas, get_request_id
from app.auth.dependencies import AuthContext, get_current_auth
from app.core.config import settings
from app.core.errors import InvalidRequestError
from app.db.database import get_db
from app.schemas.chat import UsageInfo
from app.schemas.tasks import (
    TaskCancelResponse,
    TaskCreateRequest,
    TaskResponse,
)
from app.tasks.service import TaskService

router = APIRouter()

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    payload: TaskCreateRequest,
    auth: AuthContext = Depends(enforce_generation_quotas),
    db: aiosqlite.Connection = Depends(get_db),
    req_id: str = Depends(get_request_id),
):
    """Creates and starts an asynchronous agent task."""
    messages_dicts = [m.model_dump(exclude_none=True) for m in payload.messages]
    task = await TaskService.create_task(
        db=db,
        user_id=auth.user.id,
        model_alias=payload.model,
        messages=messages_dicts,
    )

    return TaskResponse(
        id=task.id,
        object="task",
        model=task.model_alias,
        selected_model=task.selected_model,
        status=task.status,
        current_step=task.current_step,
        created_at=task.created_at,
        started_at=task.started_at,
    )

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Retrieves current state and results of an agent task."""
    task = await TaskService.get_task(db=db, task_id=task_id, user_id=auth.user.id)
    if not task:
        raise InvalidRequestError("Task not found or access denied.")

    return TaskResponse(
        id=task.id,
        object="task",
        model=task.model_alias,
        selected_model=task.selected_model,
        status=task.status,
        current_step=task.current_step,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error=task.error,
        result=task.result,
        usage=UsageInfo(
            prompt_tokens=task.prompt_tokens,
            completion_tokens=task.completion_tokens,
            total_tokens=task.total_tokens,
        ),
    )

@router.get("/tasks/{task_id}/events")
async def get_task_events(
    task_id: str,
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Streams live execution events for an agent task using SSE."""
    # Verify task ownership first
    task = await TaskService.get_task(db=db, task_id=task_id, user_id=auth.user.id)
    if not task:
        raise InvalidRequestError("Task not found or access denied.")

    db_path = str(settings.sqlite_db_path)
    stream_gen = TaskService.stream_events(
        db_path=db_path,
        task_id=task_id,
        user_id=auth.user.id,
    )

    response = StreamingResponse(stream_gen, media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    return response

@router.post("/tasks/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(
    task_id: str,
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Cancels a currently executing agent task."""
    cancelled = await TaskService.cancel_task(db=db, task_id=task_id, user_id=auth.user.id)
    if not cancelled:
        raise InvalidRequestError("Task not found or cannot be cancelled.")

    return TaskCancelResponse(id=task_id, status="cancelled")
