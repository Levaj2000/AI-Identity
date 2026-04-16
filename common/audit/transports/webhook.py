"""HTTPS webhook transport — signed POST to a customer-supplied URL.

Payload shape (v1 envelope)
---------------------------

    {
      "version": 1,
      "delivered_at": "2026-04-15T12:34:56.789Z",
      "events": [
        { ...full AuditLog row as JSON... },
        ...
      ]
    }

Signing
-------

Every request carries ``X-AI-Identity-Signature: sha256=<hex>`` where ``<hex>``
is the HMAC-SHA256 of the *exact* request body using the sink's secret. The
receiver recomputes and compares in constant time. See ``_sign_body``.

Errors
------

Connection errors, 5xx, and any non-2xx response all count as delivery
failures and get returned as ``DeliveryResult(success=False, ...)``. The
outbox worker owns retry scheduling — this module is stateless.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from common.audit.transports import DeliveryResult

logger = logging.getLogger("ai_identity.audit.webhook")

ENVELOPE_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_ERROR_CHARS = 500
USER_AGENT = "ai-identity-audit-forwarder/1.0"


def _sign_body(body: bytes, secret: str) -> str:
    """HMAC-SHA256 of the raw body, hex-encoded, prefixed with ``sha256=``."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _build_envelope(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Construct the outer envelope wrapping a batch of events."""
    return {
        "version": ENVELOPE_VERSION,
        "delivered_at": datetime.now(UTC).isoformat(),
        "events": events,
    }


# Redact URL-shaped tokens (anything with a scheme://).
_URL_RE = re.compile(r"\S*://\S*")
# Redact "Bearer <token>" or "Authorization: <token>" style — consume the
# keyword and one or more following non-space tokens that look like a
# credential (hex / alphanumeric / punctuation blobs).
_AUTH_RE = re.compile(
    r"(?i)\b(?:bearer|authorization:?|token=|api[_-]?key=)\s*[\w\-\.=+/]+",
)


def _redact_error(raw: str) -> str:
    """Strip anything URL-like or token-like out of an error string.

    Best-effort — we don't want a transient "401 Bearer abc123" from the
    customer's auth proxy landing in our ``last_error`` column.
    """
    redacted = _URL_RE.sub("<url-redacted>", raw)
    redacted = _AUTH_RE.sub("<auth-redacted>", redacted)
    if len(redacted) > MAX_ERROR_CHARS:
        redacted = redacted[:MAX_ERROR_CHARS] + "…"
    return redacted


class WebhookTransport:
    """Transport that POSTs signed JSON to a customer URL via httpx."""

    def __init__(self, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

    def deliver(
        self,
        *,
        events: list[dict[str, Any]],
        url: str,
        secret: str,
    ) -> DeliveryResult:
        if not events:
            raise ValueError("webhook transport requires at least one event")
        if not url.startswith("https://"):
            raise ValueError("webhook url must start with https://")

        envelope = _build_envelope(events)
        body = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "X-AI-Identity-Signature": _sign_body(body, secret),
            "X-AI-Identity-Event-Count": str(len(events)),
        }

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, content=body, headers=headers)
        except httpx.HTTPError as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            error = _redact_error(f"{type(exc).__name__}: {exc}")
            logger.warning("webhook delivery failed: %s", error)
            return DeliveryResult(
                success=False,
                status_code=None,
                latency_ms=latency_ms,
                error=error,
            )

        latency_ms = int((time.perf_counter() - start) * 1000)

        if 200 <= response.status_code < 300:
            return DeliveryResult(
                success=True,
                status_code=response.status_code,
                latency_ms=latency_ms,
            )

        # Non-2xx — capture a small slice of body text for debugging.
        # Never log the request body (contains audit data).
        snippet = (response.text or "")[:200]
        return DeliveryResult(
            success=False,
            status_code=response.status_code,
            latency_ms=latency_ms,
            error=_redact_error(f"HTTP {response.status_code}: {snippet}"),
        )
