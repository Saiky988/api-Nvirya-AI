import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Optional
import aiosqlite
from app.agent.orchestrator import agent_orchestrator
from app.artifacts.storage import artifact_storage
from app.core.constants import (
    EVENT_TASK_CREATED,
    EVENT_TASK_STARTED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_FAILED,
    EVENT_TASK_CANCELLED,
    TASK_RUNNING,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_CANCELLED,
)
from app.core.errors import InvalidRequestError
from app.core.logging import logger
from app.db.database import get_db, settings
from app.db.models import TaskRecord
from app.db.repositories import TaskRepository
from app.routing.model_router import model_router
from app.tasks.events import format_sse_event

class TaskService:
    @staticmethod
    async def create_task(
        db: aiosqlite.Connection,
        user_id: str,
        model_alias: str,
        messages: list[dict[str, Any]],
    ) -> TaskRecord:
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        upstream_model, _ = model_router.resolve_model(model_alias, messages)

        task = await TaskRepository.create_task(
            db=db,
            task_id=task_id,
            user_id=user_id,
            model_alias=model_alias,
            selected_model=upstream_model,
            status=TASK_RUNNING,
        )

        # Emit task.created event
        await TaskRepository.add_event(
            db=db,
            event_id=f"evt_{uuid.uuid4().hex[:16]}",
            task_id=task_id,
            event_type=EVENT_TASK_CREATED,
            event_data={"model": model_alias, "upstream": upstream_model},
        )

        # Launch background execution task
        asyncio.create_task(
            TaskService._execute_task_job(
                task_id=task_id,
                user_id=user_id,
                model_alias=model_alias,
                messages=messages,
            )
        )

        return task

    @staticmethod
    async def _execute_task_job(
        task_id: str,
        user_id: str,
        model_alias: str,
        messages: list[dict[str, Any]],
    ) -> None:
        db_path = str(settings.sqlite_db_path)
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Event callback to persist intermediate steps into DB
            async def event_callback(event_type: str, data: dict[str, Any]) -> None:
                try:
                    await TaskRepository.add_event(
                        db=db,
                        event_id=f"evt_{uuid.uuid4().hex[:16]}",
                        task_id=task_id,
                        event_type=event_type,
                        event_data=data,
                    )
                except Exception as e:
                    logger.warning(f"Error persisting task event: {e}")

            await event_callback(EVENT_TASK_STARTED, {"task_id": task_id})

            try:
                # Check if task was cancelled before starting
                task_record = await TaskRepository.get_task(db, task_id)
                if task_record and task_record.status == TASK_CANCELLED:
                    return

                response = await agent_orchestrator.execute_task(
                    task_id=task_id,
                    user_id=user_id,
                    model_name=model_alias,
                    messages=messages,
                    db=db,
                    event_callback=event_callback,
                )

                choices = response.get("choices", [])
                result_text = ""
                if choices:
                    result_text = choices[0].get("message", {}).get("content", "")

                usage = response.get("usage", {})
                p_tokens = usage.get("prompt_tokens", 0)
                c_tokens = usage.get("completion_tokens", 0)
                t_tokens = usage.get("total_tokens", p_tokens + c_tokens)

                # Check cancellation again before marking completed
                curr = await TaskRepository.get_task(db, task_id)
                if curr and curr.status == TASK_CANCELLED:
                    return

                await TaskRepository.update_task(
                    db=db,
                    task_id=task_id,
                    status=TASK_COMPLETED,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    result=result_text,
                    completed=True,
                )

                await event_callback(EVENT_TASK_COMPLETED, {"result_preview": result_text[:100]})

            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                await TaskRepository.update_task(
                    db=db,
                    task_id=task_id,
                    status=TASK_FAILED,
                    error=str(e),
                    completed=True,
                )
                await event_callback(EVENT_TASK_FAILED, {"error": str(e)})

            finally:
                # Cleanup workspace temp files
                artifact_storage.cleanup_workspace(task_id)

    @staticmethod
    async def get_task(
        db: aiosqlite.Connection, task_id: str, user_id: str
    ) -> Optional[TaskRecord]:
        return await TaskRepository.get_task(db, task_id, user_id=user_id)

    @staticmethod
    async def cancel_task(
        db: aiosqlite.Connection, task_id: str, user_id: str
    ) -> bool:
        task = await TaskRepository.get_task(db, task_id, user_id=user_id)
        if not task:
            return False

        if task.status in (TASK_COMPLETED, TASK_FAILED, TASK_CANCELLED):
            return True

        await TaskRepository.update_task(
            db=db,
            task_id=task_id,
            status=TASK_CANCELLED,
            completed=True,
        )
        await TaskRepository.add_event(
            db=db,
            event_id=f"evt_{uuid.uuid4().hex[:16]}",
            task_id=task_id,
            event_type=EVENT_TASK_CANCELLED,
            event_data={"reason": "User cancelled"},
        )
        return True

    @staticmethod
    async def stream_events(
        db_path: str, task_id: str, user_id: str
    ) -> AsyncGenerator[str, None]:
        """Streams events for a task over SSE."""
        last_event_count = 0
        poll_interval = 0.5
        max_idle_polls = 120  # 60 seconds timeout

        idle_count = 0
        while idle_count < max_idle_polls:
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                task = await TaskRepository.get_task(db, task_id, user_id=user_id)
                if not task:
                    yield format_sse_event("error", {"message": "Task not found."})
                    return

                events = await TaskRepository.get_events(db, task_id)
                if len(events) > last_event_count:
                    new_events = events[last_event_count:]
                    last_event_count = len(events)
                    for evt in new_events:
                        yield format_sse_event(
                            event_type=evt.event_type,
                            data=json.loads(evt.event_data),
                            event_id=evt.id,
                        )
                    idle_count = 0
                else:
                    idle_count += 1

                if task.status in (TASK_COMPLETED, TASK_FAILED, TASK_CANCELLED):
                    yield format_sse_event("done", {"status": task.status})
                    return

            await asyncio.sleep(poll_interval)
