"""Agent models."""

from datetime import datetime

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """Request body for creating a new agent."""

    name: str = Field(..., description="Human-readable name for the agent")
    description: str | None = Field(None, description="Optional description")
    capabilities: list = Field(default_factory=list, description="Agent capabilities")
    metadata: dict = Field(default_factory=dict, description="Freeform key-value metadata")


class AgentUpdate(BaseModel):
    """Request body for updating an agent. All fields optional."""

    name: str | None = None
    description: str | None = None
    capabilities: list | None = None
    metadata: dict | None = None
    status: str | None = Field(None, pattern="^(active|suspended)$")


class Agent(BaseModel):
    """Full agent details."""

    id: str = Field(description="Unique agent identifier (UUID)")
    user_id: str = Field(description="Owning user ID")
    org_id: str | None = Field(None, description="Owning organization ID")
    name: str
    description: str | None = None
    status: str = Field(description="active, suspended, or revoked")
    capabilities: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AgentList(BaseModel):
    """Paginated list of agents."""

    items: list[Agent]
    total: int
    limit: int
    offset: int


class AgentCreateResponse(BaseModel):
    """Response for agent creation — includes the show-once API key."""

    agent: Agent
    api_key: str = Field(description="Plaintext API key (aid_sk_…) — shown only once")
