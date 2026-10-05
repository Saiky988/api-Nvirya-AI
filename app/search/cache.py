import time
from typing import Any, Optional

class SearchCache:
    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl = ttl_seconds
        self._cache: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        timestamp, value = entry
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        self._cache.clear()

search_cache = SearchCache(ttl_seconds=300.0)
