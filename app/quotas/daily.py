from datetime import datetime, timezone, timedelta
from typing import Optional
import aiosqlite
from app.core.config import settings
from app.core.errors import QuotaExceededError
from app.db.repositories import QuotaRepository

# Asia/Ho_Chi_Minh is UTC+7 (no DST)
VN_TIMEZONE = timezone(timedelta(hours=7))

def get_current_date_vn() -> str:
    """Returns today's date formatted as YYYY-MM-DD in Asia/Ho_Chi_Minh time."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Ho_Chi_Minh")
        return datetime.now(tz).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(VN_TIMEZONE).strftime("%Y-%m-%d")


class DailyQuotaService:
    @staticmethod
    async def get_user_quota_info(
        db: aiosqlite.Connection, user_id: str
    ) -> tuple[int, int, int]:
        """
        Returns: (daily_limit, daily_used, daily_remaining)
        """
        limit = settings.DAILY_TASK_LIMIT
        today = get_current_date_vn()
        used = await QuotaRepository.get_used_today(db, user_id, today)
        remaining = max(0, limit - used)
        return limit, used, remaining

    @staticmethod
    async def consume_quota(db: aiosqlite.Connection, user_id: str) -> None:
        """
        Atomically checks and consumes 1 daily quota unit.
        Raises QuotaExceededError if limit is reached.
        """
        limit = settings.DAILY_TASK_LIMIT
        today = get_current_date_vn()
        allowed = await QuotaRepository.try_consume_daily_quota(
            db=db, user_id=user_id, date_str=today, max_limit=limit
        )
        if not allowed:
            raise QuotaExceededError(
                f"Daily task quota of {limit} tasks reached for today ({today}). Quota resets at 00:00 (Asia/Ho_Chi_Minh)."
            )
