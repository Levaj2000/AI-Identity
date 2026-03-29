"""Organization model — teams of users who share agents."""

import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class Organization(Base):
    """An organization that groups users and their agents."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", use_alter=True),
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    requests_this_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_reset_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Stripe billing (org-level for business/enterprise)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])  # noqa: F821
    memberships: Mapped[list["OrgMembership"]] = relationship(  # noqa: F821
        back_populates="organization", cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship(  # noqa: F821
        back_populates="organization", foreign_keys="Agent.org_id"
    )
