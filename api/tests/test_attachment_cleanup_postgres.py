"""Postgres-specific tests for attachment cleanup cron.

These tests MUST run against Postgres because they test timezone-aware
datetime comparisons on timestamptz columns. SQLite doesn't enforce
timezone semantics, so passing on SQLite is not coverage.

Per .bob/rules-code/AGENTS.md: "Postgres-Specific Features Require Postgres-Backed Tests"
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from common.models import Organization, SupportTicket, User
from common.models.support_ticket import TicketPriority, TicketStatus
from common.models.ticket_attachment import TicketAttachment


@pytest.mark.postgres
@pytest.mark.integration
def test_cleanup_cron_timezone_handling(postgres_client, postgres_db, mock_storage):
    """
    Verify cleanup cron handles timezone-aware datetime comparisons correctly.

    This test MUST run against Postgres because:
    - Query uses `deleted_at < (datetime.now(UTC) - timedelta(days=30))`
    - Column is `timestamp with time zone`
    - SQLite doesn't enforce timezone semantics

    The test verifies that attachments deleted 31 days ago are cleaned up,
    while attachments deleted 29 days ago are not.
    """
    # Create test user and org
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="test@example.com",
        role="owner",
        tier="enterprise",
    )
    postgres_db.add(user)
    postgres_db.flush()

    org = Organization(
        id=uuid.UUID("00000000-0000-0000-0000-000000000100"),
        name="Test Org",
        owner_id=user.id,
        tier="enterprise",
    )
    postgres_db.add(org)
    postgres_db.flush()

    user.org_id = org.id
    postgres_db.commit()

    # Create test ticket
    ticket = SupportTicket(
        id=uuid.UUID("00000000-0000-0000-0000-000000001000"),
        ticket_number="TKT-2026-0001",
        user_id=user.id,
        org_id=org.id,
        subject="Test Ticket",
        description="Test",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
    )
    postgres_db.add(ticket)
    postgres_db.commit()

    # Create attachment deleted 31 days ago (should be cleaned up)
    old_attachment = TicketAttachment(
        id=uuid.UUID("00000000-0000-0000-0000-000000002000"),
        ticket_id=ticket.id,
        user_id=user.id,
        org_id=org.id,
        filename="old.txt",
        original_filename="old.txt",
        content_type="text/plain",
        size_bytes=100,
        sha256="a" * 64,
        storage_path="test/old.txt",
        deleted_at=datetime.now(UTC) - timedelta(days=31),
    )
    postgres_db.add(old_attachment)

    # Create attachment deleted 29 days ago (should NOT be cleaned up)
    recent_attachment = TicketAttachment(
        id=uuid.UUID("00000000-0000-0000-0000-000000003000"),
        ticket_id=ticket.id,
        user_id=user.id,
        org_id=org.id,
        filename="recent.txt",
        original_filename="recent.txt",
        content_type="text/plain",
        size_bytes=100,
        sha256="b" * 64,
        storage_path="test/recent.txt",
        deleted_at=datetime.now(UTC) - timedelta(days=29),
    )
    postgres_db.add(recent_attachment)
    postgres_db.commit()

    # Run cleanup cron
    response = postgres_client.post(
        "/api/v1/cron/attachment-cleanup",
        headers={"X-Internal-Key": "test-internal-key-xyz"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["deleted"] == 1  # Only old_attachment should be deleted

    # Verify old attachment is gone
    old = (
        postgres_db.query(TicketAttachment).filter(TicketAttachment.id == old_attachment.id).first()
    )
    assert old is None

    # Verify recent attachment still exists
    recent = (
        postgres_db.query(TicketAttachment)
        .filter(TicketAttachment.id == recent_attachment.id)
        .first()
    )
    assert recent is not None


@pytest.mark.postgres
@pytest.mark.integration
def test_cleanup_cron_closed_ticket_retention(postgres_client, postgres_db, mock_storage):
    """
    Verify cleanup cron deletes attachments from tickets closed 90+ days ago.

    This implements the 90-day retention policy for closed tickets.
    """
    # Create test user and org
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="test@example.com",
        role="owner",
        tier="enterprise",
    )
    postgres_db.add(user)
    postgres_db.flush()

    org = Organization(
        id=uuid.UUID("00000000-0000-0000-0000-000000000100"),
        name="Test Org",
        owner_id=user.id,
        tier="enterprise",
    )
    postgres_db.add(org)
    postgres_db.flush()

    user.org_id = org.id
    postgres_db.commit()

    # Create ticket closed 91 days ago
    old_ticket = SupportTicket(
        id=uuid.UUID("00000000-0000-0000-0000-000000001000"),
        ticket_number="TKT-2026-0001",
        user_id=user.id,
        org_id=org.id,
        subject="Old Ticket",
        description="Test",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.CLOSED,
        closed_at=datetime.now(UTC) - timedelta(days=91),
    )
    postgres_db.add(old_ticket)

    # Create ticket closed 89 days ago
    recent_ticket = SupportTicket(
        id=uuid.UUID("00000000-0000-0000-0000-000000002000"),
        ticket_number="TKT-2026-0002",
        user_id=user.id,
        org_id=org.id,
        subject="Recent Ticket",
        description="Test",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.CLOSED,
        closed_at=datetime.now(UTC) - timedelta(days=89),
    )
    postgres_db.add(recent_ticket)
    postgres_db.commit()

    # Create attachments for both tickets
    old_attachment = TicketAttachment(
        id=uuid.UUID("00000000-0000-0000-0000-000000003000"),
        ticket_id=old_ticket.id,
        user_id=user.id,
        org_id=org.id,
        filename="old.txt",
        original_filename="old.txt",
        content_type="text/plain",
        size_bytes=100,
        sha256="a" * 64,
        storage_path="test/old.txt",
    )
    postgres_db.add(old_attachment)

    recent_attachment = TicketAttachment(
        id=uuid.UUID("00000000-0000-0000-0000-000000004000"),
        ticket_id=recent_ticket.id,
        user_id=user.id,
        org_id=org.id,
        filename="recent.txt",
        original_filename="recent.txt",
        content_type="text/plain",
        size_bytes=100,
        sha256="b" * 64,
        storage_path="test/recent.txt",
    )
    postgres_db.add(recent_attachment)
    postgres_db.commit()

    # Run cleanup cron
    response = postgres_client.post(
        "/api/v1/cron/attachment-cleanup",
        headers={"X-Internal-Key": "test-internal-key-xyz"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["deleted"] == 1  # Only old_attachment should be deleted

    # Verify old attachment is gone
    old = (
        postgres_db.query(TicketAttachment).filter(TicketAttachment.id == old_attachment.id).first()
    )
    assert old is None

    # Verify recent attachment still exists
    recent = (
        postgres_db.query(TicketAttachment)
        .filter(TicketAttachment.id == recent_attachment.id)
        .first()
    )
    assert recent is not None


# Made with Bob
