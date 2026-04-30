"""Tests for support ticket endpoints."""

import uuid

import pytest
from fastapi import status

from common.models import Agent, SupportTicket, TicketComment, User
from common.models.support_ticket import TicketCategory, TicketPriority, TicketStatus

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def test_agent(db_session, test_user):
    """Create a test agent for ticket linking."""
    agent = Agent(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Test Agent",
        status="active",
        capabilities=["read", "write"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def test_ticket(db_session, test_user):
    """Create a test ticket."""
    ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TKT-2026-0001",
        user_id=test_user.id,
        org_id=test_user.org_id,
        subject="Test ticket subject",
        description="This is a test ticket description with enough detail.",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        category=TicketCategory.TECHNICAL,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


@pytest.fixture
def other_user_ticket(db_session, other_user):
    """Create a ticket for another user."""
    ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TKT-2026-0002",
        user_id=other_user.id,
        org_id=other_user.org_id,
        subject="Other user's ticket",
        description="This ticket belongs to another user.",
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
        category=TicketCategory.BUG,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


# ── Ticket Creation Tests ────────────────────────────────────────────


def test_create_ticket_success(client, auth_headers, test_user):
    """Test creating a ticket with valid data."""
    response = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "Cannot authenticate agent",
            "description": "My agent is failing to authenticate with the gateway.",
            "priority": "high",
            "category": "technical",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["subject"] == "Cannot authenticate agent"
    assert data["priority"] == "high"
    assert data["status"] == "open"
    assert data["category"] == "technical"
    assert data["user_id"] == str(test_user.id)
    assert data["org_id"] == str(test_user.org_id)
    assert data["ticket_number"].startswith("TKT-")
    assert data["comment_count"] == 0
    assert data["comments"] == []


def test_create_ticket_with_agent_link(client, auth_headers, test_agent):
    """Test creating a ticket linked to an agent."""
    response = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "Agent not working",
            "description": "The agent is not responding to requests.",
            "priority": "urgent",
            "related_agent_id": str(test_agent.id),
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["related_agent_id"] == str(test_agent.id)
    assert data["related_agent_name"] == "Test Agent"


def test_create_ticket_with_audit_logs(client, auth_headers):
    """Test creating a ticket with related audit log IDs."""
    audit_log_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    response = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "Suspicious activity detected",
            "description": "Multiple failed authentication attempts.",
            "priority": "high",
            "category": "technical",
            "related_audit_log_ids": audit_log_ids,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["related_audit_log_ids"] == audit_log_ids


def test_create_ticket_invalid_agent(client, auth_headers):
    """Test creating a ticket with non-existent agent ID."""
    response = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "Test ticket",
            "description": "This should fail due to invalid agent.",
            "related_agent_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_data = response.json()
    # API returns custom error format: {"error": {"code": "...", "message": "..."}}
    assert "error" in response_data
    assert "message" in response_data["error"]
    assert "agent not found" in response_data["error"]["message"].lower()


def test_create_ticket_other_users_agent(client, auth_headers, db_session, other_user):
    """Test creating a ticket linked to another user's agent."""
    # Create agent for other user
    other_agent = Agent(
        id=uuid.uuid4(),
        user_id=other_user.id,
        name="Other User's Agent",
        status="active",
        capabilities=["read"],
    )
    db_session.add(other_agent)
    db_session.commit()

    response = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "Test ticket",
            "description": "This should fail - cannot link to other user's agent.",
            "related_agent_id": str(other_agent.id),
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_ticket_validation_errors(client, auth_headers):
    """Test ticket creation with validation errors."""
    # Subject too short
    response = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "Hi",
            "description": "This description is long enough.",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Description too short
    response = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "Valid subject here",
            "description": "Too short",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── Ticket Retrieval Tests ───────────────────────────────────────────


def test_get_ticket_by_id(client, auth_headers, test_ticket):
    """Test retrieving a ticket by ID."""
    response = client.get(f"/api/v1/tickets/{test_ticket.id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(test_ticket.id)
    assert data["subject"] == test_ticket.subject
    assert data["description"] == test_ticket.description
    assert "comments" in data
    assert "user_email" in data
    assert "org_name" in data


def test_get_ticket_not_found(client, auth_headers):
    """Test retrieving a non-existent ticket."""
    response = client.get(f"/api/v1/tickets/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_ticket_access_denied(client, auth_headers, other_user_ticket):
    """Test that users cannot access other users' tickets."""
    response = client.get(f"/api/v1/tickets/{other_user_ticket.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_ticket_org_member_access(client, db_session, test_user, test_ticket):
    """Test that org members can access tickets from their org."""
    # Create another user in the same org
    org_member_key = "orgmember-api-key-11111111"
    org_member = User(
        id=uuid.uuid4(),
        email=org_member_key,
        role="user",
        org_id=test_user.org_id,
    )
    db_session.add(org_member)
    db_session.commit()

    # Use X-API-Key auth for org member
    headers = {"X-API-Key": org_member_key}

    response = client.get(f"/api/v1/tickets/{test_ticket.id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK


def test_get_ticket_admin_access(client, admin_headers, other_user_ticket):
    """Test that admins can access all tickets."""
    response = client.get(f"/api/v1/tickets/{other_user_ticket.id}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK


# ── Ticket List Tests ────────────────────────────────────────────────


def test_list_tickets(client, auth_headers, test_ticket):
    """Test listing tickets."""
    response = client.get("/api/v1/tickets", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_list_tickets_filter_by_status(client, auth_headers, db_session, test_user):
    """Test filtering tickets by status."""
    # Create tickets with different statuses
    open_ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TKT-2026-1001",
        user_id=test_user.id,
        subject="Open ticket",
        description="This is an open ticket.",
        status=TicketStatus.OPEN,
    )
    resolved_ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TKT-2026-1002",
        user_id=test_user.id,
        subject="Resolved ticket",
        description="This is a resolved ticket.",
        status=TicketStatus.RESOLVED,
    )
    db_session.add_all([open_ticket, resolved_ticket])
    db_session.commit()

    # Filter by open status
    response = client.get("/api/v1/tickets?status=open", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(item["status"] == "open" for item in data["items"])

    # Filter by resolved status
    response = client.get("/api/v1/tickets?status=resolved", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(item["status"] == "resolved" for item in data["items"])


def test_list_tickets_filter_by_priority(client, auth_headers, db_session, test_user):
    """Test filtering tickets by priority."""
    urgent_ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TKT-2026-2001",
        user_id=test_user.id,
        subject="Urgent ticket",
        description="This is urgent.",
        priority=TicketPriority.URGENT,
    )
    db_session.add(urgent_ticket)
    db_session.commit()

    response = client.get("/api/v1/tickets?priority=urgent", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(item["priority"] == "urgent" for item in data["items"])


def test_list_tickets_filter_by_category(client, auth_headers, db_session, test_user):
    """Test filtering tickets by category."""
    bug_ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TKT-2026-3001",
        user_id=test_user.id,
        subject="Bug report",
        description="Found a bug.",
        category=TicketCategory.BUG,
    )
    db_session.add(bug_ticket)
    db_session.commit()

    response = client.get("/api/v1/tickets?category=bug", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(item["category"] == "bug" for item in data["items"])


def test_list_tickets_pagination(client, auth_headers, db_session, test_user):
    """Test ticket list pagination."""
    # Create multiple tickets
    for i in range(5):
        ticket = SupportTicket(
            id=uuid.uuid4(),
            ticket_number=f"TKT-2026-4{i:03d}",
            user_id=test_user.id,
            subject=f"Ticket {i}",
            description=f"Description for ticket {i}.",
        )
        db_session.add(ticket)
    db_session.commit()

    # Get first page
    response = client.get("/api/v1/tickets?limit=2&offset=0", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Get second page
    response = client.get("/api/v1/tickets?limit=2&offset=2", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2
    assert data["offset"] == 2


def test_list_tickets_assigned_to_me(client, auth_headers, db_session, test_user):
    """Test filtering tickets assigned to current user."""
    assigned_ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TKT-2026-5001",
        user_id=test_user.id,
        subject="Assigned ticket",
        description="This is assigned to me.",
        assigned_to_user_id=test_user.id,
    )
    unassigned_ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TKT-2026-5002",
        user_id=test_user.id,
        subject="Unassigned ticket",
        description="This is not assigned.",
    )
    db_session.add_all([assigned_ticket, unassigned_ticket])
    db_session.commit()

    response = client.get("/api/v1/tickets?assigned_to_me=true", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(item["assigned_to_user_id"] == str(test_user.id) for item in data["items"])


# ── Ticket Update Tests ──────────────────────────────────────────────


def test_update_ticket_user_fields(client, auth_headers, test_ticket):
    """Test that users can update their own ticket's basic fields."""
    response = client.patch(
        f"/api/v1/tickets/{test_ticket.id}",
        headers=auth_headers,
        json={
            "subject": "Updated subject",
            "description": "Updated description with more details.",
            "priority": "high",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["subject"] == "Updated subject"
    assert data["description"] == "Updated description with more details."
    assert data["priority"] == "high"


def test_update_ticket_user_cannot_change_status(client, auth_headers, test_ticket):
    """Test that regular users cannot change ticket status."""
    response = client.patch(
        f"/api/v1/tickets/{test_ticket.id}",
        headers=auth_headers,
        json={"status": "resolved"},
    )

    # Status change is silently ignored for non-admins
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "open"  # Should remain unchanged


def test_update_ticket_admin_can_change_status(client, admin_headers, test_ticket):
    """Test that admins can change ticket status."""
    response = client.patch(
        f"/api/v1/tickets/{test_ticket.id}",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "in_progress"


def test_update_ticket_resolved_sets_timestamp(client, admin_headers, test_ticket):
    """Test that resolving a ticket sets resolved_at timestamp."""
    response = client.patch(
        f"/api/v1/tickets/{test_ticket.id}",
        headers=admin_headers,
        json={"status": "resolved"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None


def test_update_ticket_closed_sets_timestamp(client, admin_headers, test_ticket):
    """Test that closing a ticket sets closed_at timestamp."""
    response = client.patch(
        f"/api/v1/tickets/{test_ticket.id}",
        headers=admin_headers,
        json={"status": "closed"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "closed"
    assert data["closed_at"] is not None


def test_update_ticket_admin_can_assign(client, admin_headers, test_ticket, admin_user):
    """Test that admins can assign tickets."""
    response = client.patch(
        f"/api/v1/tickets/{test_ticket.id}",
        headers=admin_headers,
        json={"assigned_to_user_id": str(admin_user.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["assigned_to_user_id"] == str(admin_user.id)
    assert data["assigned_to_email"] == admin_user.email


def test_update_ticket_invalid_assignee(client, admin_headers, test_ticket):
    """Test assigning to non-existent user."""
    response = client.patch(
        f"/api/v1/tickets/{test_ticket.id}",
        headers=admin_headers,
        json={"assigned_to_user_id": str(uuid.uuid4())},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_ticket_access_denied(client, auth_headers, other_user_ticket):
    """Test that users cannot update other users' tickets."""
    response = client.patch(
        f"/api/v1/tickets/{other_user_ticket.id}",
        headers=auth_headers,
        json={"subject": "Hacked!"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ── Comment Tests ────────────────────────────────────────────────────


def test_add_comment(client, auth_headers, test_ticket, test_user):
    """Test adding a comment to a ticket."""
    response = client.post(
        f"/api/v1/tickets/{test_ticket.id}/comments",
        headers=auth_headers,
        json={"content": "This is a test comment."},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["content"] == "This is a test comment."
    assert data["user_id"] == str(test_user.id)
    assert data["user_email"] == test_user.email
    assert data["is_internal"] is False
    assert data["ticket_id"] == str(test_ticket.id)


def test_add_internal_comment_admin(client, admin_headers, test_ticket, admin_user):
    """Test that admins can add internal comments."""
    response = client.post(
        f"/api/v1/tickets/{test_ticket.id}/comments",
        headers=admin_headers,
        json={"content": "Internal note for support team.", "is_internal": True},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["is_internal"] is True


def test_add_internal_comment_user_denied(client, auth_headers, test_ticket):
    """Test that regular users cannot add internal comments."""
    response = client.post(
        f"/api/v1/tickets/{test_ticket.id}/comments",
        headers=auth_headers,
        json={"content": "Trying to add internal note.", "is_internal": True},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_add_comment_updates_ticket_timestamp(client, auth_headers, test_ticket, db_session):
    """Test that adding a comment updates the ticket's updated_at timestamp."""
    original_updated_at = test_ticket.updated_at

    response = client.post(
        f"/api/v1/tickets/{test_ticket.id}/comments",
        headers=auth_headers,
        json={"content": "New comment."},
    )

    assert response.status_code == status.HTTP_201_CREATED

    # Refresh ticket from DB
    db_session.refresh(test_ticket)
    assert test_ticket.updated_at > original_updated_at


def test_comments_appear_in_ticket_detail(client, auth_headers, test_ticket, db_session, test_user):
    """Test that comments appear in ticket detail response."""
    # Add a comment
    comment = TicketComment(
        id=uuid.uuid4(),
        ticket_id=test_ticket.id,
        user_id=test_user.id,
        content="Test comment content.",
        is_internal=False,
    )
    db_session.add(comment)
    db_session.commit()

    # Get ticket detail
    response = client.get(f"/api/v1/tickets/{test_ticket.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["comments"]) == 1
    assert data["comments"][0]["content"] == "Test comment content."
    assert data["comment_count"] == 1


def test_add_comment_to_nonexistent_ticket(client, auth_headers):
    """Test adding a comment to a non-existent ticket."""
    response = client.post(
        f"/api/v1/tickets/{uuid.uuid4()}/comments",
        headers=auth_headers,
        json={"content": "This should fail."},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_comment_access_denied(client, auth_headers, other_user_ticket):
    """Test that users cannot comment on other users' tickets."""
    response = client.post(
        f"/api/v1/tickets/{other_user_ticket.id}/comments",
        headers=auth_headers,
        json={"content": "Unauthorized comment."},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ── Context Endpoint Tests ───────────────────────────────────────────


def test_get_ticket_context(client, auth_headers, test_ticket):
    """Test getting ticket context."""
    response = client.get(f"/api/v1/tickets/{test_ticket.id}/context", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["ticket_id"] == str(test_ticket.id)
    assert "related_agent" in data
    assert "recent_audit_logs" in data
    assert "org_info" in data


def test_get_ticket_context_with_agent(client, auth_headers, db_session, test_user, test_agent):
    """Test context includes agent details when linked."""
    ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number="TKT-2026-6001",
        user_id=test_user.id,
        subject="Ticket with agent",
        description="This ticket is linked to an agent.",
        related_agent_id=test_agent.id,
    )
    db_session.add(ticket)
    db_session.commit()

    response = client.get(f"/api/v1/tickets/{ticket.id}/context", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["related_agent"] is not None
    assert data["related_agent"]["name"] == "Test Agent"
    assert data["related_agent"]["id"] == str(test_agent.id)


def test_get_ticket_context_access_denied(client, auth_headers, other_user_ticket):
    """Test that users cannot access context for other users' tickets."""
    response = client.get(f"/api/v1/tickets/{other_user_ticket.id}/context", headers=auth_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ── Ticket Number Generation Tests ──────────────────────────────────


def test_ticket_number_format(client, auth_headers):
    """Test that ticket numbers follow TKT-YYYY-#### format."""
    response = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "Test ticket number",
            "description": "Testing ticket number generation.",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    ticket_number = data["ticket_number"]

    # Check format: TKT-YYYY-####
    parts = ticket_number.split("-")
    assert len(parts) == 3
    assert parts[0] == "TKT"
    assert len(parts[1]) == 4  # Year
    assert len(parts[2]) == 4  # Sequential number
    assert parts[2].isdigit()


def test_ticket_numbers_increment(client, auth_headers):
    """Test that ticket numbers increment sequentially."""
    # Create first ticket
    response1 = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "First ticket",
            "description": "This is the first ticket.",
        },
    )
    ticket1_number = response1.json()["ticket_number"]

    # Create second ticket
    response2 = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={
            "subject": "Second ticket",
            "description": "This is the second ticket.",
        },
    )
    ticket2_number = response2.json()["ticket_number"]

    # Extract numbers
    num1 = int(ticket1_number.split("-")[-1])
    num2 = int(ticket2_number.split("-")[-1])

    assert num2 == num1 + 1


# Made with Bob
