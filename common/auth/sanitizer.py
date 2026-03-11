"""Key and credential sanitization — prevents secrets from leaking into logs, errors, or payloads.

Usage:
    from common.auth.sanitizer import sanitize

    sanitize("Token is aid_sk_abc123def456ghi789...")
    # → "Token is aid_sk_abc1********"

    sanitize("postgresql://user:s3cret@host/db")
    # → "postgresql://user:****@host/db"
"""

import re
from urllib.parse import urlparse, urlunparse

from common.config.settings import settings

# ── Patterns ─────────────────────────────────────────────────────────────

# Match aid_sk_ or aid_admin_ keys — prefix + at least 4 chars of the random part
_KEY_PATTERN = re.compile(
    r"(aid_sk_|aid_admin_)([A-Za-z0-9_\-]{4})[A-Za-z0-9_\-]+",
)

# Match hex strings that look like SHA-256 hashes (exactly 64 hex chars, word boundary)
_HASH_PATTERN = re.compile(
    r"\b([a-f0-9]{8})[a-f0-9]{56}\b",
)

# Match common secret env var patterns: KEY=value, SECRET=value, TOKEN=value, PASSWORD=value
_ENV_SECRET_PATTERN = re.compile(
    r"((?:API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY)\s*[=:]\s*)['\"]?(\S{8})\S+['\"]?",
    re.IGNORECASE,
)


# ── Core sanitizer ──────────────────────────────────────────────────────


def sanitize(text: str) -> str:
    """Sanitize a string by masking API keys, hashes, database URLs, and secrets.

    Handles:
    - Agent API keys (aid_sk_*, aid_admin_*) → prefix + 4 chars + ********
    - SHA-256 key hashes (64 hex chars) → first 8 chars + ********
    - Database URLs with passwords → password replaced with ****
    - Common secret patterns (API_KEY=..., SECRET=...) → first 8 chars + ********

    Safe to call on any string — returns the original if no secrets are found.
    """
    if not text:
        return text

    # 1. Mask agent API keys: aid_sk_abc1******** (keep prefix + 4 chars)
    result = _KEY_PATTERN.sub(r"\g<1>\g<2>********", text)

    # 2. Mask SHA-256 hashes: first 8 hex chars + ********
    result = _HASH_PATTERN.sub(r"\g<1>********", result)

    # 3. Mask database URLs
    result = sanitize_url(result)

    # 4. Mask env var secrets
    result = _ENV_SECRET_PATTERN.sub(r"\g<1>\g<2>********", result)

    return result


def sanitize_url(text: str) -> str:
    """Replace passwords in database/connection URLs.

    postgresql://user:s3cret@host:5432/db → postgresql://user:****@host:5432/db
    """

    def _mask_url(match: re.Match) -> str:
        url = match.group(0)
        try:
            parsed = urlparse(url)
            if parsed.password:
                masked = parsed._replace(
                    netloc=f"{parsed.username}:****@{parsed.hostname}"
                    + (f":{parsed.port}" if parsed.port else "")
                )
                return urlunparse(masked)
        except Exception:
            pass
        return url

    # Match common database/connection URL schemes
    return re.sub(
        r"(?:postgresql|postgres|mysql|redis|amqp|mongodb)://\S+",
        _mask_url,
        text,
    )


def mask_key(key: str) -> str:
    """Mask a single API key to its safe display form.

    aid_sk_abc123def456... → aid_sk_abc1********

    Use this when you have an isolated key string (not embedded in text).
    For strings that may contain keys, use sanitize() instead.
    """
    prefix = settings.api_key_prefix
    admin_prefix = settings.admin_key_prefix

    if key.startswith(prefix):
        safe_len = len(prefix) + 4
        return key[:safe_len] + "********"
    elif key.startswith(admin_prefix):
        safe_len = len(admin_prefix) + 4
        return key[:safe_len] + "********"
    else:
        # Unknown format — show first 8 chars only
        return key[:8] + "********" if len(key) > 8 else "********"
