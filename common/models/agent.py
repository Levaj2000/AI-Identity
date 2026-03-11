"""Agent model — core identity entity for AI agents."""

import datetime
import enum
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class AgentStatus(str, enum.Enum):
    """Agent lifecycle status."""

    active = "active"
    suspended = "suspended"
    revoked = "revoked"


class Agent(Base):
    """An AI agent with its own identity, permissions, and guardrails."""

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AgentStatus.active.value, index=True
    )

    # Flexible metadata
    capabilities: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

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

    # Relationships
    user: Mapped["User"] = relationship(back_populates="agents")  # noqa: F821
    keys: Mapped[list["AgentKey"]] = relationship(back_populates="agent", cascade="all, delete-orphan")  # noqa: F821
    policies: Mapped[list["Policy"]] = relationship(back_populates="agent", cascade="all, delete-orphan")  # noqa: F821
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # noqa: F821
        back_populates="agent",
        primaryjoin="Agent.id == foreign(AuditLog.agent_id)",
    )
