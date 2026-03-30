"""Audit and forensics models."""

from datetime import datetime

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    """A single audit log entry with HMAC integrity fields."""

    id: int
    agent_id: str
    user_id: str | None = None
    endpoint: str
    method: str
    decision: str
    cost_estimate_usd: float | None = None
    latency_ms: int | None = None
    request_metadata: dict = Field(default_factory=dict)
    entry_hash: str = Field(description="HMAC-SHA256 of this entry")
    prev_hash: str = Field(description="Hash of the preceding entry (GENESIS for first)")
    created_at: datetime


class AuditList(BaseModel):
    """Paginated list of audit log entries."""

    items: list[AuditEntry]
    total: int
    limit: int
    offset: int


class TopEndpoint(BaseModel):
    """An endpoint with its request count."""

    endpoint: str
    count: int


class AuditStats(BaseModel):
    """Aggregated audit statistics."""

    total_events: int
    allowed_count: int
    denied_count: int
    error_count: int
    total_cost_usd: float
    avg_latency_ms: float | None = None
    top_endpoints: list[TopEndpoint] = Field(default_factory=list)


class AuditChainVerification(BaseModel):
    """Result of audit chain integrity verification."""

    valid: bool = Field(description="True if the entire chain is intact")
    total_entries: int
    entries_verified: int
    first_broken_id: int | None = None
    message: str
