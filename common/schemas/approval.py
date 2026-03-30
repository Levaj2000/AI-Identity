"""Approval request API schemas — human-in-the-loop review."""

import datetime
import enum

from pydantic import BaseModel, Field


class ApprovalAction(enum.StrEnum):
    """Actions that can be taken on a pending approval."""

    approve = "approve"
    reject = "reject"


# ── Response Schemas ────────────────────────────────────────────────


class ApprovalResponse(BaseModel):
    """Full approval request detail."""

    id: str
    agent_id: str
    agent_name: str | None = None
    user_id: str
    endpoint: str
    method: str
    request_metadata: dict
    status: str
    reviewer_id: str | None = None
    reviewer_note: str | None = None
    resolved_at: datetime.datetime | None = None
    expires_at: datetime.datetime
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None

    model_config = {"from_attributes": True}


class ApprovalListResponse(BaseModel):
    """Paginated list of approval requests."""

    items: list[ApprovalResponse]
    total: int
    limit: int
    offset: int


class ApprovalPendingCount(BaseModel):
    """Count of pending approvals (for sidebar badge)."""

    count: int


# ── Request Schemas ─────────────────────────────────────────────────


class ApprovalResolveRequest(BaseModel):
    """Approve or reject a pending request."""

    action: ApprovalAction
    note: str | None = Field(None, max_length=1000, description="Optional reviewer note")
