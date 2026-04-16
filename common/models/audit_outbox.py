"""AuditLogOutbox — delivery queue for forwarding audit events to external sinks.

One row per (audit_log_id, sink_id) pair, created in the same transaction as
the audit_log insert. A worker (``common/audit/outbox.flush_outbox``) claims
pending rows with ``FOR UPDATE SKIP LOCKED``, batches by sink, pushes through
the sink's transport, and updates status.

Lifecycle
  pending ─delivery ok──▶ delivered (terminal, garbage-collected after 7d)
     │
     └─delivery fails──▶ failed (retried with exponential backoff)
                            │
                            └─attempts >= max──▶ dead_letter (terminal,
                                                 needs operator intervention)
"""

from __future__ import annotations

import datetime  # noqa: TC003 — used by SQLAlchemy at mapper-config time
import enum
import uuid  # noqa: TC003 — used by SQLAlchemy at mapper-config time

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class OutboxStatus(enum.StrEnum):
    """Delivery state for a single (audit_log, sink) pair."""

    pending = "pending"
    delivered = "delivered"
    failed = "failed"  # transient — will be retried
    dead_letter = "dead_letter"  # terminal failure — needs operator action


class AuditLogOutbox(Base):
    """One pending / completed delivery of an audit event to a sink."""

    __tablename__ = "audit_log_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_log_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("audit_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sink_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # RESTRICT so an operator can't accidentally delete a sink that still
        # has pending deliveries without going through the force-delete path.
        ForeignKey("audit_log_sinks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=OutboxStatus.pending.value,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # When is this row eligible for the next delivery attempt? Set to
    # created_at initially, then bumped by the retry-backoff schedule on each
    # failure. The worker filters with ``next_attempt_at <= now()``.
    next_attempt_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_attempt_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Truncated, URL-scrubbed error detail from the last failure. Safe to log.
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    audit_log: Mapped[AuditLog] = relationship(  # noqa: F821
        primaryjoin="AuditLog.id == foreign(AuditLogOutbox.audit_log_id)",
    )
    sink: Mapped[AuditLogSink] = relationship()  # noqa: F821

    __table_args__ = (
        # Primary worker query: "pending / failed rows whose next_attempt_at
        # is due, ordered by id for FIFO-ish delivery".
        Index(
            "ix_audit_log_outbox_due",
            "status",
            "next_attempt_at",
        ),
        # Per-sink visibility for ops / health endpoints.
        Index("ix_audit_log_outbox_sink_status", "sink_id", "status"),
    )
