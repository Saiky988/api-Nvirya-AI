from fastapi import APIRouter
from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.chat import router as chat_router
from app.api.v1.models import router as models_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.usage import router as usage_router

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(models_router, tags=["Models"])
api_v1_router.include_router(chat_router, tags=["Chat"])
api_v1_router.include_router(tasks_router, tags=["Tasks"])
api_v1_router.include_router(usage_router, tags=["Usage & Quota"])
api_v1_router.include_router(api_keys_router, tags=["API Keys"])
api_v1_router.include_router(artifacts_router, tags=["Artifacts"])
