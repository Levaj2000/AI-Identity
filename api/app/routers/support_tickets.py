"""Support ticket endpoints — customer support ticket management."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from api.app.email import send_support_ticket_notification
from common.models import Agent, AuditLog, Organization, SupportTicket, TicketComment, User, get_db
from common.models.support_ticket import TicketCategory, TicketPriority, TicketStatus
from common.schemas.support_ticket import (
    CommentCreate,
    CommentResponse,
    TicketContextResponse,
    TicketCreate,
    TicketDetailResponse,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)

logger = logging.getLogger("ai_identity.api.support_tickets")

router = APIRouter(prefix="/api/v1/tickets", tags=["support"])


def _generate_ticket_number(db: Session) -> str:
    """Generate a unique ticket number in format TKT-YYYY-####."""
    year = datetime.now(UTC).year

    # Get the highest ticket number for this year
    prefix = f"TKT-{year}-"
    last_ticket = (
        db.query(SupportTicket)
        .filter(SupportTicket.ticket_number.like(f"{prefix}%"))
        .order_by(SupportTicket.ticket_number.desc())
        .first()
    )

    if last_ticket:
        # Extract the number part and increment
        last_num = int(last_ticket.ticket_number.split("-")[-1])
        next_num = last_num + 1
    else:
        next_num = 1

    return f"{prefix}{next_num:04d}"


def _build_ticket_response(
    ticket: SupportTicket,
    db: Session,
    include_comments: bool = False,
) -> TicketResponse | TicketDetailResponse:
    """Build a ticket response with related data."""
    # Get comment count
    comment_count = (
        db.query(func.count(TicketComment.id)).filter(TicketComment.ticket_id == ticket.id).scalar()
        or 0
    )

    # Get related agent name if exists
    related_agent_name = None
    if ticket.related_agent_id:
        agent = db.query(Agent).filter(Agent.id == ticket.related_agent_id).first()
        if agent:
            related_agent_name = agent.name

    # Get assigned user email if exists
    assigned_to_email = None
    if ticket.assigned_to_user_id:
        assigned_user = db.query(User).filter(User.id == ticket.assigned_to_user_id).first()
        if assigned_user:
            assigned_to_email = assigned_user.email

    base_data = {
        "id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "user_id": ticket.user_id,
        "org_id": ticket.org_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "priority": ticket.priority,
        "status": ticket.status,
        "category": ticket.category,
        "related_agent_id": ticket.related_agent_id,
        "related_agent_name": related_agent_name,
        "related_audit_log_ids": ticket.related_audit_log_ids,
        "assigned_to_user_id": ticket.assigned_to_user_id,
        "assigned_to_email": assigned_to_email,
        "comment_count": comment_count,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at,
        "closed_at": ticket.closed_at,
    }

    if not include_comments:
        return TicketResponse(**base_data)

    # Get comments for detail view
    comments = (
        db.query(TicketComment)
        .filter(TicketComment.ticket_id == ticket.id)
        .order_by(TicketComment.created_at)
        .all()
    )

    comment_responses = []
    for comment in comments:
        comment_user = db.query(User).filter(User.id == comment.user_id).first()
        comment_responses.append(
            CommentResponse(
                id=comment.id,
                ticket_id=comment.ticket_id,
                user_id=comment.user_id,
                user_email=comment_user.email if comment_user else "unknown",
                content=comment.content,
                is_internal=comment.is_internal,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
            )
        )

    # Get user and org info
    user = db.query(User).filter(User.id == ticket.user_id).first()
    org = (
        db.query(Organization).filter(Organization.id == ticket.org_id).first()
        if ticket.org_id
        else None
    )

    return TicketDetailResponse(
        **base_data,
        comments=comment_responses,
        user_email=user.email if user else "unknown",
        org_name=org.name if org else None,
    )


def _can_access_ticket(user: User, ticket: SupportTicket) -> bool:
    """Check if user can access this ticket."""
    # Admins can access all tickets
    if user.role == "admin":
        return True

    # Users can access their own tickets
    if ticket.user_id == user.id:
        return True

    # Users can access tickets from their organization
    return bool(user.org_id and ticket.org_id == user.org_id)


# ── POST /api/v1/tickets ─────────────────────────────────────────────


