import asyncio
import time
from app.core.config import settings
from app.core.errors import RateLimitError

class SlidingWindowRateLimiter:
    def __init__(self, limit: int = 1, window_seconds: float = 60.0):
        self.limit = limit
        self.window_seconds = window_seconds
        self._history: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def check_and_record(self, key: str) -> None:
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            timestamps = self._history.get(key, [])
            # Filter timestamps outside the sliding window
            timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= self.limit:
                retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
                raise RateLimitError(
                    f"Rate limit exceeded: {self.limit} request(s) per minute. Try again in {retry_after}s."
                )

            timestamps.append(now)
            self._history[key] = timestamps

    def reset_key(self, key: str) -> None:
        """Helper for testing or manual resets."""
        self._history.pop(key, None)

    def clear(self) -> None:
        """Helper to clear all rate limit tracking."""
        self._history.clear()

rate_limiter = SlidingWindowRateLimiter(
    limit=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60.0,
)
