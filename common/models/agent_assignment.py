"""Agent assignment — assigns users to specific agents with roles."""

import datetime
import enum
import uuid

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class AgentRole(enum.StrEnum):
    """Role for agent-level access."""

    owner = "owner"
    operator = "operator"
    viewer = "viewer"


class AgentAssignment(Base):
    """Assigns a user to a specific agent with a role."""

    __tablename__ = "agent_assignments"
    __table_args__ = (UniqueConstraint("agent_id", "user_id", name="uq_agent_assignment"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=AgentRole.viewer.value)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="assignments")  # noqa: F821
    user: Mapped["User"] = relationship()  # noqa: F821