@router.post(
    "",
    response_model=TicketDetailResponse,
    summary="Create a new support ticket",
    status_code=201,
)
async def create_ticket(
    data: TicketCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    """Create a new support ticket.

    The ticket will be automatically linked to the user's organization if they have one.
    Optionally link to a specific agent or audit logs for context.
    """
    # Validate related agent if provided
    if data.related_agent_id:
        agent = db.query(Agent).filter(Agent.id == data.related_agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Related agent not found")
        if agent.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Cannot link to another user's agent")

    # Generate unique ticket number
    ticket_number = _generate_ticket_number(db)

    # Create ticket
    ticket = SupportTicket(
        ticket_number=ticket_number,
        user_id=user.id,
        org_id=user.org_id,
        subject=data.subject,
        description=data.description,
        priority=data.priority,
        status=TicketStatus.OPEN,
        category=data.category,
        related_agent_id=data.related_agent_id,
        related_audit_log_ids=data.related_audit_log_ids or [],
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    logger.info(
        "Created ticket %s for user %s: %s",
        ticket.ticket_number,
        user.email,
        ticket.subject,
    )

    # Send email notification to support team (fire-and-forget)
    try:
        agent_name = None
        if data.related_agent_id:
            agent = db.query(Agent).filter(Agent.id == data.related_agent_id).first()
            if agent:
                agent_name = agent.name

        send_support_ticket_notification(
            ticket_number=ticket.ticket_number,
            subject=ticket.subject,
            description=ticket.description,
            priority=ticket.priority.value,
            category=ticket.category.value,
            user_email=user.email,
            user_name=None,  # User model doesn't have first_name field
            agent_name=agent_name,
        )
    except Exception as e:
        # Never block ticket creation on email failure
        logger.error("Failed to send ticket notification email: %s", e)

    return _build_ticket_response(ticket, db, include_comments=True)


# ── GET /api/v1/tickets ──────────────────────────────────────────────


@router.get(
    "",
    response_model=TicketListResponse,
    summary="List support tickets",
)
async def list_tickets(
    status: TicketStatus | None = Query(None, description="Filter by status"),
    priority: TicketPriority | None = Query(None, description="Filter by priority"),
    category: TicketCategory | None = Query(None, description="Filter by category"),
    assigned_to_me: bool = Query(False, description="Show only tickets assigned to me"),
    limit: int = Query(50, ge=1, le=100, description="Number of tickets to return"),
    offset: int = Query(0, ge=0, description="Number of tickets to skip"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketListResponse:
    """List support tickets with optional filtering.

    Regular users see only their own tickets and tickets from their organization.
    Admins see all tickets.
    """
    query = db.query(SupportTicket)

    # Apply access control
    if user.role != "admin":
        # Users see their own tickets or tickets from their org
        filters = [SupportTicket.user_id == user.id]
        if user.org_id:
            filters.append(SupportTicket.org_id == user.org_id)
        query = query.filter(or_(*filters))

    # Apply filters
    if status:
        query = query.filter(SupportTicket.status == status)
    if priority:
        query = query.filter(SupportTicket.priority == priority)
    if category:
        query = query.filter(SupportTicket.category == category)
    if assigned_to_me:
        query = query.filter(SupportTicket.assigned_to_user_id == user.id)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    tickets = query.order_by(SupportTicket.created_at.desc()).limit(limit).offset(offset).all()

    # Build responses
    items = [_build_ticket_response(ticket, db, include_comments=False) for ticket in tickets]

    return TicketListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ── GET /api/v1/tickets/{ticket_id} ──────────────────────────────────


@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get ticket details",
)
async def get_ticket(
    ticket_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    """Get full details of a support ticket including all comments."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not _can_access_ticket(user, ticket):
        raise HTTPException(status_code=403, detail="Access denied")

    return _build_ticket_response(ticket, db, include_comments=True)


# ── PATCH /api/v1/tickets/{ticket_id} ────────────────────────────────


@router.patch(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Update a ticket",
)
async def update_ticket(
    ticket_id: UUID,
    data: TicketUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    """Update a support ticket.

    Regular users can update their own tickets (subject, description, priority).
    Admins can additionally update status, category, and assignment.
    """
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not _can_access_ticket(user, ticket):
        raise HTTPException(status_code=403, detail="Access denied")

    # Update allowed fields
    if data.subject is not None:
        ticket.subject = data.subject
    if data.description is not None:
        ticket.description = data.description
    if data.priority is not None:
        ticket.priority = data.priority

    # Admin-only fields
    if user.role == "admin":
        if data.status is not None:
            old_status = ticket.status
            ticket.status = data.status

            # Set resolved_at when status changes to resolved
            if data.status == TicketStatus.RESOLVED and old_status != TicketStatus.RESOLVED:
                ticket.resolved_at = datetime.now(UTC)

            # Set closed_at when status changes to closed
            if data.status == TicketStatus.CLOSED and old_status != TicketStatus.CLOSED:
                ticket.closed_at = datetime.now(UTC)

        if data.category is not None:
            ticket.category = data.category

        if data.assigned_to_user_id is not None:
            # Validate assigned user exists
            assigned_user = db.query(User).filter(User.id == data.assigned_to_user_id).first()
            if not assigned_user:
                raise HTTPException(status_code=404, detail="Assigned user not found")
            ticket.assigned_to_user_id = data.assigned_to_user_id

    ticket.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(ticket)

    logger.info("Updated ticket %s by user %s", ticket.ticket_number, user.email)

    return _build_ticket_response(ticket, db, include_comments=True)


# ── POST /api/v1/tickets/{ticket_id}/comments ────────────────────────


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentResponse,
    summary="Add a comment to a ticket",
    status_code=201,
)
async def add_comment(
    ticket_id: UUID,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommentResponse:
    """Add a comment to a support ticket.

    Regular users can add public comments.
    Admins can add both public and internal comments.
    """
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not _can_access_ticket(user, ticket):
        raise HTTPException(status_code=403, detail="Access denied")

    # Only admins can create internal comments
    if data.is_internal and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create internal comments")

    comment = TicketComment(
        ticket_id=ticket_id,
        user_id=user.id,
        content=data.content,
        is_internal=data.is_internal,
    )

    db.add(comment)

    # Update ticket's updated_at timestamp
    ticket.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(comment)

    logger.info(
        "Added %s comment to ticket %s by user %s",
        "internal" if data.is_internal else "public",
        ticket.ticket_number,
        user.email,
    )

    return CommentResponse(
        id=comment.id,
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        user_email=user.email,
        content=comment.content,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


# ── GET /api/v1/tickets/{ticket_id}/context ──────────────────────────


@router.get(
    "/{ticket_id}/context",
    response_model=TicketContextResponse,
    summary="Get related context for a ticket",
)
async def get_ticket_context(
    ticket_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketContextResponse:
    """Get related context for a ticket (agent details, recent audit logs, org info)."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not _can_access_ticket(user, ticket):
        raise HTTPException(status_code=403, detail="Access denied")

    context = TicketContextResponse(ticket_id=ticket_id)

    # Get related agent details
    if ticket.related_agent_id:
        agent = db.query(Agent).filter(Agent.id == ticket.related_agent_id).first()
        if agent:
            context.related_agent = {
                "id": str(agent.id),
                "name": agent.name,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "created_at": agent.created_at.isoformat(),
            }

    # Get recent audit logs (if IDs provided)
    if ticket.related_audit_log_ids:
        audit_logs = (
            db.query(AuditLog)
            .filter(AuditLog.id.in_(ticket.related_audit_log_ids[:10]))  # Limit to 10
            .order_by(AuditLog.timestamp.desc())
            .all()
        )
        context.recent_audit_logs = [
            {
                "id": str(log.id),
                "action": log.action,
                "timestamp": log.timestamp.isoformat(),
                "agent_id": str(log.agent_id) if log.agent_id else None,
                "metadata": log.metadata_,
            }
            for log in audit_logs
        ]

    # Get organization info
    if ticket.org_id:
        org = db.query(Organization).filter(Organization.id == ticket.org_id).first()
        if org:
            context.org_info = {
                "id": str(org.id),
                "name": org.name,
                "tier": org.tier,
                "created_at": org.created_at.isoformat(),
            }

    return context


# Made with Bob
