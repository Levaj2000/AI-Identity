"""User model — account owners who manage agents."""

import datetime
import enum
import uuid

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class UserTier(enum.StrEnum):
    """Subscription tier for a user account."""

    free = "free"
    pro = "pro"
    enterprise = "enterprise"


# ── Per-tier quota defaults ──────────────────────────────────────────
# Aligned with landing page pricing:
#   Free: 3 agents, 5K req/mo, 1 credential
#   Pro:  25 agents, 100K req/mo, 10 credentials
#   Enterprise: unlimited (represented as -1)

TIER_QUOTAS: dict[str, dict[str, int]] = {
    "free": {
        "max_agents": 3,
        "max_keys_per_agent": 2,
        "max_requests_per_month": 5_000,
        "max_credentials": 1,
        "audit_retention_days": 7,
    },
    "pro": {
        "max_agents": 25,
        "max_keys_per_agent": 10,
        "max_requests_per_month": 100_000,
        "max_credentials": 10,
        "audit_retention_days": 90,
    },
    "enterprise": {
        "max_agents": -1,  # unlimited
        "max_keys_per_agent": -1,
        "max_requests_per_month": -1,
        "max_credentials": -1,
        "audit_retention_days": -1,  # unlimited
    },
}


class User(Base):
    """A user who owns and manages AI agents."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    org_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="owner")

    # Subscription tier + usage tracking
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free", index=True)
    requests_this_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_reset_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # Day of month to reset usage counter

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
    agents: Mapped[list["Agent"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def quotas(self) -> dict[str, int]:
        """Return the quota limits for this user's tier."""
        return TIER_QUOTAS.get(self.tier, TIER_QUOTAS["free"])
