import pytest
from unittest.mock import AsyncMock, patch
from app.agent.orchestrator import agent_orchestrator
from app.providers.base import BaseAIProvider
from app.providers.registry import provider_registry

class MockAIProvider(BaseAIProvider):
    async def chat_completion(self, model, messages, **kwargs):
        return {
            "id": "chatcmpl-mock123",
            "object": "chat.completion",
            "created": 1700000000,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Mocked assistant reply."},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

    async def stream_chat_completion(self, model, messages, **kwargs):
        yield 'data: {"id":"chatcmpl-mock","choices":[{"delta":{"content":"Mocked"}}]}\n\n'
        yield 'data: [DONE]\n\n'

    async def list_models(self):
        return [{"id": "mock/model"}]

@pytest.mark.asyncio
async def test_get_models_list(async_client):
    resp = await async_client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    ids = [m["id"] for m in data["data"]]
    assert "nvirya-auto" in ids
    assert "nvirya-code" in ids
    assert "nvirya-analysis" in ids

@pytest.mark.asyncio
async def test_chat_completion_non_streaming(async_client, test_user_and_key):
    user, key, plain_key = test_user_and_key
    headers = {"Authorization": f"Bearer {plain_key}"}

    # Use mock provider for predictable testing
    orig_provider = provider_registry.get_default_provider()
    mock_prov = MockAIProvider()
    provider_registry.set_default_provider(mock_prov)
    agent_orchestrator.provider = mock_prov

    try:
        req_payload = {
            "model": "nvirya-auto",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }
        resp = await async_client.post("/v1/chat/completions", json=req_payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == "nvirya-auto"
        assert data["choices"][0]["message"]["content"] == "Mocked assistant reply."
        assert "usage" in data
        assert data["usage"]["total_tokens"] == 15
    finally:
        provider_registry.set_default_provider(orig_provider)
        agent_orchestrator.provider = orig_provider

@pytest.mark.asyncio
async def test_chat_completion_streaming(async_client, test_user_and_key):
    user, key, plain_key = test_user_and_key
    headers = {"Authorization": f"Bearer {plain_key}"}

    orig_provider = provider_registry.get_default_provider()
    mock_prov = MockAIProvider()
    provider_registry.set_default_provider(mock_prov)
    agent_orchestrator.provider = mock_prov

    try:
        req_payload = {
            "model": "nvirya-auto",
            "messages": [{"role": "user", "content": "Stream test"}],
            "stream": True,
        }
        resp = await async_client.post("/v1/chat/completions", json=req_payload, headers=headers)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        body_text = resp.text
        assert "data:" in body_text
        assert "[DONE]" in body_text
    finally:
        provider_registry.set_default_provider(orig_provider)
        agent_orchestrator.provider = orig_provider

@pytest.mark.asyncio
async def test_chat_completion_invalid_request_validation(async_client, test_user_and_key):
    user, key, plain_key = test_user_and_key
    headers = {"Authorization": f"Bearer {plain_key}"}

    # Missing messages field
    resp = await async_client.post("/v1/chat/completions", json={"model": "nvirya-auto"}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["type"] == "invalid_request_error"
