"""Shadow Agent Detection schemas — analytics on denied gateway requests."""

import datetime

from pydantic import BaseModel

# ── Summary & List ──────────────────────────────────────────────────


class TopEndpointHit(BaseModel):
    """Endpoint probed by a shadow agent."""

    endpoint: str
    method: str
    count: int


class ShadowEvent(BaseModel):
    """A single denied request from a shadow agent."""

    id: int
    endpoint: str
    method: str
    deny_reason: str
    request_metadata: dict
    created_at: datetime.datetime | None


class ShadowAgentSummary(BaseModel):
    """Detected shadow agent in the list view."""

    agent_id: str
    deny_reason: str
    hit_count: int
    first_seen: datetime.datetime
    last_seen: datetime.datetime
    top_endpoints: list[str]
    is_blocked: bool = False
    is_dismissed: bool = False


class ShadowAgentListResponse(BaseModel):
    """Paginated list of detected shadow agents."""

    items: list[ShadowAgentSummary]
    total: int
    total_hits: int
    limit: int
    offset: int


# ── Detail ──────────────────────────────────────────────────────────


class ShadowAgentDetail(BaseModel):
    """Full detail view for a single shadow agent."""

    agent_id: str
    deny_reason: str
    hit_count: int
    first_seen: datetime.datetime
    last_seen: datetime.datetime
    top_endpoints: list[TopEndpointHit]
    recent_events: list[ShadowEvent]
    is_blocked: bool = False
    blocked_at: datetime.datetime | None = None
    is_dismissed: bool = False


# ── Stats ───────────────────────────────────────────────────────────


class ShadowAgentStats(BaseModel):
    """Summary counts for stats cards."""

    total_shadow_agents: int
    total_shadow_hits: int
    agents_not_found: int
    agents_inactive: int
    agents_blocked: int = 0
    agents_dismissed: int = 0


# ── Action requests/responses ───────────────────────────────────────


class BlockAgentRequest(BaseModel):
    """Request body for blocking a shadow agent."""

    reason: str | None = None


class BlockAgentResponse(BaseModel):
    """Response after blocking a shadow agent."""

    agent_id: str
    blocked: bool
    blocked_at: datetime.datetime


class DismissResponse(BaseModel):
    """Response after dismissing a shadow agent."""

    agent_id: str
    dismissed: bool
