import aiosqlite
from fastapi import APIRouter, Depends
from app.auth.api_keys import ApiKeyService
from app.auth.dependencies import AuthContext, get_current_auth
from app.core.errors import InvalidRequestError
from app.db.database import get_db
from app.schemas.api_keys import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListItem,
    ApiKeyRevokeResponse,
)

router = APIRouter()

@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
) -> ApiKeyCreateResponse:
    """Generates a new API key for the authenticated user. The plaintext key is only shown once."""
    plain_key, api_key = await ApiKeyService.create_key_for_user(
        db=db,
        user_id=auth.user.id,
        label=payload.label,
    )
    return ApiKeyCreateResponse(
        id=api_key.id,
        key=plain_key,
        key_prefix=api_key.key_prefix,
        label=api_key.label,
        created_at=api_key.created_at,
    )

@router.get("/api-keys", response_model=list[ApiKeyListItem])
async def list_api_keys(
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
) -> list[ApiKeyListItem]:
    """Lists all API keys associated with the authenticated user."""
    keys = await ApiKeyService.list_keys(db, auth.user.id)
    return [
        ApiKeyListItem(
            id=k.id,
            key_prefix=k.key_prefix,
            label=k.label,
            created_at=k.created_at,
            revoked_at=k.revoked_at,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]

@router.delete("/api-keys/{key_id}", response_model=ApiKeyRevokeResponse)
async def revoke_api_key(
    key_id: str,
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
) -> ApiKeyRevokeResponse:
    """Revokes an API key."""
    success = await ApiKeyService.revoke_key(db, key_id, auth.user.id)
    if not success:
        raise InvalidRequestError("API key not found, already revoked, or access denied.")
    return ApiKeyRevokeResponse(id=key_id, revoked=True)
