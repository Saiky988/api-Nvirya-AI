import uuid
from typing import Optional
import aiosqlite
from app.auth.hashing import generate_api_key, hash_api_key
from app.db.models import ApiKey, User
from app.db.repositories import ApiKeyRepository, UserRepository

class ApiKeyService:
    @staticmethod
    async def create_key_for_user(
        db: aiosqlite.Connection,
        user_id: str,
        label: Optional[str] = None,
    ) -> tuple[str, ApiKey]:
        key_id = f"key_{uuid.uuid4().hex[:16]}"
        plain_key, key_hash, prefix = generate_api_key()
        api_key = await ApiKeyRepository.create_api_key(
            db=db,
            key_id=key_id,
            key_hash=key_hash,
            key_prefix=prefix,
            user_id=user_id,
            label=label,
        )
        return plain_key, api_key

    @staticmethod
    async def authenticate_key(
        db: aiosqlite.Connection,
        plain_key: str,
    ) -> Optional[tuple[User, ApiKey]]:
        if not plain_key or not plain_key.strip():
            return None
        key_hash = hash_api_key(plain_key.strip())
        api_key = await ApiKeyRepository.get_by_hash(db, key_hash)
        if not api_key:
            return None
        if api_key.revoked_at is not None:
            return None
        user = await UserRepository.get_user_by_id(db, api_key.user_id)
        if not user:
            return None
        await ApiKeyRepository.update_last_used(db, api_key.id)
        return user, api_key

    @staticmethod
    async def list_keys(db: aiosqlite.Connection, user_id: str) -> list[ApiKey]:
        return await ApiKeyRepository.list_by_user(db, user_id)

    @staticmethod
    async def revoke_key(db: aiosqlite.Connection, key_id: str, user_id: str) -> bool:
        return await ApiKeyRepository.revoke(db, key_id, user_id)
