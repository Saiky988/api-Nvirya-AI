import sqlite3
from pathlib import Path
from typing import AsyncGenerator, Optional
import aiosqlite
from app.core.config import settings

CREATE_TABLES_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    user_id TEXT NOT NULL,
    label TEXT,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    last_used_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

CREATE TABLE IF NOT EXISTS daily_quotas (
    user_id TEXT NOT NULL,
    quota_date TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, quota_date),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS usage_records (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    api_key_id TEXT NOT NULL,
    model_alias TEXT NOT NULL,
    upstream_model TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    status TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    tool_calls INTEGER NOT NULL DEFAULT 0,
    duration_ms REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_usage_user_id ON usage_records(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_created_at ON usage_records(created_at);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    model_alias TEXT NOT NULL,
    selected_model TEXT NOT NULL,
    status TEXT NOT NULL,
    current_step INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    result TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

CREATE TABLE IF NOT EXISTS task_events (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    mime_type TEXT NOT NULL DEFAULT 'text/plain',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_artifacts_user_id ON artifacts(user_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_task_id ON artifacts(task_id);
"""

def init_db_sync(db_path: Optional[Path] = None) -> None:
    target_path = db_path or settings.sqlite_db_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(target_path)) as conn:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()

async def init_db(db_path: Optional[Path] = None) -> None:
    target_path = db_path or settings.sqlite_db_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(target_path)) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    db_path = str(settings.sqlite_db_path)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db
