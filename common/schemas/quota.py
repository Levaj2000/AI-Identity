"""Pydantic schemas for quota and usage endpoints."""

from pydantic import BaseModel, Field


class QuotaUsage(BaseModel):
    """Usage of a single resource against its quota limit."""

    current: int = Field(description="Current usage count")
    limit: int | None = Field(description="Maximum allowed (null = unlimited)")
    unlimited: bool = Field(description="Whether this resource is unlimited")
    percentage: float = Field(description="Usage percentage (0.0 if unlimited)")


class UsageSummaryResponse(BaseModel):
    """Complete usage summary for a user's account."""

    tier: str = Field(description="Current subscription tier: free, pro, enterprise")
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
