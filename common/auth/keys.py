"""API key generation, hashing, and validation utilities."""

import hashlib
import secrets

from common.config.settings import settings


def generate_api_key() -> str:
    """Generate a new API key with the aid_sk_ prefix.

    Returns the full plaintext key (show-once pattern — only returned at creation time).
    """
    random_part = secrets.token_urlsafe(32)
    return f"{settings.api_key_prefix}{random_part}"


def hash_key(plaintext_key: str) -> str:
    """SHA-256 hash an API key for storage."""
    return hashlib.sha256(plaintext_key.encode()).hexdigest()


def get_key_prefix(plaintext_key: str, length: int = 12) -> str:
    """Extract a short prefix from a key for identification (e.g. 'aid_sk_abc1')."""
    return plaintext_key[:length]


def validate_key_format(key: str) -> bool:
    """Check that a key starts with the expected prefix."""
    return key.startswith(settings.api_key_prefix) or key.startswith(settings.admin_key_prefix)
