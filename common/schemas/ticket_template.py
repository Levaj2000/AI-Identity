"""Pydantic schemas for ticket template API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from common.models.support_ticket import TicketCategory, TicketPriority

# ── Request Schemas ──────────────────────────────────────────────────


class TicketTemplateCreate(BaseModel):
    """Create a new ticket template."""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str | None = Field(None, description="Template description")
    subject_template: str = Field(
        ..., min_length=1, max_length=255, description="Subject line template"
    )
    body_template: str = Field(..., min_length=1, description="Body text template")
    default_priority: TicketPriority = Field(
        default=TicketPriority.MEDIUM, description="Default priority for tickets from this template"
    )
    default_category: TicketCategory | None = Field(None, description="Default category")


class TicketTemplateUpdate(BaseModel):
    """Update an existing ticket template."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    subject_template: str | None = Field(None, min_length=1, max_length=255)
    body_template: str | None = Field(None, min_length=1)
    default_priority: TicketPriority | None = None
    default_category: TicketCategory | None = None


class TicketFromTemplateCreate(BaseModel):
    """Create a ticket from a template with optional overrides."""

    subject: str | None = Field(None, description="Override template subject")
    description: str | None = Field(None, description="Override template body")
    priority: TicketPriority | None = Field(None, description="Override default priority")
    category: TicketCategory | None = Field(None, description="Override default category")
    related_agent_id: UUID | None = Field(None, description="ID of related agent for context")
    related_audit_log_ids: list[str] | None = Field(
        None, description="List of related audit log IDs for context"
    )


# ── Response Schemas ─────────────────────────────────────────────────


class TicketTemplateResponse(BaseModel):
    """Ticket template details."""

    id: UUID
    org_id: UUID
    name: str
    description: str | None
    subject_template: str
    body_template: str
    default_priority: TicketPriority
    default_category: TicketCategory | None
    created_by_user_id: UUID
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketTemplateListResponse(BaseModel):
    """Paginated list of ticket templates."""

    items: list[TicketTemplateResponse]
    total: int
    limit: int
    offset: int


# Made with Bob
