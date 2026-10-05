import os
import sys
from pathlib import Path
import pytest
import pytest_asyncio
import aiosqlite
from httpx import ASGITransport, AsyncClient

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set testing environment variables before importing app
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///./storage/test_nvirya.db"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1"
os.environ["DAILY_TASK_LIMIT"] = "5"

from app.auth.api_keys import ApiKeyService
from app.core.config import settings
from app.db.database import CREATE_TABLES_SQL, init_db
from app.db.repositories import UserRepository
from app.main import app
from app.quotas.rate_limit import rate_limiter

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    test_db_path = settings.sqlite_db_path
    settings.ensure_directories()
    await init_db(test_db_path)
    rate_limiter.clear()
    yield
    try:
        if test_db_path.exists():
            test_db_path.unlink()
    except (PermissionError, OSError):
        pass

@pytest_asyncio.fixture
async def test_db_conn():
    async with aiosqlite.connect(str(settings.sqlite_db_path)) as db:
        db.row_factory = aiosqlite.Row
        yield db

@pytest_asyncio.fixture
async def test_user_and_key(test_db_conn):
    user = await UserRepository.create_user(
        db=test_db_conn,
        user_id="usr_test1",
        username="testuser",
        email="test@nvirya.local",
    )
    plain_key, api_key = await ApiKeyService.create_key_for_user(
        db=test_db_conn,
        user_id=user.id,
        label="Test Key 1",
    )
    return user, api_key, plain_key

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
