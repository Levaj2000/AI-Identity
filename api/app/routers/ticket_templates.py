"""Ticket template endpoints — pre-configured templates for common ticket scenarios."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from api.app.routers.support_tickets import _generate_ticket_number
from common.models import Agent, SupportTicket, TicketTemplate, User, get_db
from common.models.support_ticket import TicketStatus
from common.schemas.support_ticket import TicketDetailResponse
from common.schemas.ticket_template import (
    TicketFromTemplateCreate,
    TicketTemplateCreate,
    TicketTemplateListResponse,
    TicketTemplateResponse,
    TicketTemplateUpdate,
)

logger = logging.getLogger("ai_identity.api.ticket_templates")

router = APIRouter(prefix="/api/v1/support/templates", tags=["support"])


def _build_response(template: TicketTemplate, db: Session) -> TicketTemplateResponse:
    """Build a ticket template response with creator email."""
    creator = db.query(User).filter(User.id == template.created_by_user_id).first()
    return TicketTemplateResponse(
        id=template.id,
        org_id=template.org_id,
        name=template.name,
        description=template.description,
        subject_template=template.subject_template,
        body_template=template.body_template,
        default_priority=template.default_priority,
        default_category=template.default_category,
        created_by_user_id=template.created_by_user_id,
        created_by_email=creator.email if creator else None,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


# ── GET /api/v1/support/templates ────────────────────────────────────


@router.get(
    "",
    response_model=TicketTemplateListResponse,
    summary="List ticket templates",
)
async def list_ticket_templates(
    limit: int = Query(50, ge=1, le=100, description="Number of templates to return"),
    offset: int = Query(0, ge=0, description="Number of templates to skip"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketTemplateListResponse:
    """List ticket templates for the user's organization."""
    if not user.org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization to access templates"
        )

    query = db.query(TicketTemplate).filter(TicketTemplate.org_id == user.org_id)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    templates = query.order_by(TicketTemplate.name).limit(limit).offset(offset).all()

    # Build response objects
    items = [_build_response(tmpl, db) for tmpl in templates]

    return TicketTemplateListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ── POST /api/v1/support/templates ───────────────────────────────────


@router.post(
    "",
    response_model=TicketTemplateResponse,
    summary="Create a ticket template",
    status_code=201,
)
async def create_ticket_template(
    data: TicketTemplateCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketTemplateResponse:
    """Create a new ticket template (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create ticket templates")

    if not user.org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization to create templates"
        )

    template = TicketTemplate(
        org_id=user.org_id,
        name=data.name,
        description=data.description,
        subject_template=data.subject_template,
        body_template=data.body_template,
        default_priority=data.default_priority,
        default_category=data.default_category,
        created_by_user_id=user.id,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    logger.info(
        "Created ticket template '%s' for org %s by user %s",
        template.name,
        template.org_id,
        user.email,
    )

    return _build_response(template, db)


# ── GET /api/v1/support/templates/{template_id} ──────────────────────


@router.get(
    "/{template_id}",
    response_model=TicketTemplateResponse,
    summary="Get ticket template details",
)
async def get_ticket_template(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketTemplateResponse:
    """Get details of a specific ticket template."""
    template = db.query(TicketTemplate).filter(TicketTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Ticket template not found")

    # Check org access
    if template.org_id != user.org_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return _build_response(template, db)


# ── PATCH /api/v1/support/templates/{template_id} ────────────────────


@router.patch(
    "/{template_id}",
    response_model=TicketTemplateResponse,
    summary="Update a ticket template",
)
async def update_ticket_template(
    template_id: UUID,
    data: TicketTemplateUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketTemplateResponse:
    """Update a ticket template (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update ticket templates")

    template = db.query(TicketTemplate).filter(TicketTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Ticket template not found")

    # Check org access
    if template.org_id != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update fields
    if data.name is not None:
        template.name = data.name
    if data.description is not None:
        template.description = data.description
    if data.subject_template is not None:
        template.subject_template = data.subject_template
    if data.body_template is not None:
        template.body_template = data.body_template
    if data.default_priority is not None:
        template.default_priority = data.default_priority
    if data.default_category is not None:
        template.default_category = data.default_category

    template.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(template)

    logger.info("Updated ticket template %s by user %s", template.id, user.email)

    return _build_response(template, db)


# ── DELETE /api/v1/support/templates/{template_id} ───────────────────


@router.delete(
    "/{template_id}",
    status_code=204,
    summary="Delete a ticket template",
)
async def delete_ticket_template(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a ticket template (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete ticket templates")

    template = db.query(TicketTemplate).filter(TicketTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Ticket template not found")

    # Check org access
    if template.org_id != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(template)
    db.commit()

    logger.info("Deleted ticket template %s by user %s", template_id, user.email)


# ── POST /api/v1/support/templates/{template_id}/create-ticket ───────


@router.post(
    "/{template_id}/create-ticket",
    response_model=TicketDetailResponse,
    summary="Create a ticket from a template",
    status_code=201,
)
async def create_ticket_from_template(
    template_id: UUID,
    data: TicketFromTemplateCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    """Create a new support ticket from a template.

    The template provides default values which can be overridden in the request.
    """
    template = db.query(TicketTemplate).filter(TicketTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Ticket template not found")

    # Check org access
    if template.org_id != user.org_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate related agent if provided
    if data.related_agent_id:
        agent = db.query(Agent).filter(Agent.id == data.related_agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Related agent not found")
        if agent.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Cannot link to another user's agent")

    # Generate unique ticket number
    ticket_number = _generate_ticket_number(db)

    # Use template values with optional overrides
    ticket = SupportTicket(
        ticket_number=ticket_number,
        user_id=user.id,
        org_id=user.org_id,
        subject=data.subject or template.subject_template,
        description=data.description or template.body_template,
        priority=data.priority or template.default_priority,
        status=TicketStatus.OPEN,
        category=data.category or template.default_category,
        related_agent_id=data.related_agent_id,
        related_audit_log_ids=data.related_audit_log_ids or [],
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    logger.info(
        "Created ticket %s from template '%s' for user %s",
        ticket.ticket_number,
        template.name,
        user.email,
    )

    # Import here to avoid circular dependency
    from api.app.routers.support_tickets import _build_ticket_response

    return _build_ticket_response(ticket, db, include_comments=True)


# Made with Bob
