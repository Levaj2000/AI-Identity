"""Ada → AI Identity audit hook. The dogfood case-study moment.

Every Ada tool call routes through this module. Before the tool runs,
:func:`audit_action` POSTs to AI Identity's ``/gateway/enforce`` endpoint
with Ada's ``agent_id`` and a synthetic endpoint name encoding the tool
(``/ada/tools/{tool_name}``). The gateway evaluates Ada's policy and writes
an :class:`AuditLog` entry — the row is visible in the AI Identity dashboard
audit view, tagged with Ada's ``agent_id``.

If the gateway is unreachable or returns ``deny`` for the tool, the call
is short-circuited via the ADK ``before_tool_callback`` contract: the
callback returns an error dict, ADK presents that as the tool result, and
the user sees an explicit failure. *That* is the demo:

    "Ada's authority comes from AI Identity. Cut Ada off from AI Identity,
     or revoke her policy, and Ada stops working — every time, observably."

Phase 1 (this module):
- Synchronous gateway call per tool.
- ``raise AuditError`` on network / 5xx, returns an :class:`AuditDecision`
  on every other response (callers translate ``deny`` to an error result).
- Per-call ``X-Audit-Nonce`` UUID4 in headers, forward-compat with the
  planned backend nonce-replay check.
- Ada's runtime key sent in ``X-Agent-Key`` header for forward-compat
  with planned gateway auth.

Phase 2 (follow-up sprint):
- Backend nonce-replay check on the gateway side.
- Dedicated ``POST /api/v1/agents/{id}/actions`` endpoint that captures
  sanitized tool-arg metadata in the audit row.
- Gateway endpoint authentication (today the endpoint is open behind IP
  allowlist; Ada calls it directly).

Surfaced by Insight #74. Pairs with #325 (secret denylist) and #326
(serve.py auth + CORS) — together those three lock down the Ada surface
ahead of the Cloud Run deployment in #322.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from google.adk.tools import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class AuditError(Exception):
    """Audit hook could not be satisfied — gateway unreachable, 5xx, or misconfigured."""


@dataclass(frozen=True)
class AuditDecision:
    """Result of one ``/gateway/enforce`` call."""

    decision: str  # "allow" | "deny" | "error"
    status_code: int
    latency_ms: float
    nonce: str


def _gateway_url() -> str:
    return os.getenv("AI_IDENTITY_GATEWAY_URL", "https://gateway.ai-identity.co").rstrip("/")


def _agent_id() -> str:
    return os.getenv("ADA_AGENT_ID", "")


def _runtime_key() -> str:
    return os.getenv("AI_IDENTITY_API_KEY", "")


def _audit_required() -> bool:
    return os.getenv("ADA_REQUIRE_AUDIT", "0").lower() in ("1", "true", "yes")


def _timeout_s() -> float:
    return float(os.getenv("ADA_AUDIT_TIMEOUT_S", "5.0"))


def audit_action(tool_name: str) -> AuditDecision:
    """POST a synthetic enforce request to AI Identity's gateway.

    Returns :class:`AuditDecision` on any HTTP response (``allow``, ``deny``,
    ``error``). Raises :class:`AuditError` only when the gateway is
    unreachable or returns 5xx — i.e., when AI Identity itself is unhealthy.
    """
    agent_id = _agent_id()
    if not agent_id:
        raise AuditError("ADA_AGENT_ID is not set")

    nonce = str(uuid.uuid4())
    url = f"{_gateway_url()}/gateway/enforce"
    params = {
        "agent_id": agent_id,
        "endpoint": f"/ada/tools/{tool_name}",
        "method": "POST",
        "key_type": "runtime",
    }
    headers: dict[str, str] = {"X-Audit-Nonce": nonce}
    runtime_key = _runtime_key()
    if runtime_key:
        headers["X-Agent-Key"] = runtime_key

    start = time.monotonic()
    try:
        resp = httpx.post(url, params=params, headers=headers, timeout=_timeout_s())
    except httpx.RequestError as exc:
        latency = (time.monotonic() - start) * 1000
        logger.error(
            "ada.audit network error: tool=%s agent_id=%s nonce=%s err=%s latency_ms=%.2f",
            tool_name,
            agent_id,
            nonce,
            type(exc).__name__,
            latency,
        )
        raise AuditError(f"gateway unreachable: {type(exc).__name__}") from exc

    latency = (time.monotonic() - start) * 1000

    if resp.status_code >= 500:
        logger.error(
            "ada.audit 5xx: tool=%s agent_id=%s nonce=%s status=%s",
            tool_name,
            agent_id,
            nonce,
            resp.status_code,
        )
        raise AuditError(f"gateway 5xx: {resp.status_code}")

    try:
        body = resp.json()
        decision = body.get("decision", "error")
    except (ValueError, json.JSONDecodeError):
        decision = "error"

    logger.info(
        json.dumps(
            {
                "event": "ada.audit",
                "tool": tool_name,
                "agent_id": agent_id,
                "decision": decision,
                "status_code": resp.status_code,
                "latency_ms": round(latency, 2),
                "nonce": nonce,
            }
        )
    )

    return AuditDecision(
        decision=decision,
        status_code=resp.status_code,
        latency_ms=latency,
        nonce=nonce,
    )


def before_tool_audit_callback(
    tool: BaseTool,
    args: dict[str, Any],  # noqa: ARG001 - reserved for Phase 2 sanitized metadata
    tool_context: ToolContext,  # noqa: ARG001
) -> dict | None:
    """ADK ``before_tool_callback``: audit each tool call before it runs.

    Returns ``None`` on allow → ADK lets the tool run.
    Returns an error dict on audit-required-but-failed → ADK uses the dict
    as the tool result, the user sees an explicit failure.

    Behavior is gated on ``ADA_REQUIRE_AUDIT=1`` so the local launcher (no
    gateway, no agent_id) keeps working unchanged.
    """
    if not _audit_required():
        return None

    try:
        decision = audit_action(tool.name)
    except AuditError as exc:
        # Synchronous-enough that a dependency outage is visible.
        return {
            "status": "error",
            "error_message": (
                f"Ada audit failed for tool '{tool.name}': {exc}. "
                "AI Identity is unreachable; tool call aborted."
            ),
        }

    if decision.decision == "deny":
        return {
            "status": "error",
            "error_message": (
                f"Ada audit denied tool '{tool.name}' (status={decision.status_code}). "
                "Update Ada's AI Identity policy to allow /ada/tools/* endpoints."
            ),
        }

    return None


def after_tool_audit_callback(
    tool: BaseTool,
    args: dict[str, Any],  # noqa: ARG001
    tool_context: ToolContext,  # noqa: ARG001
    tool_response: dict,
) -> dict | None:
    """ADK ``after_tool_callback``: emit a structured completion log.

    Does not call the gateway again — the before-callback already produced
    the audit row. This emits a local structured log so ops can correlate
    tool latency, success/error, and result shape with the audit row by
    nonce or correlation_id.

    Returns ``None`` so ADK uses the tool's original response unchanged.
    """
    if not _audit_required():
        return None

    status = tool_response.get("status") if isinstance(tool_response, dict) else "unknown"
    logger.info(
        json.dumps(
            {
                "event": "ada.audit.complete",
                "tool": tool.name,
                "agent_id": _agent_id(),
                "result_status": status,
            }
        )
    )
    return None
