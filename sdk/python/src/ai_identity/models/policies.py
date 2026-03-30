"""Policy models."""

from datetime import datetime

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    """Request body for creating a policy."""

    rules: dict = Field(default_factory=dict, description="Policy rules dict")


class Policy(BaseModel):
    """Policy details."""

    id: int
    agent_id: str
    rules: dict
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
