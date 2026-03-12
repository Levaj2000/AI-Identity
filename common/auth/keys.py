"""API key generation, hashing, and validation utilities."""

import hashlib
import secrets

from common.config.settings import settings


def generate_api_key(key_type: str = "runtime") -> str:
    """Generate a new API key with the appropriate prefix.

    Args:
        key_type: "runtime" for aid_sk_ prefix, "admin" for aid_admin_ prefix.

    Returns the full plaintext key (show-once pattern — only returned at creation time).
    """
    prefix = _prefix_for_type(key_type)
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}{random_part}"


def hash_key(plaintext_key: str) -> str:
    """SHA-256 hash an API key for storage."""
    return hashlib.sha256(plaintext_key.encode()).hexdigest()


def get_key_prefix(plaintext_key: str, length: int = 12) -> str:
    """Extract a short prefix from a key for identification (e.g. 'aid_sk_abc1')."""
    return plaintext_key[:length]


def validate_key_format(key: str) -> bool:
    """Check that a key starts with the expected prefix."""
    return key.startswith(settings.api_key_prefix) or key.startswith(settings.admin_key_prefix)


def detect_key_type(key: str) -> str:
    """Detect key type from the prefix.

    Returns "admin" for aid_admin_* keys, "runtime" for aid_sk_* keys.

    Raises ValueError if the key prefix is unrecognized.
    """
    if key.startswith(settings.admin_key_prefix):
        return "admin"
    if key.startswith(settings.api_key_prefix):
        return "runtime"
    msg = f"Unrecognized key prefix: {key[:8]}..."
    raise ValueError(msg)


def _prefix_for_type(key_type: str) -> str:
    """Return the key prefix for a given key type."""
    if key_type == "admin":
        return settings.admin_key_prefix
    return settings.api_key_prefix
