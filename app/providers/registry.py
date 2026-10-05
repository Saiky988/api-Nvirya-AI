from typing import Optional
from app.providers.base import BaseAIProvider
from app.providers.xkiro import XKiroProvider

class ProviderRegistry:
    def __init__(self):
        self._default_provider: Optional[BaseAIProvider] = None

    def get_default_provider(self) -> BaseAIProvider:
        if self._default_provider is None:
            self._default_provider = XKiroProvider()
        return self._default_provider

    def set_default_provider(self, provider: BaseAIProvider) -> None:
        self._default_provider = provider

provider_registry = ProviderRegistry()
