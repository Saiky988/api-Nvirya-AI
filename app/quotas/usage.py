import uuid
from typing import Optional
import aiosqlite
from app.core.logging import log_event
from app.db.repositories import UsageRepository

class UsageService:
    @staticmethod
    async def record(
        db: aiosqlite.Connection,
        request_id: str,
        user_id: str,
        api_key_id: str,
        model_alias: str,
        upstream_model: str,
        endpoint: str,
        status: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        tool_calls: int = 0,
        duration_ms: float = 0.0,
    ) -> None:
        record_id = f"usg_{uuid.uuid4().hex[:16]}"
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens

        await UsageRepository.record_usage(
            db=db,
            record_id=record_id,
            request_id=request_id,
            user_id=user_id,
            api_key_id=api_key_id,
            model_alias=model_alias,
            upstream_model=upstream_model,
            endpoint=endpoint,
            status=status,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            tool_calls=tool_calls,
            duration_ms=duration_ms,
        )

        log_event(
            event="request.completed",
            request_id=request_id,
            user_id=user_id,
            endpoint=endpoint,
            model=model_alias,
            status=status,
            duration_ms=duration_ms,
            extra={
                "tokens": total_tokens,
                "tool_calls": tool_calls,
                "upstream": upstream_model,
            },
        )

    @staticmethod
    async def get_summary(db: aiosqlite.Connection, user_id: str) -> dict:
        return await UsageRepository.get_usage_summary(db, user_id)
