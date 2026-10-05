from unittest.mock import MagicMock, patch
import pytest
from app.core.errors import ProviderError
from app.providers.google import GoogleGenAIProvider

def test_google_provider_missing_key():
    prov = GoogleGenAIProvider(api_key="")
    with pytest.raises(ProviderError) as excinfo:
        prov._get_client()
    assert "GEMINI_API_KEY is not configured" in str(excinfo.value)

def test_google_provider_message_formatting():
    prov = GoogleGenAIProvider(api_key="test-key")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]
    input_text, sys_instruction = prov._format_messages_to_input(messages)
    assert sys_instruction == "You are a helpful assistant."
    assert "User: Hello!" in input_text
    assert "Assistant: Hi there!" in input_text
    assert "User: How are you?" in input_text

@pytest.mark.asyncio
async def test_google_provider_chat_completion_mock():
    prov = GoogleGenAIProvider(api_key="test-key")

    mock_interaction = MagicMock()
    mock_interaction.id = "int_123"
    mock_interaction.output_text = "Hello from Gemini 3.8 Flash!"
    mock_step = MagicMock()
    mock_step.text = "Hello from Gemini 3.8 Flash!"
    mock_interaction.steps = [mock_step]
    mock_interaction.usage.total_input_tokens = 15
    mock_interaction.usage.total_output_tokens = 10
    mock_interaction.usage.total_tokens = 25

    with patch.object(prov, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.interactions.create.return_value = mock_interaction
        mock_get_client.return_value = mock_client

        resp = await prov.chat_completion(
            model="models/gemini-3.8-flash",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert resp["object"] == "chat.completion"
        assert resp["choices"][0]["message"]["content"] == "Hello from Gemini 3.8 Flash!"
        assert resp["usage"]["total_tokens"] == 25
        assert mock_client.interactions.create.called
        call_kwargs = mock_client.interactions.create.call_args[1]
        assert call_kwargs["model"] == "models/gemini-3.8-flash"
        assert call_kwargs["tools"] == [{"type": "google_search"}]
        assert call_kwargs["generation_config"]["thinking_level"] == "medium"
