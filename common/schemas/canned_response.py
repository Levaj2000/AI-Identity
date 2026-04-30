"""Pydantic schemas for canned response API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Request Schemas ──────────────────────────────────────────────────


class CannedResponseCreate(BaseModel):
    """Create a new canned response."""

    title: str = Field(..., min_length=1, max_length=255, description="Response title")
    body: str = Field(..., min_length=1, description="Response body text")
    category: str | None = Field(None, max_length=50, description="Category for organization")


class CannedResponseUpdate(BaseModel):
    """Update an existing canned response."""

    title: str | None = Field(None, min_length=1, max_length=255)
    body: str | None = Field(None, min_length=1)
    category: str | None = Field(None, max_length=50)


# ── Response Schemas ─────────────────────────────────────────────────


class CannedResponseResponse(BaseModel):
    """Canned response details."""

    id: UUID
    org_id: UUID
    title: str
    body: str
    category: str | None
    created_by_user_id: UUID
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CannedResponseListResponse(BaseModel):
    """Paginated list of canned responses."""

    items: list[CannedResponseResponse]
    total: int
    limit: int
    offset: int


# Made with Bob
