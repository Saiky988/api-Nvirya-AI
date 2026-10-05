import uuid
from typing import Optional
import aiosqlite
from fastapi import Depends, Header, Request
from app.auth.dependencies import AuthContext, get_current_auth
from app.db.database import get_db
from app.quotas.daily import DailyQuotaService
from app.quotas.rate_limit import rate_limiter

def get_request_id(
    request: Request,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
) -> str:
    req_id = x_request_id.strip() if x_request_id and x_request_id.strip() else f"req_{uuid.uuid4().hex[:16]}"
    request.state.request_id = req_id
    return req_id

async def enforce_generation_quotas(
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
) -> AuthContext:
    """
    Enforces per-API-key rate limit (1 req/min) and per-user daily quota (30 tasks/day).
    Only applied to generation endpoints (chat completions and task creation).
    """
    # 1. Check rate limit
    await rate_limiter.check_and_record(auth.api_key.id)

    # 2. Check and consume daily task quota
    await DailyQuotaService.consume_quota(db, auth.user.id)

    return auth
