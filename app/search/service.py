from typing import Any, Optional
from app.search.cache import search_cache
from app.search.providers import SearchProvider, SearXNGProvider

class SearchService:
    def __init__(self, provider: Optional[SearchProvider] = None):
        self.provider = provider or SearXNGProvider()

    async def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        normalized_query = query.strip().lower()
        cache_key = f"search:{normalized_query}:{limit}"

        cached = search_cache.get(cache_key)
        if cached:
            return cached

        results = await self.provider.search(query=query.strip(), limit=limit)
        search_cache.set(cache_key, results)
        return results

search_service = SearchService()
