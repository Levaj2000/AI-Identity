"""Ticket attachment model for file uploads."""

import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID

from common.models import Base


class TicketAttachment(Base):
    """File attachment for support tickets or comments.

    Attachments are stored in a storage backend (local disk or GCS) and
    metadata is tracked in this table. Supports soft delete for GDPR
    compliance and forensic retention.

    Storage path structure:
        {org_id}/ticket-attachments/{ticket_id}/{attachment_id}_{filename}
        {org_id}/comment-attachments/{comment_id}/{attachment_id}_{filename}
    """

    __tablename__ = "ticket_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parent relationships
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ticket_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Ownership and tenant isolation
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Nullable to preserve attachment when user deleted
        index=True,
    )
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File metadata
    filename = Column(String(255), nullable=False)  # Sanitized for storage
    original_filename = Column(String(255), nullable=False)  # Original for display
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False)  # Integrity verification

    # Storage location
    storage_path = Column(String(500), nullable=False, unique=True)

    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Indexes for common queries
    __table_args__ = (
        Index("ix_ticket_attachments_ticket_created", "ticket_id", "created_at"),
        Index("ix_ticket_attachments_org_created", "org_id", "created_at"),
        Index("ix_ticket_attachments_deleted", "deleted_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<TicketAttachment(id={self.id}, "
            f"ticket_id={self.ticket_id}, "
            f"filename={self.original_filename})>"
        )


# Made with Bob
