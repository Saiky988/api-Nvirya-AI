from typing import Optional
from app.core.config import settings
from app.providers.base import BaseAIProvider
from app.providers.google import GoogleGenAIProvider
from app.providers.xkiro import XKiroProvider

class ProviderRegistry:
    def __init__(self):
        self._default_provider: Optional[BaseAIProvider] = None
        self._google_provider: Optional[GoogleGenAIProvider] = None

    def get_default_provider(self) -> BaseAIProvider:
        if self._default_provider is None:
            self._default_provider = XKiroProvider()
        return self._default_provider

    def set_default_provider(self, provider: BaseAIProvider) -> None:
        self._default_provider = provider

    def get_google_provider(self) -> GoogleGenAIProvider:
        if self._google_provider is None:
            self._google_provider = GoogleGenAIProvider()
        return self._google_provider

    def get_provider_for_model(self, model_name: str) -> BaseAIProvider:
        """
        Dispatches to GoogleGenAIProvider if model is a Gemini/Google model and GEMINI_API_KEY is configured,
        otherwise defaults to XKiroProvider.
        """
        clean_model = model_name.strip().lower()
        if ("gemini" in clean_model or clean_model.startswith("google/")) and settings.GEMINI_API_KEY:
            return self.get_google_provider()
        return self.get_default_provider()

provider_registry = ProviderRegistry()
