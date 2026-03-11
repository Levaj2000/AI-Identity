"""Pydantic schemas for Agent CRUD operations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── User Schemas ─────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Request body for creating a new user."""

    email: str = Field(..., max_length=255)
    org_id: str | None = None
    role: str = "owner"


class UserResponse(BaseModel):
    """Response body for user details."""

    id: uuid.UUID
    email: str
    org_id: str | None
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Agent Schemas ────────────────────────────────────────────────────────


class AgentCreate(BaseModel):
    """Request body for creating a new agent."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    capabilities: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    """Request body for updating an agent. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    capabilities: list | None = None
    metadata: dict | None = None
    status: str | None = Field(None, pattern="^(active|suspended)$")


class AgentResponse(BaseModel):
    """Response body for a single agent."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    status: str
    capabilities: list
    metadata: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """Paginated list of agents."""

    items: list[AgentResponse]
    total: int
    limit: int
    offset: int


class AgentCreateResponse(BaseModel):
    """Response body for agent creation — includes the plaintext key (show-once)."""

    agent: AgentResponse
    api_key: str = Field(
        ..., description="Plaintext API key — only shown once at creation time"
    )


# ── Agent Key Schemas ────────────────────────────────────────────────────


class AgentKeyResponse(BaseModel):
    """Response body for an agent key (hash never exposed)."""

    id: int
    agent_id: uuid.UUID
    key_prefix: str
    status: str
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Policy Schemas ───────────────────────────────────────────────────────


class PolicyCreate(BaseModel):
    """Request body for creating a policy."""

    rules: dict = Field(default_factory=dict)


class PolicyResponse(BaseModel):
    """Response body for a policy."""

    id: int
    agent_id: uuid.UUID
    rules: dict
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Audit Log Schemas ────────────────────────────────────────────────────


class AuditLogResponse(BaseModel):
    """Response body for an audit log entry."""

    id: int
    agent_id: uuid.UUID
    endpoint: str
    method: str
    decision: str
    cost_estimate_usd: float | None
    latency_ms: int | None
    request_metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}
