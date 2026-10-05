from typing import Any, Optional
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from app.core.constants import (
    ERR_AUTH,
    ERR_RATE_LIMIT,
    ERR_QUOTA,
    ERR_INVALID_REQUEST,
    ERR_PROVIDER,
    ERR_TOOL,
    ERR_SEARCH,
    ERR_ARTIFACT,
    ERR_INTERNAL,
    ERR_TIMEOUT,
)

class NviryaException(Exception):
    """Base exception for all Nvirya API errors with OpenAI-compatible payload."""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_type: str = ERR_INTERNAL,
        code: Optional[str] = None,
        param: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.code = code or error_type
        self.param = param

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "message": self.message,
                "type": self.error_type,
                "code": self.code,
                "param": self.param,
            }
        }

    def to_response(self) -> JSONResponse:
        return JSONResponse(status_code=self.status_code, content=self.to_dict())


class AuthenticationError(NviryaException):
    def __init__(self, message: str = "Invalid or missing API key."):
        super().__init__(
            message=message,
            status_code=401,
            error_type=ERR_AUTH,
            code="invalid_api_key",
        )


class RateLimitError(NviryaException):
    def __init__(self, message: str = "Rate limit exceeded. Try again later."):
        super().__init__(
            message=message,
            status_code=429,
            error_type=ERR_RATE_LIMIT,
            code="rate_limit_exceeded",
        )


class QuotaExceededError(NviryaException):
    def __init__(self, message: str = "Daily task quota exceeded."):
        super().__init__(
            message=message,
            status_code=429,
            error_type=ERR_QUOTA,
            code="daily_quota_exceeded",
        )


class InvalidRequestError(NviryaException):
    def __init__(self, message: str, param: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_type=ERR_INVALID_REQUEST,
            code="invalid_request",
            param=param,
        )


class ProviderError(NviryaException):
    def __init__(self, message: str = "Upstream provider error."):
        super().__init__(
            message=message,
            status_code=502,
            error_type=ERR_PROVIDER,
            code="upstream_provider_error",
        )


class ToolExecutionError(NviryaException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=500,
            error_type=ERR_TOOL,
            code="tool_execution_error",
        )


class SearchUnavailableError(NviryaException):
    def __init__(self, message: str = "Search service is unavailable or not configured."):
        super().__init__(
            message=message,
            status_code=502,
            error_type=ERR_SEARCH,
            code="search_unavailable",
        )


class ArtifactNotFoundError(NviryaException):
    def __init__(self, message: str = "Artifact not found."):
        super().__init__(
            message=message,
            status_code=404,
            error_type=ERR_ARTIFACT,
            code="artifact_not_found",
        )


class TimeoutError(NviryaException):
    def __init__(self, message: str = "Request or task execution timed out."):
        super().__init__(
            message=message,
            status_code=504,
            error_type=ERR_TIMEOUT,
            code="request_timeout",
        )
