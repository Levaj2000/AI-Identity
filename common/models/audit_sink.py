"""AuditLogSink — per-org configuration for forwarding audit events externally.

One organization can have multiple sinks (e.g. prod-splunk + dr-splunk + slack-alerts).
The writer enqueues one outbox row per *active* sink for the org every time an
``audit_log`` row is inserted. A separate worker drains the outbox (see
``common/audit/outbox.py``).

Security notes
  * ``secret`` is used to HMAC-sign outgoing payloads; customers verify on receipt.
    Stored in cleartext for now — secret rotation is a Phase 2A.1 follow-up
    (issue #136). Fine for MVP because all DB access is tenant-scoped via RLS,
    but should move to a KMS-backed envelope encryption before this ships to
    any customer who treats it as a long-lived credential.
  * ``url`` MUST be https — enforced by Pydantic validator at the API layer,
    not at the DB layer (so an operator investigating data can SELECT it).
"""

from __future__ import annotations

import datetime  # noqa: TC003 — used by SQLAlchemy at mapper-config time
import enum
import uuid  # noqa: TC003 — used by SQLAlchemy at mapper-config time

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class SinkKind(enum.StrEnum):
    """Transport kind. Webhook is the only one in Phase 2A; Pub/Sub, Splunk HEC,
    Chronicle, and Datadog are tracked in issue #136 as follow-up transports.
    """

    webhook = "webhook"


class AuditLogSink(Base):
    """An external destination that an org wants audit events forwarded to."""

    __tablename__ = "audit_log_sinks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human label shown in the management UI. Not unique per org — orgs can
    # have two sinks with the same name if they really want (staging-1, staging-2).
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default=SinkKind.webhook.value)

    # Transport target. Shape is validated per-kind at the API layer.
    # For webhooks: an https:// URL.
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Per-sink HMAC secret. Hex-encoded 32 bytes (same shape as org.forensic_verify_key).
    # Customers use it to verify that incoming events really came from AI Identity
    # and weren't modified in flight.
    secret: Mapped[str] = mapped_column(String(128), nullable=False)

    # Opt-in toggle. Disabled sinks stay in the DB so historical outbox rows
    # keep their FK target, but no new events get enqueued for them.
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Optional filter — only forward events matching these criteria.
    # Keys recognized in v1:
    #   - decisions: list[str]       (e.g. ["deny", "error"])
    #   - action_types: list[str]    (e.g. ["key_rotated", "agent_revoked"])
    # Empty / null means "everything".
    # Kept as JSONB so we can add filter keys without a migration.
    filter_config: Mapped[dict] = mapped_column("filter", JSONB, nullable=False, default=dict)

    # Soft-delete marker. Deleting a sink with pending outbox rows requires
    # the ?force=true query param on the DELETE endpoint; short of that, we
    # flip this flag and keep the row around until the outbox drains.
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Circuit-breaker state — opens after too many consecutive delivery
    # failures, closes on the next success. Separate from ``enabled`` which
    # is operator-driven. Zero = closed (healthy).
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    circuit_opened_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Optional free-form description — for ops notes ("owned by Cisco SOC team").
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped[Organization] = relationship()  # noqa: F821

    __table_args__ = (
        # Fast "what sinks should receive this event" lookup in the writer.
        Index("ix_audit_log_sinks_org_enabled", "org_id", "enabled"),
    )
