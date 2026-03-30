"""Agent key models."""

from datetime import datetime

from pydantic import BaseModel, Field


class AgentKey(BaseModel):
    """Agent key metadata. The full key is never exposed after creation."""

    id: int
    agent_id: str
    key_prefix: str = Field(description="First 12 characters for identification")
    key_type: str = Field(description="runtime (aid_sk_) or admin (aid_admin_)")
    status: str = Field(description="active, rotated, or revoked")
    expires_at: datetime | None = None
    created_at: datetime


class AgentKeyCreateResponse(BaseModel):
    """Response for key creation — includes the show-once plaintext key."""

    key: AgentKey
    api_key: str = Field(description="Plaintext API key — shown only once")


class AgentKeyList(BaseModel):
    """List of agent keys."""

    items: list[AgentKey]
    total: int


class AgentKeyRotateResponse(BaseModel):
    """Response for key rotation. Old key enters 24-hour grace period."""

    new_key: AgentKey
    api_key: str = Field(description="Plaintext API key for the new key — shown only once")
    rotated_key: AgentKey = Field(description="Old key, now with status=rotated and 24hr expiry")
