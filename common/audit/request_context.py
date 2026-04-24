"""Extract audit-loggable context from a FastAPI Request.

Keeps router code DRY — every lifecycle audit site needs the same
``ip_address`` + ``user_agent`` pair, pulled the same way, with the
same proxy-aware IP resolution. Living in one helper means changing
the extraction policy (e.g. redacting to /24) is a one-file change.

See docs/specs/change-log-export-schema-v2.md §Source context for
how these fields land in the export.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request


# Cap user_agent at 256 chars to match the CSV writer's truncation.
# Longer headers exist in the wild (custom SDKs stacking versions) —
# trimming at ingress keeps DB + export sizes predictable.
_USER_AGENT_MAX_LEN = 256


def extract_audit_context(request: Request | None) -> dict[str, str]:
    """Return the source-context fields suitable for merging into
    ``AuditLog.request_metadata``.

    ``request`` is accepted as optional so background jobs and tests
    that don't have a Request in scope can call this uniformly — the
    result is an empty-valued dict and the audit writer handles that.

    IP resolution prefers ``X-Forwarded-For`` (first value) because
    production runs behind a GCP L7 load balancer that sets it; falls
    back to ``request.client.host`` for direct connections. Either
    way we end up with the client-observed address, not the proxy's.
    """
    if request is None:
        return {"ip_address": "", "user_agent": ""}

    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # X-Forwarded-For is comma-separated; the client is the first
        # hop. Anything after is an intermediary the client can't
        # control, so taking [0] is correct for the "who made this
        # request" question an auditor asks.
        ip_address = forwarded.split(",", 1)[0].strip()
    else:
        ip_address = request.client.host if request.client else ""

    user_agent = (request.headers.get("user-agent") or "")[:_USER_AGENT_MAX_LEN]

    return {"ip_address": ip_address, "user_agent": user_agent}
