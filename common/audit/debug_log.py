"""Opt-in debug logging with PII redaction and 24hr auto-expire.

DISABLED by default. Enable via:
  AUDIT_DEBUG_LOGGING=true

When enabled, writes a separate debug log file with redacted request
context for operational troubleshooting. This is NOT the audit trail —
it's ephemeral debug data that auto-expires after AUDIT_DEBUG_TTL_HOURS.

PII redaction is applied BEFORE writing — even debug logs never contain
raw PII values.
"""

import logging
import re
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from common.config.settings import settings

logger = logging.getLogger("ai_identity.audit.debug")

# ── PII Redaction Patterns ──────────────────────────────────────────────

# Patterns to detect and redact common PII in string values
_REDACTION_PATTERNS = [
    # Email addresses
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[EMAIL_REDACTED]"),
    # Phone numbers (various formats)
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE_REDACTED]"),
    (re.compile(r"\+\d{1,3}[-.\s]?\d{3,14}"), "[PHONE_REDACTED]"),
    # SSN
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    # Credit card numbers (basic 16-digit patterns)
    (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "[CARD_REDACTED]"),
    # IP addresses (IPv4)
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[IP_REDACTED]"),
    # API keys (aid_sk_ and aid_admin_ prefixes)
    (re.compile(r"(aid_sk_|aid_admin_)[A-Za-z0-9_\-]+"), r"\g<1>[REDACTED]"),
    # Bearer tokens
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE), "Bearer [REDACTED]"),
    # JWT tokens (three base64 segments separated by dots)
    (re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"), "[JWT_REDACTED]"),
]

# Maximum value length in debug logs
_MAX_DEBUG_VALUE_LENGTH = 200


# ── PII Redaction ───────────────────────────────────────────────────────


def redact_pii(value: str) -> str:
    """Apply PII redaction patterns to a string value.

    Returns the string with all detected PII replaced by redaction tokens.
    Safe to call on any string — returns the original if no PII is found.
    """
    if not value or not isinstance(value, str):
        return value

    result = value
    for pattern, replacement in _REDACTION_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def redact_dict(data: dict) -> dict:
    """Recursively redact PII from all string values in a dict.

    Returns a new dict with all string values redacted. Non-string values
    are passed through as-is (truncated if necessary).
    """
    if not isinstance(data, dict):
        return {}

    clean: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            redacted = redact_pii(value)
            if len(redacted) > _MAX_DEBUG_VALUE_LENGTH:
                redacted = redacted[:_MAX_DEBUG_VALUE_LENGTH] + "…"
            clean[key] = redacted
        elif isinstance(value, dict):
            clean[key] = redact_dict(value)
        elif isinstance(value, list):
            clean[key] = [
                redact_pii(str(item)) if isinstance(item, str) else item
                for item in value[:10]  # Cap list length
            ]
        else:
            clean[key] = value
    return clean


# ── Debug Logger Setup ──────────────────────────────────────────────────

_debug_logger: logging.Logger | None = None


def _get_debug_logger() -> logging.Logger | None:
    """Get or initialize the debug audit logger.

    Returns None if debug logging is disabled.
    Uses TimedRotatingFileHandler with AUDIT_DEBUG_TTL_HOURS interval
    to auto-expire old debug logs.
    """
    global _debug_logger  # noqa: PLW0603

    if not settings.audit_debug_logging:
        return None

    if _debug_logger is not None:
        return _debug_logger

    # Create log directory
    log_dir = Path(settings.audit_debug_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set up rotating file handler — rotates every N hours, keeps 1 backup
    log_path = log_dir / "audit_debug.log"
    handler = TimedRotatingFileHandler(
        filename=str(log_path),
        when="H",
        interval=settings.audit_debug_ttl_hours,
        backupCount=1,  # Keep only 1 old file → ~2x TTL max
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )

    _debug_logger = logging.getLogger("ai_identity.audit.debug_file")
    _debug_logger.addHandler(handler)
    _debug_logger.setLevel(logging.DEBUG)
    _debug_logger.propagate = False  # Don't send to root logger

    return _debug_logger


def write_debug_entry(
    *,
    agent_id: str,
    endpoint: str,
    method: str,
    decision: str,
    raw_metadata: dict | None = None,
) -> None:
    """Write a PII-redacted debug log entry.

    This is opt-in and separate from the audit trail. It provides
    richer context for debugging while ensuring PII is never stored
    even in debug files.

    No-op if AUDIT_DEBUG_LOGGING is False.
    """
    debug_logger = _get_debug_logger()
    if debug_logger is None:
        return

    # Redact all metadata values
    clean_metadata = redact_dict(raw_metadata or {})

    debug_logger.info(
        "agent=%s endpoint=%s method=%s decision=%s metadata=%s",
        agent_id,
        endpoint,
        method,
        decision,
        clean_metadata,
    )


def cleanup_expired_debug_logs() -> int:
    """Manually clean up debug log files older than TTL.

    Returns the number of files removed.
    The TimedRotatingFileHandler handles most cleanup, but this can be
    called explicitly for immediate cleanup (e.g., from a cron job).
    """
    log_dir = Path(settings.audit_debug_log_dir)
    if not log_dir.exists():
        return 0

    ttl_seconds = settings.audit_debug_ttl_hours * 3600
    cutoff = time.time() - ttl_seconds
    removed = 0

    for log_file in log_dir.glob("audit_debug.log*"):
        try:
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                removed += 1
                logger.info("Removed expired debug log: %s", log_file.name)
        except OSError:
            logger.warning("Failed to remove expired debug log: %s", log_file.name)

    return removed
