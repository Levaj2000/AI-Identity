"""AuditLog model — immutable record of every gateway decision."""

import datetime
import uuid

from sqlalchemy import DateTime, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class AuditLog(Base):
    """An immutable log entry for every request the gateway processes."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Request details
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)

    # Decision
    decision: Mapped[str] = mapped_column(String(10), nullable=False)  # allow, deny, error

    # Metrics
    cost_estimate_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Flexible request context
    request_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Timestamp
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships — soft FK (no CASCADE, audit logs survive agent deletion)
    agent: Mapped["Agent"] = relationship(  # noqa: F821
        back_populates="audit_logs",
        primaryjoin="Agent.id == foreign(AuditLog.agent_id)",
    )

    # Composite index for query performance: filter by agent + time range
    __table_args__ = (Index("ix_audit_log_agent_created", "agent_id", "created_at"),)
