import json
import pytest
from app.agent.budgets import ExecutionBudget
from app.agent.context import AgentContext
from app.agent.loop import AgentLoop
from app.providers.base import BaseAIProvider

class ToolCallingMockProvider(BaseAIProvider):
    def __init__(self):
        self.call_count = 0

    async def chat_completion(self, model, messages, tools=None, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            # First turn: model requests tool calculator
            return {
                "id": "chatcmpl-tool1",
                "object": "chat.completion",
                "created": 1700000000,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_calc_1",
                                    "type": "function",
                                    "function": {
                                        "name": "calculator",
                                        "arguments": '{"expression": "25 * 4"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25},
            }
        else:
            # Second turn: model receives tool output and returns final answer
            return {
                "id": "chatcmpl-final",
                "object": "chat.completion",
                "created": 1700000000,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "The calculated result is 100.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 30, "completion_tokens": 8, "total_tokens": 38},
            }

    async def stream_chat_completion(self, model, messages, **kwargs):
        yield 'data: [DONE]\n\n'

    async def list_models(self):
        return []

@pytest.mark.asyncio
async def test_agent_tool_execution_loop_integration():
    mock_provider = ToolCallingMockProvider()
    context = AgentContext(
        task_id="task_integ_1",
        user_id="user_integ_1",
        messages=[{"role": "user", "content": "What is 25 * 4?"}],
    )
    budget = ExecutionBudget(max_steps=5)

    loop = AgentLoop(
        provider=mock_provider,
        upstream_model="mock/model",
        context=context,
        budget=budget,
    )

    result = await loop.run()

    # 1. Verify two model turns occurred
    assert mock_provider.call_count == 2

    # 2. Verify tool result was injected into context
    tool_messages = [m for m in context.messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["content"] == "100"
    assert tool_messages[0]["tool_call_id"] == "call_calc_1"

    # 3. Verify final answer
    assert result["choices"][0]["message"]["content"] == "The calculated result is 100."
    assert context.total_tool_calls == 1

class MalformedToolMockProvider(BaseAIProvider):
    def __init__(self):
        self.call_count = 0

    async def chat_completion(self, model, messages, tools=None, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            # Returns broken JSON in tool call
            return {
                "id": "chatcmpl-err1",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_bad",
                                    "type": "function",
                                    "function": {
                                        "name": "calculator",
                                        "arguments": "{bad json",
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {},
            }
        else:
            return {
                "id": "chatcmpl-recovered",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Recovered from syntax error."},
                    }
                ],
                "usage": {},
            }

    async def stream_chat_completion(self, model, messages, **kwargs):
        yield 'data: [DONE]\n\n'

    async def list_models(self):
        return []

@pytest.mark.asyncio
async def test_agent_loop_recovers_from_malformed_tool_args():
    mock_provider = MalformedToolMockProvider()
    context = AgentContext(
        task_id="task_err_1",
        user_id="user_err_1",
        messages=[{"role": "user", "content": "Compute something"}],
    )
    budget = ExecutionBudget(max_steps=3)

    loop = AgentLoop(
        provider=mock_provider,
        upstream_model="mock/model",
        context=context,
        budget=budget,
    )

    result = await loop.run()
    # Ensure loop caught error, injected error message to model, and continued to step 2
    assert mock_provider.call_count == 2
    tool_msg = [m for m in context.messages if m.get("role") == "tool"][0]
    assert "error parsing arguments" in tool_msg["content"].lower()
    assert result["choices"][0]["message"]["content"] == "Recovered from syntax error."
