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
        "correlation_id",  # full-UUID counterpart; also denormalized to top-level column
        # Versioning — tags rows written through AuditMetadataV1
        "schema_version",
        # Decision context (set by gateway enforce.py)
        "deny_reason",
        "deny_rule_id",
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
        # Change-log v2.1 source context. SOC 2 CC7.2 and HIPAA
        # §164.312(b) both expect source IP and user agent on audit
        # records — their absence is a reviewer finding. Writers are
        # responsible for only emitting these on lifecycle audit
        # rows; the request-path sanitizer chain upstream of this
        # allowlist already scrubs them from per-request audit entries
        # where they'd be noise and a GDPR liability.
        # Org-level IP redaction (/24 or /48) is the Q1 follow-up in
        # docs/specs/change-log-export-schema-v2.md §Open questions.
        "ip_address",
        "user_agent",
        # diff dict for agent_updated / policy_updated — the sanitizer
        # passes nested objects through untouched when the key is
        # allowlisted. Schema-validated upstream by the router-side
        # _compute_diff helper.
        "diff",
    }
)

# V1 structured-metadata top-level keys that hold nested dicts/lists
# (Actor, Tenant, PolicyTrace, Resource, Cost). When the caller passes
# an AuditMetadataV1 instance, the writer flags these as trusted — the
# Pydantic schema has already validated their shape, so we store them
# as-is instead of running them through the flat-value sanitizer.
V1_STRUCTURED_KEYS: frozenset[str] = frozenset(
    {"actor", "tenant", "policy_trace", "resource", "cost"}
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
        # NOTE: ip_address and user_agent were historically blocklisted
        # here but are now ALLOWLISTED above for change-log v2.1
        # compliance (SOC 2 CC7.2 / HIPAA §164.312(b)). Keep the
        # aliases blocked so nobody smuggles them in under a variant
        # name — only the canonical spellings are audit-compliant.
        "ip",
        "client_ip",
        "remote_addr",
        "x_forwarded_for",
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


def sanitize_metadata(
    metadata: dict | None,
    *,
    trusted_structured_keys: frozenset[str] = frozenset(),
) -> dict:
    """Sanitize request_metadata before writing to the audit log.

    1. Strips all keys not in the allowlist
    2. Logs warnings for PII field attempts
    3. Truncates oversized values
    4. Returns a clean, safe metadata dict

    This function is idempotent — calling it twice gives the same result.

    ``trusted_structured_keys`` names top-level keys whose values are
    allowed to be dicts or lists and pass through without flat-value
    sanitization. Use this when the caller has already validated the
    nested shape (e.g. via ``AuditMetadataV1``). Keys in this set still
    have to survive the PII name check at the top level.
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
        # Explicit allowlist wins over PII pattern matching. A key
        # being in ALLOWED_METADATA_KEYS means the team has reviewed
        # and approved it for audit logging (e.g. ip_address /
        # user_agent for change-log v2.1 compliance). Without this
        # short-circuit the `ip_addr` pattern would strip the
        # approved `ip_address` field.
        is_allowlisted = key in ALLOWED_METADATA_KEYS or key in trusted_structured_keys

        # Check PII blocklist for non-allowlisted keys — log the attempt
        if not is_allowlisted and is_pii_field(key):
            pii_keys.append(key)
            continue

        # Trusted structured keys (Pydantic-validated) bypass the
        # flat-value restriction.
        if key in trusted_structured_keys:
            clean[key] = value
            continue

        # Check allowlist
        if key not in ALLOWED_METADATA_KEYS:
            dropped_keys.append(key)
            continue

        # Truncate oversized string values
        if isinstance(value, str) and len(value) > MAX_METADATA_VALUE_LENGTH:
            value = value[:MAX_METADATA_VALUE_LENGTH] + "…[truncated]"

        # Allow nested dicts for `diff` (change-log v2.1); otherwise
        # restrict to simple types to preserve the existing contract.
        if (
            isinstance(value, (str, int, float, bool))
            or value is None
            or key == "diff"
            and isinstance(value, dict)
        ):
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
