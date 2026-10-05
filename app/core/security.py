import hashlib
import hmac
import secrets

KEY_PREFIX = "nv-"

def generate_api_key() -> tuple[str, str, str]:
    """
    Generates a secure API key.
    Returns: (plain_key, key_hash, prefix)
    """
    token = secrets.token_hex(24)  # 48 characters
    plain_key = f"{KEY_PREFIX}{token}"
    key_hash = hash_api_key(plain_key)
    prefix = plain_key[:7]  # e.g. nv-abcd
    return plain_key, key_hash, prefix

def hash_api_key(key: str) -> str:
    """Hashes the plain API key using SHA-256."""
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()

def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Timing-safe comparison between plain key hash and stored hash."""
    computed_hash = hash_api_key(plain_key)
    return hmac.compare_digest(computed_hash, hashed_key)
