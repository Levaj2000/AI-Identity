"""SLA (Service Level Agreement) tracking for support tickets.

Defines SLA time limits by priority and provides functions for
calculating due times, checking for breaches, and escalating tickets.
"""

from datetime import UTC, datetime, timedelta

from common.models.support_ticket import SupportTicket, TicketPriority, TicketStatus

# SLA time limits in hours by priority
SLA_HOURS = {
    TicketPriority.URGENT: 4,
    TicketPriority.HIGH: 24,
    TicketPriority.MEDIUM: 48,
    TicketPriority.LOW: 72,
}

# Maximum number of escalations before stopping (prevents infinite loops)
MAX_ESCALATIONS = 3


def calculate_sla_due_at(priority: TicketPriority, created_at: datetime) -> datetime:
    """Calculate SLA due timestamp based on priority.

    Args:
        priority: Ticket priority level
        created_at: When the ticket was created

    Returns:
        Datetime when the SLA is due
    """
    hours = SLA_HOURS.get(priority, SLA_HOURS[TicketPriority.MEDIUM])
    return created_at + timedelta(hours=hours)


def should_escalate(ticket: SupportTicket) -> bool:
    """Check if a ticket should be escalated due to SLA breach.

    Args:
        ticket: The support ticket to check

    Returns:
        True if ticket should be escalated, False otherwise
    """
    # Don't escalate resolved or closed tickets
    if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
        return False

    # Must have an SLA due time
    if not ticket.sla_due_at:
        return False

    # Ensure timezone-aware comparison (SQLite stores naive datetimes)
    due_at = ticket.sla_due_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)

    # Check if past due and not already marked as breached
    now = datetime.now(UTC)
    return now > due_at and not ticket.sla_breached


def escalate_priority(current_priority: TicketPriority) -> TicketPriority:
    """Escalate to the next priority level.

    Args:
        current_priority: Current ticket priority

    Returns:
        Next higher priority level (URGENT is max)
    """
    escalation_map = {
        TicketPriority.LOW: TicketPriority.MEDIUM,
        TicketPriority.MEDIUM: TicketPriority.HIGH,
        TicketPriority.HIGH: TicketPriority.URGENT,
        TicketPriority.URGENT: TicketPriority.URGENT,  # Already at max
    }
    return escalation_map.get(current_priority, TicketPriority.URGENT)


def get_hours_overdue(ticket: SupportTicket) -> float:
    """Calculate how many hours a ticket is overdue.

    Args:
        ticket: The support ticket

    Returns:
        Hours overdue (0 if not overdue)
    """
    if not ticket.sla_due_at:
        return 0.0

    # Ensure timezone-aware comparison (SQLite stores naive datetimes)
    due_at = ticket.sla_due_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)

    now = datetime.now(UTC)
    if now <= due_at:
        return 0.0

    delta = now - due_at
    return delta.total_seconds() / 3600


def get_sla_status(ticket: SupportTicket) -> dict:
    """Get SLA status information for a ticket.

    Args:
        ticket: The support ticket

    Returns:
        Dict with SLA status details
    """
    if not ticket.sla_due_at:
        return {
            "has_sla": False,
            "due_at": None,
            "is_breached": False,
            "hours_remaining": None,
            "hours_overdue": None,
        }

    # Ensure timezone-aware comparison (SQLite stores naive datetimes)
    due_at = ticket.sla_due_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)

    now = datetime.now(UTC)
    is_overdue = now > due_at
    delta = due_at - now if not is_overdue else now - due_at
    hours = delta.total_seconds() / 3600

    return {
        "has_sla": True,
        "due_at": ticket.sla_due_at.isoformat(),
        "is_breached": ticket.sla_breached,
        "hours_remaining": None if is_overdue else hours,
        "hours_overdue": hours if is_overdue else None,
        "escalation_count": ticket.escalation_count,
    }


# Made with Bob
