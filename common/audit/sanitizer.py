"""Audit metadata sanitizer — allowlist-only filtering with PII rejection.

SECURITY-CRITICAL: This module prevents PII and sensitive data from
reaching the audit_log table's request_metadata JSONB column.

Design principles:
  - ALLOWLIST-ONLY: only recognized metadata keys pass through.
  - PII-BLOCKED: known PII field names are explicitly rejected + logged.
  - BODY-BLOCKED: request/response body content is NEVER stored.
  - FAIL-SAFE: unknown keys are silently dropped, never stored.
"""

import logging
import re
from typing import Any

logger = logging.getLogger("ai_identity.audit.sanitizer")

# ── Allowlist ────────────────────────────────────────────────────────────
# ONLY these keys are permitted in request_metadata.
# Everything else is silently stripped before storage.

ALLOWED_METADATA_KEYS: frozenset[str] = frozenset(
    {
        # Correlation (propagated across Gateway → API for incident investigation)
        "request_id",
        # Decision context (set by gateway enforce.py)
        "deny_reason",
        "status_code",
        "key_type",
        # Performance metrics
        "latency_ms",
        "upstream_latency_ms",
        "token_count",
        # Cost tracking
        "cost_estimate_usd",
        "model",
        # Request classification
        "request_category",
        "policy_version",
        "circuit_breaker_state",
        # Management operations (set by agent/key CRUD endpoints)
        "action_type",
        "resource_type",
        "agent_name",
        "old_status",
        "new_status",
        "key_prefix",
        "keys_revoked",
        "grace_hours",
    }
)

# ── PII Blocklist ────────────────────────────────────────────────────────
# Field names that are known to carry PII. If ANY of these appear in the
# metadata, we log a WARNING (potential data leak attempt) and strip them.

PII_FIELD_BLOCKLIST: frozenset[str] = frozenset(
    {
        # Identity
        "email",
        "e_mail",
        "email_address",
        "name",
        "first_name",
        "last_name",
        "full_name",
        "username",
        "user_name",
        "phone",
        "phone_number",
        "mobile",
        "telephone",
        "ssn",
        "social_security",
        "national_id",
        "passport",
        "passport_number",
        "date_of_birth",
        "dob",
        "birthday",
        # Network / tracking
        "ip",
        "ip_address",
        "client_ip",
        "remote_addr",
        "x_forwarded_for",
        "user_agent",
        "ua",
        "referer",
        "referrer",
        # Auth / secrets
        "authorization",
        "auth_token",
        "bearer",
        "token",
        "api_key",
        "secret",
        "password",
        "credential",
        "credentials",
        "cookie",
        "cookies",
        "session_id",
        "session_token",
        "access_token",
        "refresh_token",
        "id_token",
        "jwt",
        # Request/response bodies (NEVER log these)
        "body",
        "request_body",
        "response_body",
        "payload",
        "request_payload",
        "response_payload",
        "content",
        "request_content",
        "response_content",
        "data",
        "request_data",
        "response_data",
        "raw",
        "raw_request",
        "raw_response",
        "headers",
        "request_headers",
        "response_headers",
        # Financial
        "credit_card",
        "card_number",
        "cvv",
        "expiry",
        "bank_account",
        "routing_number",
        "iban",
        "swift",
        # Medical
        "diagnosis",
        "prescription",
        "medical_record",
    }
)

# Patterns that suggest PII even if the key name isn't in the blocklist.
# NOTE: Patterns are intentionally specific to avoid false positives on
# legitimate metrics fields like "token_count" or "header_size".
_PII_PATTERNS = [
    re.compile(r".*(?:email|phone|ssn|passport|ip_addr|password|secret).*", re.IGNORECASE),
    # Match "token" only in auth/credential contexts, not metrics
    re.compile(
        r".*(?:auth_token|access_token|refresh_token|bearer_token|id_token|session_token|api_token).*",
        re.IGNORECASE,
    ),
    # Match body/header only as field containers, not metrics
    re.compile(
        r".*(?:request_body|response_body|request_header|response_header|raw_body|raw_header).*",
        re.IGNORECASE,
    ),
]

# Maximum size for any single metadata value (prevent oversized entries)
MAX_METADATA_VALUE_LENGTH = 500

# Maximum total metadata keys
MAX_METADATA_KEYS = 20


# ── Core Sanitizer ───────────────────────────────────────────────────────


def is_pii_field(key: str) -> bool:
    """Check if a field name is known or suspected PII.

    Checks both the explicit blocklist and pattern-based detection.
    """
    normalized = key.lower().strip()

    # Explicit blocklist
    if normalized in PII_FIELD_BLOCKLIST:
        return True

    # Pattern-based detection
    return any(pattern.match(normalized) for pattern in _PII_PATTERNS)


def sanitize_metadata(metadata: dict | None) -> dict:
    """Sanitize request_metadata before writing to the audit log.

    1. Strips all keys not in the allowlist
    2. Logs warnings for PII field attempts
    3. Truncates oversized values
    4. Returns a clean, safe metadata dict

    This function is idempotent — calling it twice gives the same result.
    """
    if metadata is None:
        return {}

    if not isinstance(metadata, dict):
        logger.warning(
            "Audit metadata must be a dict, got %s — dropping all metadata",
            type(metadata).__name__,
        )
        return {}

    clean: dict[str, Any] = {}
    dropped_keys: list[str] = []
    pii_keys: list[str] = []

    for key, value in metadata.items():
        # Check PII blocklist FIRST — log the attempt
        if is_pii_field(key):
            pii_keys.append(key)
            continue

        # Check allowlist
        if key not in ALLOWED_METADATA_KEYS:
            dropped_keys.append(key)
            continue

        # Truncate oversized string values
        if isinstance(value, str) and len(value) > MAX_METADATA_VALUE_LENGTH:
            value = value[:MAX_METADATA_VALUE_LENGTH] + "…[truncated]"

        # Only store simple types (str, int, float, bool, None)
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean[key] = value
        else:
            # Complex types (lists, dicts, etc.) are not permitted
            dropped_keys.append(key)

    # Enforce max keys
    if len(clean) > MAX_METADATA_KEYS:
        excess = sorted(clean.keys())[MAX_METADATA_KEYS:]
        for key in excess:
            del clean[key]
        logger.warning(
            "Audit metadata exceeded %d keys — dropped: %s",
            MAX_METADATA_KEYS,
            excess,
        )

    # Log PII attempts (security event — someone tried to log PII)
    if pii_keys:
        logger.warning(
            "SECURITY: PII fields blocked from audit log: %s",
            sorted(pii_keys),
        )

    # Log dropped keys at debug level (expected for ad-hoc metadata)
    if dropped_keys:
        logger.debug(
            "Audit metadata keys dropped (not in allowlist): %s",
            sorted(dropped_keys),
        )

    return clean
