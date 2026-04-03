"""DismissedShadowAgent model — UI-state table for hiding shadow agents.

Stores user dismissals so shadow agents can be hidden from the default
dashboard view without affecting gateway behavior. Server-side storage
so dismissals persist across devices.
"""

import datetime
import uuid

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class DismissedShadowAgent(Base):
    """A dismissed shadow agent hidden from the default list view."""

    __tablename__ = "dismissed_shadow_agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "agent_id", name="uq_dismissed_user_agent"),
        Index("ix_dismissed_shadow_user_id", "user_id"),
    )
