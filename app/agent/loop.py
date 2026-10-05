import json
from typing import Any, Callable, Coroutine, Optional
from app.agent.budgets import ExecutionBudget
from app.agent.context import AgentContext
from app.agent.messages import prepare_agent_messages
from app.core.constants import (
    EVENT_MODEL_REQUESTED,
    EVENT_TOOL_STARTED,
    EVENT_TOOL_COMPLETED,
    EVENT_TOOL_FAILED,
)
from app.core.errors import InvalidRequestError, ToolExecutionError
from app.core.logging import logger
from app.providers.base import BaseAIProvider
from app.tools.registry import tool_registry

EventCallback = Optional[Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]]

class AgentLoop:
    def __init__(
        self,
        provider: BaseAIProvider,
        upstream_model: str,
        context: AgentContext,
        budget: Optional[ExecutionBudget] = None,
        event_callback: EventCallback = None,
        enabled_tools: Optional[list[str]] = None,
    ):
        self.provider = provider
        self.upstream_model = upstream_model
        self.context = context
        self.budget = budget or ExecutionBudget()
        self.event_callback = event_callback
        self.enabled_tools = enabled_tools

    async def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        if self.event_callback:
            try:
                await self.event_callback(event_type, data)
            except Exception as e:
                logger.warning(f"Error emitting event {event_type}: {e}")

    async def run(
        self,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tool_choice: Optional[Any] = "auto",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Runs the multi-step agent execution loop.
        Returns the final completion response dictionary.
        """
        # Prepare system instructions & guardrails
        self.context.messages = prepare_agent_messages(self.context.messages)

        # Build tools schema definitions
        tool_defs = None
        if tool_choice != "none":
            tool_defs = tool_registry.get_definitions(self.enabled_tools)
            if not tool_defs:
                tool_defs = None
                tool_choice = None

        while self.budget.can_take_step():
            self.budget.record_step()

            await self._emit_event(EVENT_MODEL_REQUESTED, {
                "step": self.budget.steps_taken,
                "model": self.upstream_model,
            })

            # Call upstream model
            resp = await self.provider.chat_completion(
                model=self.upstream_model,
                messages=self.context.messages,
                tools=tool_defs,
                tool_choice=tool_choice,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                **kwargs,
            )

            # Record usage
            self.context.record_usage(resp.get("usage", {}))

            choices = resp.get("choices", [])
            if not choices:
                return resp

            first_choice = choices[0]
            message = first_choice.get("message", {})
            tool_calls = message.get("tool_calls")

            # If no tool calls requested, we reached the final answer
            if not tool_calls:
                return resp

            # Append the assistant's tool-calling message to context
            self.context.append_message(message)

            # Process each requested tool call
            for call in tool_calls:
                call_id = call.get("id", f"call_{self.budget.tool_calls_count}")
                function_data = call.get("function", {})
                tool_name = function_data.get("name", "")
                raw_args = function_data.get("arguments", "{}")

                await self._emit_event(EVENT_TOOL_STARTED, {
                    "tool": tool_name,
                    "call_id": call_id,
                })

                # 1. Check tool budget
                can_run, budget_err = self.budget.can_call_tool(tool_name)
                if not can_run:
                    self.context.append_tool_result(call_id, tool_name, f"Error: {budget_err}")
                    await self._emit_event(EVENT_TOOL_FAILED, {
                        "tool": tool_name,
                        "call_id": call_id,
                        "error": budget_err,
                    })
                    continue

                # 2. Check tool existence
                tool_obj = tool_registry.get_tool(tool_name)
                if not tool_obj:
                    err_msg = f"Error: Unknown tool '{tool_name}'."
                    self.context.append_tool_result(call_id, tool_name, err_msg)
                    await self._emit_event(EVENT_TOOL_FAILED, {
                        "tool": tool_name,
                        "call_id": call_id,
                        "error": err_msg,
                    })
                    continue

                # 3. Parse arguments safely
                parsed_args, parse_err = tool_registry.parse_arguments(raw_args)
                if parse_err:
                    err_msg = f"Error parsing arguments: {parse_err}. Please format valid JSON."
                    self.context.append_tool_result(call_id, tool_name, err_msg)
                    await self._emit_event(EVENT_TOOL_FAILED, {
                        "tool": tool_name,
                        "call_id": call_id,
                        "error": err_msg,
                    })
                    continue

                # 4. Execute tool
                self.budget.record_tool_call(tool_name)
                self.context.total_tool_calls += 1
                try:
                    result_str = await tool_obj.execute(parsed_args, self.context.tool_context)
                    self.context.append_tool_result(call_id, tool_name, result_str)
                    await self._emit_event(EVENT_TOOL_COMPLETED, {
                        "tool": tool_name,
                        "call_id": call_id,
                        "result_preview": result_str[:200],
                    })
                except Exception as e:
                    err_str = f"Tool execution error: {str(e)}"
                    self.context.append_tool_result(call_id, tool_name, err_str)
                    await self._emit_event(EVENT_TOOL_FAILED, {
                        "tool": tool_name,
                        "call_id": call_id,
                        "error": err_str,
                    })

        # If budget exhausted, return last message or synthesis
        return resp
