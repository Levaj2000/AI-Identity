"""Correlation ID plumbing for end-to-end request tracing.

One UUID travels the whole request: client → API → gateway → DB → audit row.
It lets operators reconstruct a single user action across services without
guessing at timestamps.

Two forms coexist:

  * ``correlation_id``  — full UUID4 (36 chars). Stored on audit rows,
    returned in the ``X-Correlation-ID`` response header, queryable via
    the audit API. Use this for cross-service tracing.
  * ``request_id``      — first 8 hex chars. Log-friendly shorthand used
    in structured log records for scan-readability.

Both are derived from the same UUID so they always agree. The middleware
sets a contextvar so downstream code (e.g. ``create_audit_entry``) can
auto-resolve without a Request object in scope.

Incoming headers — we accept either header for interop with existing
clients; ``X-Correlation-ID`` wins if both are present:

  * ``X-Correlation-ID`` (preferred, full UUID)
  * ``X-Request-ID``     (legacy, any format up to 64 chars)
"""

from __future__ import annotations

import contextvars
import uuid

# The one correlation ID in scope for the current request/task.
# FastAPI middleware sets it; create_audit_entry reads it.
_current_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "ai_identity_correlation_id", default=None
)

# Max length enforced at the DB column level.
CORRELATION_ID_MAX_LEN = 64


def generate_correlation_id() -> str:
    """Generate a fresh correlation ID (full UUID4)."""
    return str(uuid.uuid4())


def resolve_correlation_id(
    header_x_correlation_id: str | None,
    header_x_request_id: str | None,
) -> str:
    """Pick the correlation ID to use for this request.

    Order of preference:
      1. ``X-Correlation-ID`` header (if non-empty and within length limits)
      2. ``X-Request-ID`` header (legacy, same constraints)
      3. Freshly generated UUID4

    Values longer than ``CORRELATION_ID_MAX_LEN`` are ignored to prevent
    clients from padding huge strings into the audit index.
    """
    for candidate in (header_x_correlation_id, header_x_request_id):
        if candidate and 0 < len(candidate) <= CORRELATION_ID_MAX_LEN:
            return candidate
    return generate_correlation_id()


def to_short_id(correlation_id: str) -> str:
    """Return an 8-char log-friendly prefix for a correlation ID.

    For real UUIDs this is the first 8 hex chars; for arbitrary strings
    it's just the first 8 characters. Always safe to log — it's an
    identifier, not a secret.
    """
    return correlation_id[:8]


def set_current_correlation_id(correlation_id: str) -> contextvars.Token:
    """Set the per-request correlation ID. Called by the HTTP middleware.

    Returns the contextvars token; pass it to ``reset_current_correlation_id``
    to restore the previous value (e.g. at the end of the request).
    """
    return _current_correlation_id.set(correlation_id)


def reset_current_correlation_id(token: contextvars.Token) -> None:
    """Restore the previous correlation ID for this context."""
    _current_correlation_id.reset(token)


def get_current_correlation_id() -> str | None:
    """Return the correlation ID in scope for the current task, or None.

    Auto-resolved by ``create_audit_entry`` when a caller doesn't pass one
    explicitly. Outside of a request (background jobs, migrations, tests)
    this may be None — callers should either pass ``correlation_id=...``
    explicitly or accept that the audit row won't be cross-service-traceable.
    """
    return _current_correlation_id.get()
