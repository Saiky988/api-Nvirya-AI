from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional

class BaseAIProvider(ABC):
    @abstractmethod
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
        """Sends a non-streaming chat completion request and returns the normalized response dict."""
        pass

    @abstractmethod
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
        """Streams chat completion raw SSE chunks."""
        pass

    @abstractmethod
    async def list_models(self) -> list[dict[str, Any]]:
        """Returns the list of available upstream models."""
        pass
