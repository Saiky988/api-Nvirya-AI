import aiosqlite
from fastapi import APIRouter, Depends
from app.auth.dependencies import AuthContext, get_current_auth
from app.core.config import settings
from app.db.database import get_db
from app.quotas.daily import DailyQuotaService
from app.quotas.usage import UsageService
from app.schemas.usage import QuotaResponse, UsageSummaryResponse

router = APIRouter()

@router.get("/quota", response_model=QuotaResponse)
async def get_user_quota(
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
) -> QuotaResponse:
    """Returns the current user's daily quota status and rate limit."""
    limit, used, remaining = await DailyQuotaService.get_user_quota_info(db, auth.user.id)
    return QuotaResponse(
        daily_limit=limit,
        daily_used=used,
        daily_remaining=remaining,
        rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    )

@router.get("/usage", response_model=UsageSummaryResponse)
async def get_user_usage(
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
) -> UsageSummaryResponse:
    """Returns aggregated token and request usage summary for the user."""
    summary = await UsageService.get_summary(db, auth.user.id)
    return UsageSummaryResponse(
        user_id=auth.user.id,
        total_requests=summary["total_requests"],
        total_prompt_tokens=summary["total_prompt_tokens"],
        total_completion_tokens=summary["total_completion_tokens"],
        total_tokens=summary["total_tokens"],
        total_tool_calls=summary["total_tool_calls"],
    )
