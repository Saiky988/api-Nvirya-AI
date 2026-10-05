import asyncio
import json
import time
import uuid
from typing import Any, AsyncGenerator, Optional
import aiosqlite
from app.agent.budgets import ExecutionBudget
from app.agent.context import AgentContext
from app.agent.loop import AgentLoop, EventCallback
from app.core.config import settings
from app.core.constants import MODEL_ANALYSIS
from app.core.logging import logger
from app.providers.base import BaseAIProvider
from app.providers.registry import provider_registry
from app.routing.model_router import model_router

class AgentOrchestrator:
    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self.provider = provider or provider_registry.get_default_provider()

    async def execute_task(
        self,
        task_id: str,
        user_id: str,
        model_name: str,
        messages: list[dict[str, Any]],
        db: Optional[aiosqlite.Connection] = None,
        event_callback: EventCallback = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tool_choice: Optional[Any] = "auto",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Executes a complete agent request with tool loop, model resolution, and synthesis.
        """
        # 1. Resolve model
        upstream_model, public_alias = model_router.resolve_model(model_name, messages)

        # 2. Build context
        context = AgentContext(
            task_id=task_id,
            user_id=user_id,
            messages=messages,
            db=db,
        )

        budget = ExecutionBudget()

        # 3. Initialize loop
        loop = AgentLoop(
            provider=self.provider,
            upstream_model=upstream_model,
            context=context,
            budget=budget,
            event_callback=event_callback,
        )

        # 4. Execute tool loop
        response = await loop.run(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            **kwargs,
        )

        # 5. Analysis Model Synthesis Strategy (Section 33)
        # If tools were used and the public model or classification was analysis,
        # synthesize with the analysis model if different from upstream
        if (
            context.total_tool_calls > 0
            and public_alias == MODEL_ANALYSIS
            and upstream_model != settings.ANALYSIS_MODEL
        ):
            try:
                synth_response = await self.provider.chat_completion(
                    model=settings.ANALYSIS_MODEL,
                    messages=context.messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                context.record_usage(synth_response.get("usage", {}))
                response = synth_response
            except Exception as e:
                logger.warning(f"Analysis model synthesis failed, retaining primary output: {e}")

        # 6. Normalize response format
        response["model"] = public_alias
        response["id"] = response.get("id") or f"chatcmpl-{uuid.uuid4()}"
        response["object"] = "chat.completion"
        response["created"] = int(time.time())

        # Combine total usage
        total_p = context.total_prompt_tokens or response.get("usage", {}).get("prompt_tokens", 0)
        total_c = context.total_completion_tokens or response.get("usage", {}).get("completion_tokens", 0)
        response["usage"] = {
            "prompt_tokens": total_p,
            "completion_tokens": total_c,
            "total_tokens": total_p + total_c,
        }

        # Store tool count on response for usage recording
        response["_tool_calls"] = context.total_tool_calls
        response["_upstream_model"] = upstream_model

        return response

    async def stream_execute_task(
        self,
        task_id: str,
        user_id: str,
        model_name: str,
        messages: list[dict[str, Any]],
        db: Optional[aiosqlite.Connection] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tool_choice: Optional[Any] = "auto",
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Executes a task and streams OpenAI-compatible chunks (SSE).
        """
        # Execute tool loop to completion
        result = await self.execute_task(
            task_id=task_id,
            user_id=user_id,
            model_name=model_name,
            messages=messages,
            db=db,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            **kwargs,
        )

        chat_id = result.get("id", f"chatcmpl-{uuid.uuid4()}")
        public_model = result.get("model", model_name)
        choices = result.get("choices", [])
        content = ""
        if choices:
            content = choices[0].get("message", {}).get("content", "")

        # Chunk the content into streaming pieces
        chunk_size = 40  # Characters per chunk for natural streaming
        created_ts = int(time.time())

        # Initial chunk with role
        initial_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created_ts,
            "model": public_model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(initial_chunk)}\n\n"

        for i in range(0, len(content), chunk_size):
            slice_text = content[i : i + chunk_size]
            chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": public_model,
                "choices": [{"index": 0, "delta": {"content": slice_text}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.01)

        # Final chunk with finish_reason
        final_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created_ts,
            "model": public_model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": result.get("usage"),
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

agent_orchestrator = AgentOrchestrator()
