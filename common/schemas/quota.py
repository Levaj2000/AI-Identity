"""Pydantic schemas for quota and usage endpoints."""

import datetime

from pydantic import BaseModel, Field


class QuotaUsage(BaseModel):
    """Usage of a single resource against its quota limit."""

    current: int = Field(description="Current usage count")
    limit: int | None = Field(description="Maximum allowed (null = unlimited)")
    unlimited: bool = Field(description="Whether this resource is unlimited")
    percentage: float = Field(description="Usage percentage (0.0 if unlimited)")


class UsageSummaryResponse(BaseModel):
    """Complete usage summary for a user's account."""

    tier: str = Field(description="Current subscription tier: free, pro, business, enterprise")
    agents: QuotaUsage
    active_keys: QuotaUsage
    credentials: QuotaUsage
    requests_this_month: QuotaUsage
    audit_retention_days: int = Field(description="Audit log retention in days (-1 = unlimited)")


class TierInfoResponse(BaseModel):
    """Information about a subscription tier and its limits."""

    name: str
    max_agents: int = Field(description="-1 = unlimited")
    max_keys_per_agent: int
    max_requests_per_month: int
    max_credentials: int
    audit_retention_days: int


class TierListResponse(BaseModel):
    """All available subscription tiers."""

    tiers: list[TierInfoResponse]
    current_tier: str


# ── Usage Aggregation Schemas ────────────────────────────────────────


class DailyUsagePoint(BaseModel):
    """A single day's usage data."""

    date: str = Field(description="Date in YYYY-MM-DD format")
    total_requests: int = Field(description="Total gateway requests")
    allowed: int = Field(description="Requests allowed by policy")
    denied: int = Field(description="Requests denied by policy")
    errors: int = Field(description="Requests that hit errors")


class AgentUsageBreakdown(BaseModel):
    """Usage breakdown for a single agent."""

    agent_id: str = Field(description="Agent UUID")
    agent_name: str = Field(description="Agent display name")
    agent_status: str = Field(description="active, suspended, or revoked")
    total_requests: int
    allowed: int
    denied: int
    last_active: datetime.datetime | None = Field(description="Last request timestamp")


class BillingPeriodSummary(BaseModel):
    """Usage summary for a billing period."""

    period_start: str = Field(description="Period start date (YYYY-MM-DD)")
    period_end: str = Field(description="Period end date (YYYY-MM-DD)")
    total_requests: int
    allowed: int
    denied: int
    errors: int
    active_agents: int = Field(description="Agents with at least 1 request")
    peak_daily_requests: int = Field(description="Highest single-day request count")
    avg_daily_requests: float = Field(description="Average daily request count")


class UsageAggregationResponse(BaseModel):
    """Full usage aggregation with time-series, per-agent breakdown, and billing summary."""

    tier: str
    billing_period: BillingPeriodSummary
    previous_period: BillingPeriodSummary | None = Field(
        description="Previous billing period for comparison (null if no data)"
    )
    daily: list[DailyUsagePoint] = Field(description="Daily usage time series")
    by_agent: list[AgentUsageBreakdown] = Field(
        description="Per-agent usage breakdown, sorted by total_requests desc"
    )
