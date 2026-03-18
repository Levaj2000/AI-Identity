"""Admin API schemas — platform stats, user management, system health."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    import datetime


class AdminTierEnum(enum.StrEnum):
    """Tier values for admin tier update (avoids importing ORM model at runtime)."""

    free = "free"
    pro = "pro"
    enterprise = "enterprise"


# ── Platform Stats ───────────────────────────────────────────────────


class AdminStatsResponse(BaseModel):
    """Platform-wide statistics."""

    total_users: int
    total_agents: int
    total_active_agents: int
    total_requests: int
    users_by_tier: dict[str, int]
    agents_by_status: dict[str, int]


# ── User Management ─────────────────────────────────────────────────


class AdminUserSummary(BaseModel):
    """Single user row in the admin user list."""

    id: str
    email: str | None
    role: str | None
    tier: str
    requests_this_month: int
    agent_count: int
    has_subscription: bool
    stripe_customer_id: str | None = None
    created_at: datetime.datetime | None

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    """Paginated list of users for admin view."""

    items: list[AdminUserSummary]
    total: int
    limit: int
    offset: int


class AdminTierUpdate(BaseModel):
    """Request body for changing a user's tier."""

    tier: AdminTierEnum


# ── System Health ────────────────────────────────────────────────────


class AdminHealthResponse(BaseModel):
    """System health metrics for admin dashboard."""

    status: str
    db_latency_ms: float
    table_counts: dict[str, int]
