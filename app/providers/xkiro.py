import asyncio
import json
import time
from typing import Any, AsyncGenerator, Optional
import httpx
from app.core.config import settings
from app.core.errors import InvalidRequestError, ProviderError
from app.core.logging import logger
from app.providers.base import BaseAIProvider

class XKiroProvider(BaseAIProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.XKIRO_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.XKIRO_API_KEY
        self._client: Optional[httpx.AsyncClient] = None
        self._models_cache: Optional[list[dict[str, Any]]] = None
        self._models_cache_time: float = 0.0
        self._cache_ttl: float = 600.0  # 10 minutes
        self.model_health: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "NviryaAI/1.0",
                "Content-Type": "application/json",
            }
            timeout = httpx.Timeout(
                connect=10.0,
                read=90.0,
                write=30.0,
                pool=10.0,
            )
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=timeout,
                limits=limits,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _record_health(self, model: str, success: bool, latency: float = 0.0) -> None:
        if model not in self.model_health:
            self.model_health[model] = {
                "last_success": None,
                "last_failure": None,
                "consecutive_failures": 0,
                "last_latency": 0.0,
            }
        rec = self.model_health[model]
        if success:
            rec["last_success"] = time.time()
            rec["consecutive_failures"] = 0
            rec["last_latency"] = latency
        else:
            rec["last_failure"] = time.time()
            rec["consecutive_failures"] += 1

    def is_model_healthy(self, model: str) -> bool:
        rec = self.model_health.get(model)
        if not rec:
            return True
        # If model had 3+ consecutive failures in the last 2 minutes, treat as degraded
        if rec["consecutive_failures"] >= 3:
            if time.time() - (rec["last_failure"] or 0) < 120.0:
                return False
        return True

    def _build_payload(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[Any] = None,
        stream: bool = False,
        response_format: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if stop is not None:
            payload["stop"] = stop
        if response_format is not None:
            payload["response_format"] = response_format

        for k, v in kwargs.items():
            if v is not None and k not in payload:
                payload[k] = v
        return payload

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[Any] = None,
        response_format: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        client = self._get_client()
        payload = self._build_payload(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            stream=False,
            response_format=response_format,
            **kwargs,
        )

        start_time = time.time()
        try:
            resp = await client.post("/chat/completions", json=payload)
            latency = time.time() - start_time
            if resp.status_code == 200:
                self._record_health(model, success=True, latency=latency)
                return resp.json()
            
            # Handle upstream errors
            self._record_health(model, success=False, latency=latency)
            error_text = resp.text
            logger.warning(f"Upstream xKiro error: status={resp.status_code} body={error_text[:200]}")
            
            if resp.status_code == 400:
                raise InvalidRequestError(f"Upstream model rejected request: {error_text[:120]}")
            elif resp.status_code in (401, 403):
                raise ProviderError("Upstream AI provider authentication error.")
            elif resp.status_code == 429:
                raise ProviderError("Upstream AI provider rate limit reached.")
            else:
                raise ProviderError(f"Upstream AI provider error (status {resp.status_code}).")

        except httpx.TimeoutException:
            self._record_health(model, success=False)
            raise ProviderError("Upstream AI provider timed out.")
        except (InvalidRequestError, ProviderError):
            raise
        except Exception as e:
            self._record_health(model, success=False)
            logger.error(f"Unexpected error calling xKiro: {type(e).__name__}")
            raise ProviderError("Failed to communicate with upstream AI provider.")

    async def stream_chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[Any] = None,
        response_format: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        payload = self._build_payload(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            stream=True,
            response_format=response_format,
            **kwargs,
        )

        start_time = time.time()
        try:
            async with client.stream("POST", "/chat/completions", json=payload) as resp:
                if resp.status_code != 200:
                    err_body = await resp.aread()
                    self._record_health(model, success=False)
                    logger.warning(f"Upstream stream error {resp.status_code}: {err_body.decode('utf-8', 'ignore')[:200]}")
                    raise ProviderError(f"Upstream stream error (status {resp.status_code})")

                async for line in resp.aiter_lines():
                    clean_line = line.strip()
                    if not clean_line:
                        continue
                    if clean_line.startswith("data:"):
                        yield clean_line
                    elif clean_line.startswith(":"):
                        # SSE keep-alive comment
                        continue
                    else:
                        yield f"data: {clean_line}"

            self._record_health(model, success=True, latency=time.time() - start_time)
        except (ProviderError, InvalidRequestError):
            raise
        except httpx.TimeoutException:
            self._record_health(model, success=False)
            raise ProviderError("Upstream streaming timed out.")
        except Exception as e:
            self._record_health(model, success=False)
            logger.error(f"Stream exception: {type(e).__name__}")
            raise ProviderError("Failed streaming from upstream AI provider.")

    async def list_models(self) -> list[dict[str, Any]]:
        now = time.time()
        if self._models_cache and (now - self._models_cache_time < self._cache_ttl):
            return self._models_cache

        client = self._get_client()
        try:
            resp = await client.get("/models")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                async with self._lock:
                    self._models_cache = models
                    self._models_cache_time = now
                return models
            logger.warning(f"Failed to fetch models from xKiro: status={resp.status_code}")
            return self._models_cache or []
        except Exception as e:
            logger.warning(f"Error fetching models: {e}")
            return self._models_cache or []
