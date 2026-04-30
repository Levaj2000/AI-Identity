"""SLA escalation cron job — runs every 15 minutes to check for SLA breaches.

Called by Kubernetes CronJob every 15 minutes. Not exposed in public API docs.
Secured by internal service key.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from api.app.email import send_sla_breach_notification
from api.app.sla import MAX_ESCALATIONS, calculate_sla_due_at, escalate_priority, should_escalate
from common.config.settings import settings
from common.models import SupportTicket, get_db
from common.models.support_ticket import TicketStatus

logger = logging.getLogger("ai_identity.api.sla_escalation")

router = APIRouter(prefix="/api/v1/cron", tags=["cron"])


@router.post("/sla-escalation")
async def escalate_overdue_tickets(
    db: Session = Depends(get_db),
    x_internal_key: str | None = Header(None, alias="x-internal-key"),
) -> dict:
    """Check for SLA breaches and escalate tickets.

    This endpoint should be called by a Kubernetes CronJob every 15 minutes.
    It finds tickets that have breached their SLA and:
    1. Marks them as breached
    2. Escalates their priority
    3. Recalculates SLA due time for new priority
    4. Sends notification to support team

    Returns:
        Dict with escalation statistics
    """
    # Verify internal service key
    if not settings.internal_service_key or x_internal_key != settings.internal_service_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    now = datetime.now(UTC)

    # Find tickets that need escalation
    # - Status is open, in_progress, or waiting_customer
    # - SLA due time has passed
    # - Not already marked as breached
    tickets = (
        db.query(SupportTicket)
        .filter(
            SupportTicket.status.in_(
                [
                    TicketStatus.OPEN,
                    TicketStatus.IN_PROGRESS,
                    TicketStatus.WAITING_CUSTOMER,
                ]
            ),
            SupportTicket.sla_due_at <= now,
            SupportTicket.sla_breached == False,  # noqa: E712
        )
        .all()
    )

    escalated_count = 0
    errors = []

    for ticket in tickets:
        try:
            if should_escalate(ticket):
                # Check if we've hit the escalation cap
                if ticket.escalation_count >= MAX_ESCALATIONS:
                    logger.info(
                        "Ticket %s has reached max escalations (%d), skipping",
                        ticket.ticket_number,
                        MAX_ESCALATIONS,
                    )
                    continue

                # Store old priority and original SLA due time for notification
                old_priority = ticket.priority

                # Capture original_sla_due_at on first breach for accurate hours_overdue
                if not ticket.original_sla_due_at:
                    ticket.original_sla_due_at = ticket.sla_due_at

                # Mark as breached (keep it True permanently)
                ticket.sla_breached = True
                ticket.escalation_count += 1

                # Escalate priority
                ticket.priority = escalate_priority(old_priority)

                # Recalculate SLA due time for new priority
                ticket.sla_due_at = calculate_sla_due_at(ticket.priority, now)

                db.commit()
                db.refresh(ticket)

                escalated_count += 1

                logger.info(
                    "Escalated ticket %s: %s → %s (escalation #%d/%d)",
                    ticket.ticket_number,
                    old_priority,
                    ticket.priority,
                    ticket.escalation_count,
                    MAX_ESCALATIONS,
                )

                # Send notification to support team
                try:
                    # Use original_sla_due_at for accurate hours_overdue calculation
                    original_due = ticket.original_sla_due_at
                    if original_due.tzinfo is None:
                        original_due = original_due.replace(tzinfo=UTC)
                    hours_overdue = (now - original_due).total_seconds() / 3600

                    send_sla_breach_notification(
                        ticket_number=ticket.ticket_number,
                        subject=ticket.subject,
                        old_priority=old_priority,
                        new_priority=ticket.priority,
                        hours_overdue=hours_overdue,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to send SLA breach notification for %s: %s",
                        ticket.ticket_number,
                        e,
                    )
                    # Don't fail the escalation if email fails

        except Exception as e:
            error_msg = f"Failed to escalate ticket {ticket.ticket_number}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            db.rollback()

    result = {
        "checked": len(tickets),
        "escalated": escalated_count,
        "errors": errors,
        "timestamp": now.isoformat(),
    }

    logger.info(
        "SLA escalation run complete: checked=%d, escalated=%d, errors=%d",
        result["checked"],
        result["escalated"],
        len(errors),
    )

    return result


# Made with Bob
