"""Pydantic schemas for support ticket API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from common.models.support_ticket import TicketCategory, TicketPriority, TicketStatus

# ── Request Schemas ──────────────────────────────────────────────────


class TicketCreate(BaseModel):
    """Create a new support ticket."""

    subject: str = Field(..., min_length=5, max_length=255, description="Ticket subject/title")
    description: str = Field(..., min_length=10, description="Detailed description of the issue")
    priority: TicketPriority = Field(
        default=TicketPriority.MEDIUM, description="Ticket priority level"
    )
    category: TicketCategory | None = Field(None, description="Ticket category")
    related_agent_id: UUID | None = Field(None, description="ID of related agent for context")
    related_audit_log_ids: list[str] | None = Field(
        None, description="List of related audit log IDs for context"
    )


class TicketUpdate(BaseModel):
    """Update an existing ticket."""

    subject: str | None = Field(None, min_length=5, max_length=255)
    description: str | None = Field(None, min_length=10)
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    category: TicketCategory | None = None
    assigned_to_user_id: UUID | None = Field(
        None, description="Assign ticket to a user (admin only)"
    )


class CommentCreate(BaseModel):
    """Add a comment to a ticket."""

    content: str = Field(..., min_length=1, description="Comment text")
    is_internal: bool = Field(
        default=False, description="Internal note (admin-only, not visible to customer)"
    )


# ── Response Schemas ─────────────────────────────────────────────────


class CommentResponse(BaseModel):
    """Comment on a support ticket."""

    id: UUID
    ticket_id: UUID
    user_id: UUID
    user_email: str
    content: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    """Support ticket summary for list views."""

    id: UUID
    ticket_number: str
    user_id: UUID
    org_id: UUID | None
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    category: TicketCategory | None
    related_agent_id: UUID | None
    related_agent_name: str | None = None
    related_audit_log_ids: list[str] | None
    assigned_to_user_id: UUID | None
    assigned_to_email: str | None = None
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class TicketDetailResponse(TicketResponse):
    """Full ticket details including comments and context."""

    comments: list[CommentResponse] = []
    user_email: str
    org_name: str | None = None

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    """Paginated list of tickets."""

    items: list[TicketResponse]
    total: int
    limit: int
    offset: int


class TicketContextResponse(BaseModel):
    """Related context for a ticket (agent details, recent audit logs)."""

    ticket_id: UUID
    related_agent: dict | None = Field(
        None, description="Agent details if ticket is linked to an agent"
    )
    recent_audit_logs: list[dict] = Field(
        default_factory=list, description="Recent audit log entries for context"
    )
    org_info: dict | None = Field(None, description="Organization information")


# Made with Bob
