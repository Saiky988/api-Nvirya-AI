from dataclasses import dataclass
from typing import Optional
import aiosqlite
from fastapi import Depends, Header, Request
from app.auth.api_keys import ApiKeyService
from app.core.errors import AuthenticationError
from app.db.database import get_db
from app.db.models import ApiKey, User

@dataclass
class AuthContext:
    user: User
    api_key: ApiKey

async def get_api_key_from_headers(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
) -> str:
    if authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        # Fallback if raw token passed in Authorization header
        return parts[0].strip()
    if x_api_key:
        return x_api_key.strip()
    raise AuthenticationError("Missing API key. Provide via Bearer token or x-api-key header.")

async def get_current_auth(
    raw_key: str = Depends(get_api_key_from_headers),
    db: aiosqlite.Connection = Depends(get_db),
) -> AuthContext:
    auth_result = await ApiKeyService.authenticate_key(db, raw_key)
    if not auth_result:
        raise AuthenticationError("Invalid or revoked API key.")
    user, api_key = auth_result
    return AuthContext(user=user, api_key=api_key)
