"""Audit log utilities — append-only writer with HMAC integrity chain."""

from common.audit.writer import (
    ChainVerificationResult,
    compute_entry_hash,
    create_audit_entry,
    verify_chain,
)

__all__ = [
    "ChainVerificationResult",
    "compute_entry_hash",
    "create_audit_entry",
    "verify_chain",
]
