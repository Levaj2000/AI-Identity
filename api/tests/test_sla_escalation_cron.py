"""Tests for SLA escalation cron endpoint."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi import status

from common.models import SupportTicket
from common.models.support_ticket import TicketPriority, TicketStatus


class TestSLAEscalationCron:
    """Tests for the SLA escalation cron job endpoint."""

    def test_requires_authentication(self, client):
        """Endpoint requires internal service key."""
        response = client.post("/api/v1/cron/sla-escalation")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rejects_invalid_key(self, client):
        """Endpoint rejects invalid internal service key."""
        response = client.post(
            "/api/v1/cron/sla-escalation",
            headers={"X-Internal-Key": "invalid-key"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_accepts_valid_key(self, client, db_session):
        """Endpoint accepts valid internal service key (test key set by fixture)."""
        response = client.post(
            "/api/v1/cron/sla-escalation",
            headers={"X-Internal-Key": "test-internal-key-xyz"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "checked" in data
        assert "escalated" in data
        assert "errors" in data
        assert "timestamp" in data

    def test_escalates_overdue_ticket(self, client, db_session, test_user):
        """Escalates ticket that is past SLA due time."""
        # Create overdue ticket
        past_due = datetime.now(UTC) - timedelta(hours=1)
        ticket = SupportTicket(
            id=uuid.uuid4(),
            ticket_number="TKT-2026-ESC1",
            user_id=test_user.id,
            org_id=test_user.org_id,
            subject="Overdue ticket",
            description="This ticket is past its SLA.",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
            sla_due_at=past_due,
            sla_breached=False,
            escalation_count=0,
        )
        db_session.add(ticket)
        db_session.commit()
        ticket_id = ticket.id

        # Run escalation
        response = client.post(
            "/api/v1/cron/sla-escalation",
            headers={"X-Internal-Key": "test-internal-key-xyz"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["checked"] >= 1
        assert data["escalated"] >= 1

        # Verify ticket was escalated
        db_session.expire_all()
        escalated_ticket = (
            db_session.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        )

        assert escalated_ticket.priority == TicketPriority.HIGH  # MEDIUM → HIGH
        assert escalated_ticket.sla_breached is True  # Kept True permanently
        assert escalated_ticket.escalation_count == 1
        # SQLite stores naive datetimes, so compare without timezone
        assert escalated_ticket.original_sla_due_at.replace(tzinfo=UTC) == past_due

    def test_does_not_double_escalate(self, client, db_session, test_user):
        """Does not escalate ticket that is already marked as breached."""
        past_due = datetime.now(UTC) - timedelta(hours=1)
        ticket = SupportTicket(
            id=uuid.uuid4(),
            ticket_number="TKT-2026-ESC2",
            user_id=test_user.id,
            org_id=test_user.org_id,
            subject="Already breached",
            description="This ticket is already breached.",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
            sla_due_at=past_due,
            sla_breached=True,  # Already breached
            escalation_count=1,
        )
        db_session.add(ticket)
        db_session.commit()
        ticket_id = ticket.id

        # Run escalation
        response = client.post(
            "/api/v1/cron/sla-escalation",
            headers={"X-Internal-Key": "test-internal-key-xyz"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["escalated"] == 0  # Should not escalate

        # Verify ticket was NOT escalated again
        db_session.expire_all()
        ticket = db_session.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

        assert ticket.priority == TicketPriority.MEDIUM  # Unchanged
        assert ticket.escalation_count == 1  # Unchanged

    def test_does_not_escalate_resolved_tickets(self, client, db_session, test_user):
        """Does not escalate resolved tickets."""
        past_due = datetime.now(UTC) - timedelta(hours=1)
        ticket = SupportTicket(
            id=uuid.uuid4(),
            ticket_number="TKT-2026-ESC3",
            user_id=test_user.id,
            org_id=test_user.org_id,
            subject="Resolved ticket",
            description="This ticket is resolved.",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.RESOLVED,
            sla_due_at=past_due,
            sla_breached=False,
            escalation_count=0,
        )
        db_session.add(ticket)
        db_session.commit()

        # Run escalation
        response = client.post(
            "/api/v1/cron/sla-escalation",
            headers={"X-Internal-Key": "test-internal-key-xyz"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["escalated"] == 0

    def test_does_not_escalate_closed_tickets(self, client, db_session, test_user):
        """Does not escalate closed tickets."""
        past_due = datetime.now(UTC) - timedelta(hours=1)
        ticket = SupportTicket(
            id=uuid.uuid4(),
            ticket_number="TKT-2026-ESC4",
            user_id=test_user.id,
            org_id=test_user.org_id,
            subject="Closed ticket",
            description="This ticket is closed.",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.CLOSED,
            sla_due_at=past_due,
            sla_breached=False,
            escalation_count=0,
        )
        db_session.add(ticket)
        db_session.commit()

        # Run escalation
        response = client.post(
            "/api/v1/cron/sla-escalation",
            headers={"X-Internal-Key": "test-internal-key-xyz"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["escalated"] == 0

    def test_escalates_multiple_tickets(self, client, db_session, test_user):
        """Escalates multiple overdue tickets in one run."""
        past_due = datetime.now(UTC) - timedelta(hours=2)

        # Create 3 overdue tickets
        for i in range(3):
            ticket = SupportTicket(
                id=uuid.uuid4(),
                ticket_number=f"TKT-2026-MULTI{i}",
                user_id=test_user.id,
                org_id=test_user.org_id,
                subject=f"Overdue ticket {i}",
                description="Overdue",
                priority=TicketPriority.LOW,
                status=TicketStatus.OPEN,
                sla_due_at=past_due,
                sla_breached=False,
                escalation_count=0,
            )
            db_session.add(ticket)
        db_session.commit()

        # Run escalation
        response = client.post(
            "/api/v1/cron/sla-escalation",
            headers={"X-Internal-Key": "test-internal-key-xyz"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["checked"] >= 3
        assert data["escalated"] == 3

    def test_regression_bug1_max_escalations_cap(self, client, db_session, test_user):
        """REGRESSION TEST: Verify escalation stops at MAX_ESCALATIONS (3) to prevent infinite loops."""
        from api.app.sla import MAX_ESCALATIONS

        # Create URGENT ticket that's already at max escalations
        past_due = datetime.now(UTC) - timedelta(hours=1)
        ticket = SupportTicket(
            id=uuid.uuid4(),
            ticket_number="TKT-2026-MAXESC",
            user_id=test_user.id,
            org_id=test_user.org_id,
            subject="Max escalations reached",
            description="This ticket has hit the cap.",
            priority=TicketPriority.URGENT,
            status=TicketStatus.OPEN,
            sla_due_at=past_due,
            sla_breached=False,  # Query will find it
            escalation_count=MAX_ESCALATIONS,  # Already at cap
        )
        db_session.add(ticket)
        db_session.commit()
        ticket_id = ticket.id

        # Run escalation twice
        for _ in range(2):
            response = client.post(
                "/api/v1/cron/sla-escalation",
                headers={"X-Internal-Key": "test-internal-key-xyz"},
            )
            assert response.status_code == status.HTTP_200_OK

        # Verify escalation_count did NOT increase beyond MAX_ESCALATIONS
        db_session.expire_all()
        ticket = db_session.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

        assert ticket.escalation_count == MAX_ESCALATIONS  # Still at cap, not 4 or 5
        assert ticket.priority == TicketPriority.URGENT  # Unchanged

    @patch("api.app.routers.sla_escalation_cron.send_sla_breach_notification")
    def test_regression_bug2_positive_hours_overdue(
        self, mock_send_email, client, db_session, test_user
    ):
        """REGRESSION TEST: Verify hours_overdue is positive using original_sla_due_at."""
        # Create overdue ticket
        original_due = datetime.now(UTC) - timedelta(hours=5)
        ticket = SupportTicket(
            id=uuid.uuid4(),
            ticket_number="TKT-2026-POSOVERDUE",
            user_id=test_user.id,
            org_id=test_user.org_id,
            subject="Positive overdue test",
            description="Test hours_overdue calculation.",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
            sla_due_at=original_due,
            sla_breached=False,
            escalation_count=0,
        )
        db_session.add(ticket)
        db_session.commit()

        # Run escalation
        response = client.post(
            "/api/v1/cron/sla-escalation",
            headers={"X-Internal-Key": "test-internal-key-xyz"},
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify send_sla_breach_notification was called with positive hours_overdue
        assert mock_send_email.called
        call_args = mock_send_email.call_args[1]
        hours_overdue = call_args["hours_overdue"]

        # Should be ~5 hours (positive), not negative
        assert hours_overdue > 4.9
        assert hours_overdue < 5.1


# Made with Bob
