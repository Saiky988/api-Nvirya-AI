import time
from fastapi import APIRouter
from app.core.constants import PUBLIC_MODELS
from app.schemas.models import ModelCard, ModelListResponse

router = APIRouter()

@router.get("/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """Lists the available public Nvirya AI models."""
    now = int(time.time())
    models_data = [
        ModelCard(
            id=model_id,
            object="model",
            created=now,
            owned_by="nvirya",
        )
        for model_id in PUBLIC_MODELS
    ]
    return ModelListResponse(object="list", data=models_data)
