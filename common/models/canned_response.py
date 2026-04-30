"""Canned response model for support ticket quick replies."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from common.models.base import Base


class CannedResponse(Base):
    """Pre-written response for common support questions.

    Canned responses are scoped to organizations and can be categorized
    for easy searching and filtering.
    """

    __tablename__ = "canned_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(50), index=True)
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

    __table_args__ = (Index("idx_canned_responses_org_category", "org_id", "category"),)

    def __repr__(self) -> str:
        return f"<CannedResponse {self.title}>"


# Made with Bob
