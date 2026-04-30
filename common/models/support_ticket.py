"""Support ticket models for customer support system."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from common.models.base import Base


class TicketPriority(StrEnum):
    """Ticket priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(StrEnum):
    """Ticket lifecycle status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCategory(StrEnum):
    """Ticket category for classification."""

    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    BUG = "bug"
    OTHER = "other"


class SupportTicket(Base):
    """Support ticket for customer issues and requests.

    Tickets are scoped to users and organizations, with optional
    links to specific agents and audit logs for context.
    """

    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number = Column(String(20), unique=True, nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        index=True,
    )

    # Ticket content
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default=TicketPriority.MEDIUM, index=True)
    status = Column(String(20), nullable=False, default=TicketStatus.OPEN, index=True)
    category = Column(String(50))

    # Context linking
    related_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
    )
    related_audit_log_ids = Column(JSONB, default=list)

    # Assignment
    assigned_to_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    # Additional metadata (renamed to avoid conflict with SQLAlchemy's metadata)
    ticket_metadata = Column(JSONB, default=dict)

    # SLA tracking
    sla_due_at = Column(DateTime(timezone=True), index=True)
    sla_breached = Column(Boolean, default=False, nullable=False)
    escalation_count = Column(Integer, default=0, nullable=False)
    original_sla_due_at = Column(
        DateTime(timezone=True)
    )  # Captured on first breach for accurate hours_overdue

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    resolved_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="support_tickets")
    organization = relationship("Organization", back_populates="support_tickets")
    related_agent = relationship("Agent")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    comments = relationship(
        "TicketComment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at",
    )

    __table_args__ = (
        Index("idx_tickets_user_org", "user_id", "org_id"),
        Index("idx_tickets_status_priority", "status", "priority"),
    )

    def __repr__(self) -> str:
        return f"<SupportTicket {self.ticket_number} status={self.status}>"


class TicketComment(Base):
    """Comment on a support ticket.

    Comments can be customer-visible or internal (admin-only).
    """

    __tablename__ = "ticket_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Comment content
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False, nullable=False)

    # Attachments (future enhancement)
    attachments = Column(JSONB, default=list)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    ticket = relationship("SupportTicket", back_populates="comments")
    user = relationship("User")

    __table_args__ = (Index("idx_comments_ticket_created", "ticket_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<TicketComment ticket={self.ticket_id} internal={self.is_internal}>"


# Made with Bob
