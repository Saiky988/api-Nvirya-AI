from abc import ABC, abstractmethod
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import httpx
from app.core.config import settings
from app.core.errors import SearchUnavailableError, ToolExecutionError
from app.core.logging import logger

def clean_url(url: str) -> str:
    """Removes tracking query parameters (utm_*, fbclid, etc.)."""
    try:
        parsed = urlparse(url)
        query_dict = parse_qs(parsed.query)
        # Filter out common tracking parameters
        clean_params = {
            k: v for k, v in query_dict.items()
            if not k.startswith("utm_") and k not in ("fbclid", "gclid", "ref", "source")
        }
        new_query = urlencode(clean_params, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    except Exception:
        return url

class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        pass

class SearXNGProvider(SearchProvider):
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = (endpoint_url or settings.SEARXNG_URL).rstrip("/")

    async def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        if not self.endpoint_url:
            raise SearchUnavailableError("Search provider is not configured. Set SEARXNG_URL in environment.")

        params = {
            "q": query,
            "format": "json",
            "engines": "google,duckduckgo,bing,wikipedia",
            "language": "en",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.endpoint_url}/search", params=params)
                if resp.status_code != 200:
                    logger.warning(f"SearXNG returned {resp.status_code}")
                    raise ToolExecutionError(f"Search engine returned error {resp.status_code}")

                data = resp.json()
                raw_results = data.get("results", [])

                seen_urls = set()
                normalized_results = []

                for item in raw_results:
                    raw_url = item.get("url")
                    if not raw_url:
                        continue
                    url = clean_url(raw_url)
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    normalized_results.append({
                        "title": item.get("title", ""),
                        "url": url,
                        "snippet": item.get("content", "") or item.get("snippet", ""),
                        "source": item.get("engine", "searxng"),
                        "published_at": item.get("publishedDate"),
                    })

                    if len(normalized_results) >= limit:
                        break

                return {
                    "query": query,
                    "results": normalized_results,
                }
        except SearchUnavailableError:
            raise
        except ToolExecutionError:
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise ToolExecutionError(f"Search request failed: {str(e)}")
