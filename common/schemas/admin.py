"""Admin API schemas — platform stats, user management, system health."""

import datetime
import enum

from pydantic import BaseModel


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


# ── Agent Management ─────────────────────────────────────────────


class AdminAgentSummary(BaseModel):
    """Single agent row in the admin agent list."""

    id: str
    name: str
    status: str
    owner_email: str | None
    key_count: int
    created_at: datetime.datetime | None

    model_config = {"from_attributes": True}


class AdminAgentListResponse(BaseModel):
    """Paginated list of agents for admin view."""

    items: list[AdminAgentSummary]
    total: int
    limit: int
    offset: int


class AdminPurgeResponse(BaseModel):
    """Result of purging revoked agents."""

    purged_count: int
    agent_names: list[str]


# ── User Detail (admin drill-down) ─────────────────────────────


class AdminUserAgent(BaseModel):
    """Agent summary within a user detail view."""

    id: str
    name: str
    status: str
    key_count: int
    created_at: datetime.datetime | None

    model_config = {"from_attributes": True}


class AdminUserAuditEntry(BaseModel):
    """Single audit log entry for a user detail view."""

    id: int
    agent_id: str
    agent_name: str | None = None
    endpoint: str
    method: str
    decision: str
    latency_ms: int | None = None
    created_at: datetime.datetime | None

    model_config = {"from_attributes": True}


class AdminUserDetail(BaseModel):
    """Full user profile for admin drill-down."""

    id: str
    email: str | None
    role: str | None
    tier: str
    requests_this_month: int
    agent_count: int
    has_subscription: bool
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    welcome_email_sent_at: datetime.datetime | None = None
    followup_email_sent_at: datetime.datetime | None = None
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None

    # Tier quota info
    quotas: dict[str, int]

    # Nested data
    agents: list[AdminUserAgent]
    recent_audit_logs: list[AdminUserAuditEntry]

    model_config = {"from_attributes": True}
