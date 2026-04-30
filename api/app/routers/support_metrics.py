"""Support metrics endpoint — dashboard for support performance tracking."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import SupportTicket, User, get_db
from common.models.support_ticket import TicketStatus

logger = logging.getLogger("ai_identity.api.support_metrics")

router = APIRouter(prefix="/api/v1/support/metrics", tags=["support"])


# ── Response Schemas ─────────────────────────────────────────────────


class TicketBreakdown(BaseModel):
    """Count of tickets by a specific dimension."""

    label: str
    count: int


class SupportMetricsResponse(BaseModel):
    """Support performance metrics."""

    # Time range
    start_date: datetime
    end_date: datetime

    # Overall counts
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    closed_tickets: int

    # Breakdowns
    by_status: list[TicketBreakdown]
    by_priority: list[TicketBreakdown]

    # Performance metrics
    avg_resolution_time_hours: float | None
    sla_compliance_rate: float | None
    escalation_rate: float | None

    # Assignment metrics (if applicable)
    tickets_by_assignee: list[dict[str, Any]] | None = None


# ── GET /api/v1/support/metrics ──────────────────────────────────────


@router.get(
    "",
    response_model=SupportMetricsResponse,
    summary="Get support metrics",
)
async def get_support_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    assigned_to_user_id: str | None = Query(
        None, description="Filter metrics for specific assignee"
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupportMetricsResponse:
    """Get support performance metrics for the specified time range.

    Admins can see all metrics. Regular users see only their organization's metrics.
    """
    if not user.org_id and user.role != "admin":
        raise HTTPException(
            status_code=400, detail="User must belong to an organization to view metrics"
        )

    # Calculate time range
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    # Base query
    query = db.query(SupportTicket).filter(SupportTicket.created_at >= start_date)

    # Apply org filter for non-admins
    if user.role != "admin":
        query = query.filter(SupportTicket.org_id == user.org_id)

    # Apply assignee filter if requested
    if assigned_to_user_id:
        query = query.filter(SupportTicket.assigned_to_user_id == assigned_to_user_id)

    # Get all tickets in range
    tickets = query.all()
    total_tickets = len(tickets)

    # Count by status
    status_counts = (
        db.query(SupportTicket.status, func.count(SupportTicket.id))
        .filter(SupportTicket.created_at >= start_date)
        .group_by(SupportTicket.status)
    )
    if user.role != "admin":
        status_counts = status_counts.filter(SupportTicket.org_id == user.org_id)
    if assigned_to_user_id:
        status_counts = status_counts.filter(
            SupportTicket.assigned_to_user_id == assigned_to_user_id
        )

    by_status = [
        TicketBreakdown(label=status, count=count) for status, count in status_counts.all()
    ]

    # Count by priority
    priority_counts = (
        db.query(SupportTicket.priority, func.count(SupportTicket.id))
        .filter(SupportTicket.created_at >= start_date)
        .group_by(SupportTicket.priority)
    )
    if user.role != "admin":
        priority_counts = priority_counts.filter(SupportTicket.org_id == user.org_id)
    if assigned_to_user_id:
        priority_counts = priority_counts.filter(
            SupportTicket.assigned_to_user_id == assigned_to_user_id
        )

    by_priority = [
        TicketBreakdown(label=priority, count=count) for priority, count in priority_counts.all()
    ]

    # Calculate average resolution time
    resolved_tickets = [
        t
        for t in tickets
        if t.resolved_at and t.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
    ]
    if resolved_tickets:
        total_resolution_time = sum(
            (t.resolved_at - t.created_at).total_seconds() / 3600 for t in resolved_tickets
        )
        avg_resolution_time_hours = total_resolution_time / len(resolved_tickets)
    else:
        avg_resolution_time_hours = None

    # Calculate SLA compliance rate (tickets resolved within SLA)
    tickets_with_sla = [t for t in tickets if hasattr(t, "sla_due_at") and t.sla_due_at]
    if tickets_with_sla:
        compliant_tickets = [
            t for t in tickets_with_sla if t.resolved_at and t.resolved_at <= t.sla_due_at
        ]
        sla_compliance_rate = (len(compliant_tickets) / len(tickets_with_sla)) * 100
    else:
        sla_compliance_rate = None

    # Calculate escalation rate
    if total_tickets > 0:
        escalated_tickets = [
            t
            for t in tickets
            if hasattr(t, "escalation_count") and t.escalation_count and t.escalation_count > 0
        ]
        escalation_rate = (len(escalated_tickets) / total_tickets) * 100
    else:
        escalation_rate = None

    # Get tickets by assignee (admin only)
    tickets_by_assignee = None
    if user.role == "admin" and not assigned_to_user_id:
        assignee_counts = (
            db.query(
                SupportTicket.assigned_to_user_id,
                func.count(SupportTicket.id).label("count"),
            )
            .filter(SupportTicket.created_at >= start_date)
            .filter(SupportTicket.assigned_to_user_id.isnot(None))
            .group_by(SupportTicket.assigned_to_user_id)
            .all()
        )

        tickets_by_assignee = []
        for assignee_id, count in assignee_counts:
            assignee = db.query(User).filter(User.id == assignee_id).first()
            tickets_by_assignee.append(
                {
                    "user_id": str(assignee_id),
                    "email": assignee.email if assignee else "unknown",
                    "count": count,
                }
            )

    # Count tickets by status
    open_tickets = len([t for t in tickets if t.status == TicketStatus.OPEN])
    resolved_tickets_count = len([t for t in tickets if t.status == TicketStatus.RESOLVED])
    closed_tickets = len([t for t in tickets if t.status == TicketStatus.CLOSED])

    return SupportMetricsResponse(
        start_date=start_date,
        end_date=end_date,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        resolved_tickets=resolved_tickets_count,
        closed_tickets=closed_tickets,
        by_status=by_status,
        by_priority=by_priority,
        avg_resolution_time_hours=avg_resolution_time_hours,
        sla_compliance_rate=sla_compliance_rate,
        escalation_rate=escalation_rate,
        tickets_by_assignee=tickets_by_assignee,
    )


# Made with Bob
