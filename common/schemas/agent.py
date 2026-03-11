"""Pydantic schemas for Agent CRUD operations."""

from datetime import datetime

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """Request body for creating a new agent."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    policies: dict = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Response body for agent details (no key hash exposed)."""

    id: int
    name: str
    description: str | None
    key_prefix: str
    capabilities: list[str]
    policies: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentCreateResponse(BaseModel):
    """Response body for agent creation — includes the plaintext key (show-once)."""

    agent: AgentResponse
    api_key: str = Field(..., description="Plaintext API key — only shown once at creation time")
