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
    """Request body for creating a new agent.

    Only `name` is required. Capabilities and metadata are optional and
    default to an empty list and empty dict respectively.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable name for the agent",
        examples=["Customer Support Bot"],
    )
    description: str | None = Field(
        None,
        description="Optional description of the agent's purpose",
        examples=["Handles tier-1 support tickets via chat"],
    )
    capabilities: list = Field(
        default_factory=list,
        description="Structured list of what the agent can do",
        examples=[["chat_completion", "function_calling"]],
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Freeform key-value pairs for filtering and grouping",
        examples=[{"framework": "langchain", "environment": "production"}],
    )


class AgentUpdate(BaseModel):
    """Request body for updating an agent. All fields are optional — only
    include the fields you want to change.
    """

    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="New name for the agent",
    )
    description: str | None = Field(
        None,
        description="New description",
    )
    capabilities: list | None = Field(
        None,
        description="Replace the agent's capabilities list",
        examples=[["chat_completion", "embeddings"]],
    )
    metadata: dict | None = Field(
        None,
        description="Replace the agent's metadata dict",
        examples=[{"environment": "staging", "owner_team": "platform"}],
    )
    status: str | None = Field(
        None,
        pattern="^(active|suspended)$",
        description="Set agent status (active or suspended). Use DELETE to revoke.",
    )


class AgentResponse(BaseModel):
    """Full agent details returned by GET, PUT, and DELETE endpoints."""

    id: uuid.UUID = Field(description="Unique agent identifier")
    user_id: uuid.UUID = Field(description="ID of the owning user")
    name: str = Field(description="Human-readable agent name")
    description: str | None = Field(description="Agent description")
    status: str = Field(description="Current status: active, suspended, or revoked")
    capabilities: list = Field(description="List of agent capabilities")
    metadata: dict = Field(description="Freeform key-value metadata")
    created_at: datetime = Field(description="When the agent was created")
    updated_at: datetime = Field(description="When the agent was last modified")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
                    "name": "Customer Support Bot",
                    "description": "Handles tier-1 support tickets",
                    "status": "active",
                    "capabilities": ["chat_completion", "function_calling"],
                    "metadata": {"framework": "langchain", "environment": "production"},
                    "created_at": "2026-03-10T12:00:00Z",
                    "updated_at": "2026-03-10T12:00:00Z",
                }
            ]
        },
    }


class AgentListResponse(BaseModel):
    """Paginated list of agents."""

    items: list[AgentResponse] = Field(description="List of agents")
    total: int = Field(description="Total number of matching agents")
    limit: int = Field(description="Maximum items per page")
    offset: int = Field(description="Number of items skipped")


class AgentCreateResponse(BaseModel):
    """Response for agent creation — includes the show-once plaintext API key.

    **Important:** The `api_key` field is only returned at creation time.
    Store it securely — it cannot be retrieved again.
    """

    agent: AgentResponse
    api_key: str = Field(
        ...,
        description="Plaintext API key (aid_sk_…) — shown only once at creation time",
        examples=["aid_sk_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"],
    )


# ── Agent Key Schemas ────────────────────────────────────────────────────


class AgentKeyResponse(BaseModel):
    """Agent key metadata. The full key and hash are never exposed."""

    id: int = Field(description="Key ID")
    agent_id: uuid.UUID = Field(description="Agent this key belongs to")
    key_prefix: str = Field(
        description="First 12 characters of the key for identification",
        examples=["aid_sk_a1b2"],
    )
    status: str = Field(
        description="Key status: active, rotated, or revoked",
        examples=["active"],
    )
    expires_at: datetime | None = Field(
        description="When the key expires (set during rotation grace period)",
    )
    created_at: datetime = Field(description="When the key was created")

    model_config = {"from_attributes": True}


class AgentKeyCreateResponse(BaseModel):
    """Response for key creation — includes the show-once plaintext key.

    **Important:** Store the `api_key` securely. It cannot be retrieved after
    this response.
    """

    key: AgentKeyResponse
    api_key: str = Field(
        ...,
        description="Plaintext API key (aid_sk_…) — shown only once",
        examples=["aid_sk_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"],
    )


class AgentKeyListResponse(BaseModel):
    """List of agent keys with prefix and status (never the full key)."""

    items: list[AgentKeyResponse] = Field(description="List of keys")
    total: int = Field(description="Total number of keys")


class AgentKeyRotateResponse(BaseModel):
    """Response for key rotation. The old key enters a 24-hour grace period
    (status=rotated) before being automatically revoked.
    """

    new_key: AgentKeyResponse = Field(description="The newly generated key")
    api_key: str = Field(
        ...,
        description="Plaintext API key for the new key — shown only once",
        examples=["aid_sk_f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8"],
    )
    rotated_key: AgentKeyResponse = Field(
        description="The old key, now with status=rotated and a 24hr expiry",
    )


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
