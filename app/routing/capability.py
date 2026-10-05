from dataclasses import dataclass

@dataclass
class ModelCapabilities:
    text: bool = True
    tools: bool = True
    streaming: bool = True
    reasoning: bool = False
    vision: bool = False
    audio_input: bool = False
    audio_output: bool = False

DEFAULT_CAPABILITIES = ModelCapabilities(text=True, tools=True, streaming=True)
