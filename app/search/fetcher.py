from typing import Any, Optional
from urllib.parse import urljoin
import httpx
from app.core.errors import InvalidRequestError, ToolExecutionError
from app.search.extractor import extract_readable_text
from app.search.security import validate_url_security

MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024  # 2 MB limit
MAX_REDIRECTS = 3

class WebFetcher:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch(self, url: str) -> dict[str, Any]:
        """
        Fetches web page with strict SSRF protection and manual redirect checking.
        Returns extracted readable content.
        """
        current_url = validate_url_security(url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 NviryaAI/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        }

        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=headers,
            follow_redirects=False,
            verify=True,
        ) as client:
            redirect_count = 0
            while redirect_count <= MAX_REDIRECTS:
                try:
                    resp = await client.get(current_url)
                except httpx.TimeoutException:
                    raise ToolExecutionError(f"Connection timed out while fetching '{current_url}'.")
                except Exception as e:
                    raise ToolExecutionError(f"Failed to fetch '{current_url}': {str(e)}")

                # Check for redirects
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        break
                    next_url = urljoin(current_url, location)
                    # SSRF validate redirect target!
                    current_url = validate_url_security(next_url)
                    redirect_count += 1
                    continue

                if resp.status_code >= 400:
                    raise ToolExecutionError(f"HTTP error {resp.status_code} returned by '{current_url}'.")

                # Content type check
                content_type = resp.headers.get("content-type", "").lower()
                if not any(t in content_type for t in ("text/html", "application/xhtml+xml", "text/plain")):
                    raise ToolExecutionError(f"Unsupported content type '{content_type}' at '{current_url}'.")

                # Size check
                content_bytes = resp.content
                if len(content_bytes) > MAX_DOWNLOAD_BYTES:
                    content_bytes = content_bytes[:MAX_DOWNLOAD_BYTES]

                html_text = content_bytes.decode("utf-8", errors="replace")
                return extract_readable_text(html_text, source_url=current_url)

            raise ToolExecutionError(f"Too many redirects encountered while fetching '{url}'.")

web_fetcher = WebFetcher()
