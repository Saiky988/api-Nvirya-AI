from datetime import datetime, timezone
import json
from typing import Optional
import aiosqlite
from app.db.models import User, ApiKey, UsageRecord, TaskRecord, TaskEventRecord, ArtifactRecord

class UserRepository:
    @staticmethod
    async def create_user(db: aiosqlite.Connection, user_id: str, username: str, email: Optional[str] = None) -> User:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO users (id, username, email, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, email, now),
        )
        await db.commit()
        return User(id=user_id, username=username, email=email, created_at=now)

    @staticmethod
    async def get_user_by_id(db: aiosqlite.Connection, user_id: str) -> Optional[User]:
        async with db.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return User(id=row[0], username=row[1], email=row[2], created_at=row[3])
            return None


class ApiKeyRepository:
    @staticmethod
    async def create_api_key(
        db: aiosqlite.Connection,
        key_id: str,
        key_hash: str,
        key_prefix: str,
        user_id: str,
        label: Optional[str] = None,
    ) -> ApiKey:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """
            INSERT INTO api_keys (id, key_hash, key_prefix, user_id, label, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (key_id, key_hash, key_prefix, user_id, label, now),
        )
        await db.commit()
        return ApiKey(
            id=key_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            user_id=user_id,
            label=label,
            created_at=now,
        )

    @staticmethod
    async def get_by_hash(db: aiosqlite.Connection, key_hash: str) -> Optional[ApiKey]:
        async with db.execute(
            """
            SELECT id, key_hash, key_prefix, user_id, label, created_at, revoked_at, last_used_at
            FROM api_keys
            WHERE key_hash = ?
            """,
            (key_hash,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return ApiKey(
                    id=row[0],
                    key_hash=row[1],
                    key_prefix=row[2],
                    user_id=row[3],
                    label=row[4],
                    created_at=row[5],
                    revoked_at=row[6],
                    last_used_at=row[7],
                )
            return None

    @staticmethod
    async def list_by_user(db: aiosqlite.Connection, user_id: str) -> list[ApiKey]:
        async with db.execute(
            """
            SELECT id, key_hash, key_prefix, user_id, label, created_at, revoked_at, last_used_at
            FROM api_keys
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                ApiKey(
                    id=r[0],
                    key_hash=r[1],
                    key_prefix=r[2],
                    user_id=r[3],
                    label=r[4],
                    created_at=r[5],
                    revoked_at=r[6],
                    last_used_at=r[7],
                )
                for r in rows
            ]

    @staticmethod
    async def revoke(db: aiosqlite.Connection, key_id: str, user_id: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute(
            "UPDATE api_keys SET revoked_at = ? WHERE id = ? AND user_id = ? AND revoked_at IS NULL",
            (now, key_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0

    @staticmethod
    async def update_last_used(db: aiosqlite.Connection, key_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, key_id))
        await db.commit()


class QuotaRepository:
    @staticmethod
    async def get_used_today(db: aiosqlite.Connection, user_id: str, date_str: str) -> int:
        async with db.execute(
            "SELECT count FROM daily_quotas WHERE user_id = ? AND quota_date = ?",
            (user_id, date_str),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    @staticmethod
    async def try_consume_daily_quota(
        db: aiosqlite.Connection, user_id: str, date_str: str, max_limit: int
    ) -> bool:
        """
        Atomically increments daily quota if under limit.
        Returns True if quota consumed, False if limit exceeded.
        """
        # We perform an atomic upsert check within a transaction
        await db.execute("BEGIN IMMEDIATE")
        try:
            async with db.execute(
                "SELECT count FROM daily_quotas WHERE user_id = ? AND quota_date = ?",
                (user_id, date_str),
            ) as cursor:
                row = await cursor.fetchone()
                current_count = row[0] if row else 0

            if current_count >= max_limit:
                await db.execute("ROLLBACK")
                return False

            new_count = current_count + 1
            await db.execute(
                """
                INSERT INTO daily_quotas (user_id, quota_date, count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, quota_date) DO UPDATE SET count = count + 1
                """,
                (user_id, date_str),
            )
            await db.commit()
            return True
        except Exception:
            await db.execute("ROLLBACK")
            raise


class UsageRepository:
    @staticmethod
    async def record_usage(
        db: aiosqlite.Connection,
        record_id: str,
        request_id: str,
        user_id: str,
        api_key_id: str,
        model_alias: str,
        upstream_model: str,
        endpoint: str,
        status: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        tool_calls: int,
        duration_ms: float,
    ) -> UsageRecord:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """
            INSERT INTO usage_records (
                id, request_id, user_id, api_key_id, model_alias,
                upstream_model, endpoint, status, prompt_tokens,
                completion_tokens, total_tokens, tool_calls, duration_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                request_id,
                user_id,
                api_key_id,
                model_alias,
                upstream_model,
                endpoint,
                status,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                tool_calls,
                duration_ms,
                now,
            ),
        )
        await db.commit()
        return UsageRecord(
            id=record_id,
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
            created_at=now,
        )

    @staticmethod
    async def get_usage_summary(db: aiosqlite.Connection, user_id: str) -> dict:
        async with db.execute(
            """
            SELECT 
                COUNT(*) as total_requests,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(tool_calls) as total_tool_calls
            FROM usage_records
            WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "total_requests": row[0] or 0,
                    "total_prompt_tokens": row[1] or 0,
                    "total_completion_tokens": row[2] or 0,
                    "total_tokens": row[3] or 0,
                    "total_tool_calls": row[4] or 0,
                }
            return {
                "total_requests": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_tool_calls": 0,
            }


class TaskRepository:
    @staticmethod
    async def create_task(
        db: aiosqlite.Connection,
        task_id: str,
        user_id: str,
        model_alias: str,
        selected_model: str,
        status: str = "created",
    ) -> TaskRecord:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """
            INSERT INTO tasks (
                id, user_id, model_alias, selected_model, status,
                current_step, prompt_tokens, completion_tokens, total_tokens,
                created_at, started_at
            ) VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, ?, ?)
            """,
            (task_id, user_id, model_alias, selected_model, status, now, now),
        )
        await db.commit()
        return TaskRecord(
            id=task_id,
            user_id=user_id,
            model_alias=model_alias,
            selected_model=selected_model,
            status=status,
            current_step=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            error=None,
            result=None,
            created_at=now,
            started_at=now,
        )

    @staticmethod
    async def get_task(db: aiosqlite.Connection, task_id: str, user_id: Optional[str] = None) -> Optional[TaskRecord]:
        query = "SELECT id, user_id, model_alias, selected_model, status, current_step, prompt_tokens, completion_tokens, total_tokens, error, result, created_at, started_at, completed_at FROM tasks WHERE id = ?"
        params: list = [task_id]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        async with db.execute(query, tuple(params)) as cursor:
            row = await cursor.fetchone()
            if row:
                return TaskRecord(
                    id=row[0],
                    user_id=row[1],
                    model_alias=row[2],
                    selected_model=row[3],
                    status=row[4],
                    current_step=row[5],
                    prompt_tokens=row[6],
                    completion_tokens=row[7],
                    total_tokens=row[8],
                    error=row[9],
                    result=row[10],
                    created_at=row[11],
                    started_at=row[12],
                    completed_at=row[13],
                )
            return None

    @staticmethod
    async def update_task(
        db: aiosqlite.Connection,
        task_id: str,
        status: Optional[str] = None,
        current_step: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        error: Optional[str] = None,
        result: Optional[str] = None,
        completed: bool = False,
    ) -> None:
        updates = []
        params = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if current_step is not None:
            updates.append("current_step = ?")
            params.append(current_step)
        if prompt_tokens is not None:
            updates.append("prompt_tokens = prompt_tokens + ?")
            params.append(prompt_tokens)
        if completion_tokens is not None:
            updates.append("completion_tokens = completion_tokens + ?")
            params.append(completion_tokens)
        if total_tokens is not None:
            updates.append("total_tokens = total_tokens + ?")
            params.append(total_tokens)
        if error is not None:
            updates.append("error = ?")
            params.append(error)
        if result is not None:
            updates.append("result = ?")
            params.append(result)
        if completed:
            updates.append("completed_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())

        if updates:
            params.append(task_id)
            sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
            await db.execute(sql, tuple(params))
            await db.commit()

    @staticmethod
    async def add_event(
        db: aiosqlite.Connection,
        event_id: str,
        task_id: str,
        event_type: str,
        event_data: dict,
    ) -> TaskEventRecord:
        now = datetime.now(timezone.utc).isoformat()
        data_str = json.dumps(event_data)
        await db.execute(
            "INSERT INTO task_events (id, task_id, event_type, event_data, created_at) VALUES (?, ?, ?, ?, ?)",
            (event_id, task_id, event_type, data_str, now),
        )
        await db.commit()
        return TaskEventRecord(
            id=event_id,
            task_id=task_id,
            event_type=event_type,
            event_data=data_str,
            created_at=now,
        )

    @staticmethod
    async def get_events(db: aiosqlite.Connection, task_id: str) -> list[TaskEventRecord]:
        async with db.execute(
            "SELECT id, task_id, event_type, event_data, created_at FROM task_events WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                TaskEventRecord(
                    id=r[0],
                    task_id=r[1],
                    event_type=r[2],
                    event_data=r[3],
                    created_at=r[4],
                )
                for r in rows
            ]


class ArtifactRepository:
    @staticmethod
    async def create_artifact(
        db: aiosqlite.Connection,
        artifact_id: str,
        user_id: str,
        task_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        mime_type: str = "text/plain",
    ) -> ArtifactRecord:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """
            INSERT INTO artifacts (id, user_id, task_id, filename, file_path, file_size, mime_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, user_id, task_id, filename, file_path, file_size, mime_type, now),
        )
        await db.commit()
        return ArtifactRecord(
            id=artifact_id,
            user_id=user_id,
            task_id=task_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            created_at=now,
        )

    @staticmethod
    async def get_artifact(
        db: aiosqlite.Connection, artifact_id: str, user_id: Optional[str] = None
    ) -> Optional[ArtifactRecord]:
        query = "SELECT id, user_id, task_id, filename, file_path, file_size, mime_type, created_at FROM artifacts WHERE id = ?"
        params = [artifact_id]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        async with db.execute(query, tuple(params)) as cursor:
            row = await cursor.fetchone()
            if row:
                return ArtifactRecord(
                    id=row[0],
                    user_id=row[1],
                    task_id=row[2],
                    filename=row[3],
                    file_path=row[4],
                    file_size=row[5],
                    mime_type=row[6],
                    created_at=row[7],
                )
            return None
