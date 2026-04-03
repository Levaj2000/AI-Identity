"""BlockedAgent model — explicitly blocked shadow agent IDs.

When a shadow agent is blocked, the gateway issues a hard deny with
deny_reason='agent_blocked' instead of 'agent_not_found'. This gives
operators a way to act on detected shadow agents.

Note: agent_id is VARCHAR, not a UUID FK, because shadow agent IDs are
user-supplied strings that may not exist in the agents table.
"""

import datetime
import uuid

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class BlockedAgent(Base):
    """An explicitly blocked shadow agent ID."""

    __tablename__ = "blocked_agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "agent_id", name="uq_blocked_user_agent"),
        Index("ix_blocked_agents_agent_id", "agent_id"),
        Index("ix_blocked_agents_user_id", "user_id"),
    )
