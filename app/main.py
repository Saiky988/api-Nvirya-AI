import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import aiosqlite
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_v1_router
from app.core.config import settings
from app.core.constants import ERR_INTERNAL, ERR_INVALID_REQUEST
from app.core.errors import NviryaException
from app.core.logging import logger
from app.db.database import init_db
from app.providers.registry import provider_registry

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    logger.info("Starting Nvirya AI Gateway...")
    settings.ensure_directories()
    await init_db()
    logger.info(f"Database initialized at: {settings.sqlite_db_path}")
    yield
    # Shutdown
    logger.info("Shutting down Nvirya AI...")
    provider = provider_registry.get_default_provider()
    if hasattr(provider, "close"):
        await provider.close()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Production-oriented AI API Gateway and Agent Runtime",
    lifespan=lifespan,
)

# Request ID & Logging Middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:16]}"
    request.state.request_id = req_id

    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"Unhandled server error on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "An internal server error occurred.",
                    "type": ERR_INTERNAL,
                    "code": "internal_server_error",
                    "param": None,
                }
            },
            headers={"X-Request-ID": req_id},
        )

    duration_ms = (time.time() - start_time) * 1000.0
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
    return response

# Custom Exception Handlers
@app.exception_handler(NviryaException)
async def nvirya_exception_handler(request: Request, exc: NviryaException):
    resp = exc.to_response()
    req_id = getattr(request.state, "request_id", None)
    if req_id:
        resp.headers["X-Request-ID"] = req_id
    return resp

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_msgs = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        error_msgs.append(f"{loc}: {err.get('msg')}")
    message = "; ".join(error_msgs) if error_msgs else "Validation error."

    req_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": req_id} if req_id else {}
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "message": message,
                "type": ERR_INVALID_REQUEST,
                "code": "validation_error",
                "param": None,
            }
        },
        headers=headers,
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": req_id} if req_id else {}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": str(exc.detail),
                "type": "http_error",
                "code": f"http_{exc.status_code}",
                "param": None,
            }
        },
        headers=headers,
    )

# Health & Readiness Endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Liveness probe: reports if process is running."""
    return {"status": "ok"}

@app.get("/ready", tags=["Health"])
async def ready_check():
    """Readiness probe: validates database and storage accessibility."""
    try:
        # Check SQLite accessibility
        async with aiosqlite.connect(str(settings.sqlite_db_path)) as db:
            await db.execute("SELECT 1")
    except Exception as e:
        logger.error(f"Readiness check failed on DB: {e}")
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "unavailable"})

    # Check storage directories
    if not settings.STORAGE_DIR.exists() or not settings.ARTIFACTS_DIR.exists():
        return JSONResponse(status_code=503, content={"status": "degraded", "storage": "unavailable"})

    return {"status": "ready", "database": "connected", "storage": "accessible"}

# Mount API V1 routes
app.include_router(api_v1_router)
