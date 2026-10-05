import asyncio
import json
import time
import uuid
from typing import Any, AsyncGenerator, Optional
from google import genai
from app.core.config import settings
from app.core.errors import InvalidRequestError, ProviderError
from app.core.logging import logger
from app.providers.base import BaseAIProvider

class GoogleGenAIProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY is not configured. Set GEMINI_API_KEY in your environment.")
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _normalize_model_name(self, model: str) -> str:
        clean = model.strip()
        if clean.startswith("google/"):
            clean = clean.replace("google/", "")
        if not clean.startswith("models/"):
            clean = f"models/{clean}"
        return clean

    def _format_messages_to_input(self, messages: list[dict[str, Any]]) -> tuple[str, Optional[str]]:
        """
        Extracts system instruction and serializes conversation turns into input text.
        """
        system_instructions = []
        dialogue = []

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
                )

            if role == "system":
                system_instructions.append(content)
            elif role == "user":
                dialogue.append(f"User: {content}")
            elif role == "assistant":
                dialogue.append(f"Assistant: {content}")
            elif role == "tool":
                dialogue.append(f"Tool Output ({m.get('name', 'tool')}): {content}")

        system_text = "\n\n".join(system_instructions) if system_instructions else None
        
        # If single user message, send raw content directly
        if len(dialogue) == 1 and dialogue[0].startswith("User: "):
            input_text = dialogue[0][len("User: "):]
        else:
            input_text = "\n\n".join(dialogue)

        return input_text or "Hello", system_text

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
        target_model = self._normalize_model_name(model)
        input_text, system_instruction = self._format_messages_to_input(messages)

        # Build tools: default to Google Search if requested or enabled
        google_tools = [
            {
                "type": "google_search",
            }
        ]

        generation_config: dict[str, Any] = {
            "max_output_tokens": max_tokens or 65536,
            "thinking_level": "medium",
        }
        if temperature is not None:
            generation_config["temperature"] = temperature
        if top_p is not None:
            generation_config["top_p"] = top_p

        try:
            interaction_kwargs: dict[str, Any] = {
                "model": target_model,
                "input": input_text,
                "tools": google_tools,
                "generation_config": generation_config,
            }
            if system_instruction:
                interaction_kwargs["system_instruction"] = system_instruction

            # Execute via thread pool to keep event loop responsive
            interaction = await asyncio.to_thread(
                client.interactions.create,
                **interaction_kwargs,
            )

            # Extract output text
            content_text = getattr(interaction, "output_text", None)
            if not content_text and hasattr(interaction, "steps") and interaction.steps:
                last_step = interaction.steps[-1]
                if hasattr(last_step, "content") and last_step.content:
                    parts = []
                    for c in last_step.content:
                        if hasattr(c, "text") and c.text:
                            parts.append(c.text)
                        elif isinstance(c, dict) and "text" in c:
                            parts.append(c["text"])
                    content_text = "".join(parts)
                elif hasattr(last_step, "text"):
                    content_text = last_step.text
                else:
                    content_text = str(last_step)

            content_text = content_text or ""

            # Extract token usage
            usage_obj = getattr(interaction, "usage", None)
            prompt_tokens = getattr(usage_obj, "total_input_tokens", 0) or 0
            completion_tokens = getattr(usage_obj, "total_output_tokens", 0) or 0
            total_tokens = getattr(usage_obj, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)

            return {
                "id": f"chatcmpl-gemini-{getattr(interaction, 'id', uuid.uuid4().hex[:12])}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content_text,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
            }

        except Exception as e:
            logger.error(f"Google GenAI API call failed: {e}")
            raise ProviderError(f"Google GenAI provider error: {str(e)}")

    async def stream_chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        # Generate full response and stream SSE chunks
        full_resp = await self.chat_completion(model=model, messages=messages, **kwargs)
        chat_id = full_resp["id"]
        content = full_resp["choices"][0]["message"]["content"] or ""
        created_ts = full_resp["created"]

        init_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created_ts,
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(init_chunk)}\n\n"

        chunk_size = 40
        for i in range(0, len(content), chunk_size):
            slice_text = content[i : i + chunk_size]
            chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": slice_text}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.01)

        final_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created_ts,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": full_resp.get("usage"),
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    async def list_models(self) -> list[dict[str, Any]]:
        return [
            {"id": "models/gemini-3.8-flash", "object": "model", "owned_by": "google"},
            {"id": "models/gemini-2.5-flash", "object": "model", "owned_by": "google"},
            {"id": "models/gemini-2.5-pro", "object": "model", "owned_by": "google"},
        ]
