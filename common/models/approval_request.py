"""ApprovalRequest model — human-in-the-loop review for sensitive agent actions.

Enterprise tier feature: when a policy includes `require_approval` patterns,
matching requests are paused until an admin approves or rejects them.
Unapproved requests auto-expire after a configurable timeout (fail-closed).
"""

import datetime
import enum
import uuid

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class ApprovalStatus(enum.StrEnum):
    """Lifecycle status for an approval request."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class ApprovalRequest(Base):
    """A paused gateway request awaiting human approval."""

    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Request context
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # What was requested
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    request_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ApprovalStatus.pending.value, index=True
    )

    # Reviewer info (populated on approve/reject)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Auto-expiry (fail-closed)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships — soft FK (no CASCADE, approvals survive agent deletion for audit)
    agent: Mapped["Agent"] = relationship(  # noqa: F821
        primaryjoin="Agent.id == foreign(ApprovalRequest.agent_id)",
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_approval_agent_status", "agent_id", "status"),
        Index("ix_approval_user_status", "user_id", "status"),
        Index("ix_approval_expires_pending", "expires_at", postgresql_where="status = 'pending'"),
    )
