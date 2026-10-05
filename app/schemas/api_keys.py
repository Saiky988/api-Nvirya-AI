from typing import Optional
from pydantic import BaseModel

class ApiKeyCreateRequest(BaseModel):
    label: Optional[str] = None
    username: Optional[str] = None

class ApiKeyCreateResponse(BaseModel):
    id: str
    key: str  # Plaintext key shown ONLY once
    key_prefix: str
    label: Optional[str] = None
    created_at: str

class ApiKeyListItem(BaseModel):
    id: str
    key_prefix: str
    label: Optional[str] = None
    created_at: str
    revoked_at: Optional[str] = None
    last_used_at: Optional[str] = None

class ApiKeyRevokeResponse(BaseModel):
    id: str
    revoked: bool
