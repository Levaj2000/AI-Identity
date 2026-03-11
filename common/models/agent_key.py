"""AgentKey model — API key storage with rotation support."""

import datetime
import enum
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class KeyStatus(enum.StrEnum):
    """API key lifecycle status."""

    active = "active"
    rotated = "rotated"
    revoked = "revoked"


class AgentKey(Base):
    """An API key issued to an agent — SHA-256 hashed, show-once pattern."""

    __tablename__ = "agent_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Key storage — only the hash is persisted, never the plaintext
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # First 8 chars for identification, e.g. "aid_sk_a"

    # Lifecycle
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=KeyStatus.active.value)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="keys")  # noqa: F821
