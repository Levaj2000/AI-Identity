"""Audit log utilities — append-only writer with HMAC integrity chain.

Includes metadata sanitization (allowlist-only, PII-blocked) and
opt-in debug logging with PII redaction and auto-expire.
"""

from common.audit.debug_log import (
    cleanup_expired_debug_logs,
    redact_dict,
    redact_pii,
    write_debug_entry,
)
from common.audit.sanitizer import (
    ALLOWED_METADATA_KEYS,
    PII_FIELD_BLOCKLIST,
    is_pii_field,
    sanitize_metadata,
)
from common.audit.writer import (
    ChainVerificationResult,
    compute_entry_hash,
    create_audit_entry,
    generate_report_signature,
    verify_chain,
    verify_report_signature,
)

__all__ = [
    "ALLOWED_METADATA_KEYS",
    "ChainVerificationResult",
    "PII_FIELD_BLOCKLIST",
    "cleanup_expired_debug_logs",
    "compute_entry_hash",
    "create_audit_entry",
    "generate_report_signature",
    "is_pii_field",
    "redact_dict",
    "redact_pii",
    "sanitize_metadata",
    "verify_chain",
    "verify_report_signature",
    "write_debug_entry",
]
