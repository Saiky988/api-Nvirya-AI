from typing import Any, Optional
from app.core.config import settings
from app.core.constants import (
    MODEL_AUTO,
    MODEL_CODE,
    MODEL_ANALYSIS,
    MODEL_FAST,
    MODEL_VISION,
    PUBLIC_MODELS,
)
from app.core.errors import InvalidRequestError
from app.providers.registry import provider_registry
from app.routing.policies import classify_prompt_intent

class ModelRouter:
    @staticmethod
    def resolve_model(
        requested_model: str,
        messages: list[dict[str, Any]],
    ) -> tuple[str, str]:
        """
        Resolves the requested model to an upstream provider model ID.
        Returns: (upstream_model_id, public_alias)
        """
        requested = requested_model.strip()
        provider = provider_registry.get_default_provider()

        # Handle nvirya-vision placeholder
        if requested == MODEL_VISION:
            raise InvalidRequestError("Vision capabilities are not yet enabled in this release.")

        # Determine target alias
        target_alias = requested
        if requested == MODEL_AUTO:
            target_alias = classify_prompt_intent(messages)

        # Map alias to configured upstream model
        if target_alias == MODEL_CODE:
            primary = settings.CODE_MODEL
            fallback = settings.CODE_FALLBACK_MODEL
            upstream = primary
            if hasattr(provider, "is_model_healthy") and not provider.is_model_healthy(primary):
                upstream = fallback or primary
            return upstream, requested

        elif target_alias == MODEL_ANALYSIS:
            primary = settings.ANALYSIS_MODEL
            fallback = settings.CODE_MODEL
            upstream = primary
            if hasattr(provider, "is_model_healthy") and not provider.is_model_healthy(primary):
                upstream = fallback or primary
            return upstream, requested

        elif target_alias == MODEL_FAST:
            primary = settings.FAST_MODEL or settings.CODE_MODEL
            fallback = settings.CODE_MODEL
            upstream = primary
            if hasattr(provider, "is_model_healthy") and not provider.is_model_healthy(primary):
                upstream = fallback or primary
            return upstream, requested

        # Direct model ID check (e.g. vendor/model format)
        if "/" in requested:
            return requested, requested

        if requested in PUBLIC_MODELS:
            return settings.CODE_MODEL, requested

        raise InvalidRequestError(f"Model '{requested}' is not supported. Use one of: {', '.join(PUBLIC_MODELS)}")

model_router = ModelRouter()
