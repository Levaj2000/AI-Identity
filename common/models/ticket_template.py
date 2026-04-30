"""Ticket template model for pre-configured support ticket scenarios."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from common.models.base import Base


class TicketTemplate(Base):
    """Pre-configured template for common ticket scenarios.

    Templates help users quickly create tickets for common issues
    like password resets, API problems, billing questions, etc.
    """

    __tablename__ = "ticket_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    subject_template = Column(String(255), nullable=False)
    body_template = Column(Text, nullable=False)
    default_priority = Column(String(20), nullable=False)
    default_category = Column(String(50))
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

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
    organization = relationship("Organization")
    created_by = relationship("User")

    def __repr__(self) -> str:
        return f"<TicketTemplate {self.name}>"


# Made with Bob
