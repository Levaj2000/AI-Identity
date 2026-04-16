"""Transport protocol — how a batch of audit events reaches an external sink.

Each ``SinkKind`` binds to one ``Transport`` implementation (webhook → WebhookTransport).
Additional transports (Pub/Sub, Splunk HEC, Chronicle, Datadog) land in this
package as separate modules — see issue #136.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class DeliveryResult:
    """Outcome of a single transport call.

    Per-event results aren't tracked in the MVP — a batch either succeeds or
    fails as a unit. Partial-success semantics are a follow-up (#136).
    """

    success: bool
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None


class Transport(Protocol):
    """Push a batch of audit event payloads to an external sink.

    Implementations MUST be idempotent from the receiver's perspective when
    possible (e.g. include event IDs in the payload so a re-delivered batch
    can be deduplicated downstream).
    """

    def deliver(
        self,
        *,
        events: list[dict[str, Any]],
        url: str,
        secret: str,
    ) -> DeliveryResult:
        """Send ``events`` to ``url``, signed with ``secret``.

        Never raises on network / transport errors — returns a DeliveryResult
        with ``success=False`` and a safe-to-log ``error``. Only raises on
        misuse (empty event list, invalid URL shape, etc.).
        """
        ...


# ── Transport registry ───────────────────────────────────────────────
# Maps SinkKind → concrete Transport instance. Imported at boot by the
# outbox worker; new transports register themselves here.

from common.audit.transports.webhook import WebhookTransport  # noqa: E402

TRANSPORTS: dict[str, Transport] = {
    "webhook": WebhookTransport(),
}


__all__ = ["DeliveryResult", "Transport", "TRANSPORTS", "WebhookTransport"]
