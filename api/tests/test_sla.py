"""Tests for SLA tracking and escalation logic."""

from datetime import UTC, datetime, timedelta

from api.app.sla import (
    calculate_sla_due_at,
    escalate_priority,
    get_hours_overdue,
    get_sla_status,
    should_escalate,
)
from common.models.support_ticket import TicketPriority, TicketStatus


class TestCalculateSLADueAt:
    """Tests for SLA due time calculation."""

    def test_urgent_priority(self):
        """URGENT priority has 4-hour SLA."""
        created_at = datetime(2026, 4, 30, 10, 0, 0, tzinfo=UTC)
        due_at = calculate_sla_due_at(TicketPriority.URGENT, created_at)

        expected = created_at + timedelta(hours=4)
        assert due_at == expected

    def test_high_priority(self):
        """HIGH priority has 24-hour SLA."""
        created_at = datetime(2026, 4, 30, 10, 0, 0, tzinfo=UTC)
        due_at = calculate_sla_due_at(TicketPriority.HIGH, created_at)

        expected = created_at + timedelta(hours=24)
        assert due_at == expected

    def test_medium_priority(self):
        """MEDIUM priority has 48-hour SLA."""
        created_at = datetime(2026, 4, 30, 10, 0, 0, tzinfo=UTC)
        due_at = calculate_sla_due_at(TicketPriority.MEDIUM, created_at)

        expected = created_at + timedelta(hours=48)
        assert due_at == expected

    def test_low_priority(self):
        """LOW priority has 72-hour SLA."""
        created_at = datetime(2026, 4, 30, 10, 0, 0, tzinfo=UTC)
        due_at = calculate_sla_due_at(TicketPriority.LOW, created_at)

        expected = created_at + timedelta(hours=72)
        assert due_at == expected


class TestEscalatePriority:
    """Tests for priority escalation."""

    def test_escalate_low_to_medium(self):
        """LOW escalates to MEDIUM."""
        result = escalate_priority(TicketPriority.LOW)
        assert result == TicketPriority.MEDIUM

    def test_escalate_medium_to_high(self):
        """MEDIUM escalates to HIGH."""
        result = escalate_priority(TicketPriority.MEDIUM)
        assert result == TicketPriority.HIGH

    def test_escalate_high_to_urgent(self):
        """HIGH escalates to URGENT."""
        result = escalate_priority(TicketPriority.HIGH)
        assert result == TicketPriority.URGENT

    def test_escalate_urgent_stays_urgent(self):
        """URGENT is already max priority."""
        result = escalate_priority(TicketPriority.URGENT)
        assert result == TicketPriority.URGENT


class TestShouldEscalate:
    """Tests for escalation decision logic."""

    def test_should_escalate_when_overdue(self, db_session, test_user):
        """Ticket should escalate when past SLA and not breached."""
        from common.models import SupportTicket

        past_due = datetime.now(UTC) - timedelta(hours=1)
        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST1",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            status=TicketStatus.OPEN,
            sla_due_at=past_due,
            sla_breached=False,
        )
        db_session.add(ticket)
        db_session.commit()

        assert should_escalate(ticket) is True

    def test_should_not_escalate_when_already_breached(self, db_session, test_user):
        """Ticket should not escalate if already marked as breached."""
        from common.models import SupportTicket

        past_due = datetime.now(UTC) - timedelta(hours=1)
        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST2",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            status=TicketStatus.OPEN,
            sla_due_at=past_due,
            sla_breached=True,
        )
        db_session.add(ticket)
        db_session.commit()

        assert should_escalate(ticket) is False

    def test_should_not_escalate_when_resolved(self, db_session, test_user):
        """Resolved tickets should not escalate."""
        from common.models import SupportTicket

        past_due = datetime.now(UTC) - timedelta(hours=1)
        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST3",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            status=TicketStatus.RESOLVED,
            sla_due_at=past_due,
            sla_breached=False,
        )
        db_session.add(ticket)
        db_session.commit()

        assert should_escalate(ticket) is False

    def test_should_not_escalate_when_closed(self, db_session, test_user):
        """Closed tickets should not escalate."""
        from common.models import SupportTicket

        past_due = datetime.now(UTC) - timedelta(hours=1)
        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST4",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            status=TicketStatus.CLOSED,
            sla_due_at=past_due,
            sla_breached=False,
        )
        db_session.add(ticket)
        db_session.commit()

        assert should_escalate(ticket) is False

    def test_should_not_escalate_when_not_overdue(self, db_session, test_user):
        """Ticket should not escalate if SLA not yet breached."""
        from common.models import SupportTicket

        future_due = datetime.now(UTC) + timedelta(hours=1)
        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST5",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            status=TicketStatus.OPEN,
            sla_due_at=future_due,
            sla_breached=False,
        )
        db_session.add(ticket)
        db_session.commit()

        assert should_escalate(ticket) is False


class TestGetHoursOverdue:
    """Tests for calculating hours overdue."""

    def test_hours_overdue_when_past_due(self, db_session, test_user):
        """Calculate correct hours when ticket is overdue."""
        from common.models import SupportTicket

        past_due = datetime.now(UTC) - timedelta(hours=5)
        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST6",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            sla_due_at=past_due,
        )
        db_session.add(ticket)
        db_session.commit()

        hours = get_hours_overdue(ticket)
        assert 4.9 < hours < 5.1  # Allow small timing variance

    def test_zero_when_not_overdue(self, db_session, test_user):
        """Return 0 when ticket is not overdue."""
        from common.models import SupportTicket

        future_due = datetime.now(UTC) + timedelta(hours=5)
        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST7",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            sla_due_at=future_due,
        )
        db_session.add(ticket)
        db_session.commit()

        hours = get_hours_overdue(ticket)
        assert hours == 0.0

    def test_zero_when_no_sla(self, db_session, test_user):
        """Return 0 when ticket has no SLA."""
        from common.models import SupportTicket

        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST8",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            sla_due_at=None,
        )
        db_session.add(ticket)
        db_session.commit()

        hours = get_hours_overdue(ticket)
        assert hours == 0.0


class TestGetSLAStatus:
    """Tests for SLA status information."""

    def test_status_with_sla(self, db_session, test_user):
        """Get status for ticket with SLA."""
        from common.models import SupportTicket

        due_at = datetime.now(UTC) + timedelta(hours=10)
        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST9",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            sla_due_at=due_at,
            sla_breached=False,
            escalation_count=0,
        )
        db_session.add(ticket)
        db_session.commit()

        status = get_sla_status(ticket)
        assert status["has_sla"] is True
        assert status["is_breached"] is False
        assert status["hours_remaining"] is not None
        assert status["hours_overdue"] is None
        assert status["escalation_count"] == 0

    def test_status_without_sla(self, db_session, test_user):
        """Get status for ticket without SLA."""
        from common.models import SupportTicket

        ticket = SupportTicket(
            ticket_number="TKT-2026-TEST10",
            user_id=test_user.id,
            subject="Test",
            description="Test ticket",
            sla_due_at=None,
        )
        db_session.add(ticket)
        db_session.commit()

        status = get_sla_status(ticket)
        assert status["has_sla"] is False
        assert status["due_at"] is None
        assert status["hours_remaining"] is None
        assert status["hours_overdue"] is None


# Made with Bob
