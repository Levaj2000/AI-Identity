"""Pydantic schemas for organization and agent assignment endpoints."""

import datetime
import uuid

from pydantic import BaseModel, Field

# ── Organization ──────────────────────────────────────────────────────


class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")


class OrgUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="New organization name")


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    tier: str
    member_count: int
    agent_count: int
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class OrgMemberInvite(BaseModel):
    email: str = Field(..., description="Email of user to invite")
    role: str = Field("member", pattern="^(admin|member)$", description="Role: admin or member")


class OrgMemberUpdate(BaseModel):
    role: str = Field(..., pattern="^(owner|admin|member)$", description="New role")


class OrgMemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str
    joined_at: datetime.datetime

    model_config = {"from_attributes": True}


# ── Agent Assignments ─────────────────────────────────────────────────


class AgentAssignmentCreate(BaseModel):
    user_id: uuid.UUID = Field(..., description="User to assign")
    role: str = Field("viewer", pattern="^(owner|operator|viewer)$", description="Assignment role")


class AgentAssignmentUpdate(BaseModel):
    role: str = Field(..., pattern="^(owner|operator|viewer)$", description="New role")


class AgentAssignmentResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
