"""Tests for Shadow Agent Detection API endpoints.

NOTE: These tests require PostgreSQL because the shadow detection queries
use JSONB operators (request_metadata['deny_reason'].astext) which are not
supported by SQLite. Mark as skipped when running against SQLite.

Verifies:
  - Stats endpoint returns correct counts from audit_log
  - List endpoint groups by agent_id with hit counts
  - Detail endpoint returns top endpoints and recent events
  - Non-admin users only see their own shadow agents
  - Empty state returns zeros (not errors)
"""

import datetime
import uuid

import pytest

from common.models import AuditLog, User

# Shadow detection uses PostgreSQL JSONB operators not supported by SQLite
pytestmark = pytest.mark.skipif(
    "sqlite" in str(__import__("api.tests.conftest", fromlist=["engine"]).engine.url),
    reason="Shadow detection requires PostgreSQL JSONB operators",
)

# Fixed UUIDs — must match conftest.py TEST_USER_ID
SHADOW_AGENT_1 = uuid.UUID("00000000-0000-0000-0000-aaaaaaaaaaaa")
SHADOW_AGENT_2 = uuid.UUID("00000000-0000-0000-0000-bbbbbbbbbbbb")
INACTIVE_AGENT = uuid.UUID("00000000-0000-0000-0000-cccccccccccc")
REGULAR_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

# Matches conftest TEST_API_KEY
TEST_API_KEY = "test-user-api-key-12345678"
REGULAR_API_KEY = "regular-user-api-key-99999"


def _create_shadow_audit_entries(db_session, agent_id, user_id, deny_reason, endpoint, count):
    """Helper to create multiple denied audit log entries for a shadow agent."""
    for i in range(count):
        entry = AuditLog(
            agent_id=agent_id,
            user_id=user_id,
            endpoint=endpoint,
            method="POST",
            decision="deny",
            request_metadata={"deny_reason": deny_reason, "status_code": 404},
            entry_hash=f"hash_{agent_id}_{i}",
            prev_hash=f"prev_{agent_id}_{i}",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=i),
        )
        db_session.add(entry)
    db_session.commit()


@pytest.fixture
def make_admin(db_session, test_user):
    """Promote the conftest test_user to admin role."""
    test_user.role = "admin"
    db_session.commit()
    return test_user


@pytest.fixture
def regular_user(db_session):
    """Non-admin user who sees only their own shadow agents."""
    user = User(
        id=REGULAR_USER_ID,
        email=REGULAR_API_KEY,
        role="owner",
        tier="free",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def shadow_data(db_session, make_admin):
    """Seed audit_log with shadow agent entries."""
    # Shadow agent 1: unknown agent, 5 hits on /v1/chat
    _create_shadow_audit_entries(
        db_session, SHADOW_AGENT_1, None, "agent_not_found", "/v1/chat/completions", 5
    )
    # Shadow agent 1: also hit /v1/admin
    _create_shadow_audit_entries(
        db_session, SHADOW_AGENT_1, None, "agent_not_found", "/v1/admin/secrets", 2
    )
    # Shadow agent 2: unknown agent, 3 hits
    _create_shadow_audit_entries(
        db_session, SHADOW_AGENT_2, None, "agent_not_found", "/v1/embeddings", 3
    )
    # Inactive agent: owned by regular_user, 4 hits
    _create_shadow_audit_entries(
        db_session, INACTIVE_AGENT, REGULAR_USER_ID, "agent_inactive", "/v1/chat/completions", 4
    )
    return {
        "total_shadow_agents": 3,
        "total_hits": 14,
        "not_found": 2,
        "inactive": 1,
    }


# ── Stats Endpoint ───────────────────────────────────────────────────


class TestShadowStats:
    """GET /api/v1/shadow-agents/stats"""

    def test_stats_returns_correct_counts(self, client, auth_headers, shadow_data):
        """Admin sees all shadow agents across the platform."""
        resp = client.get("/api/v1/shadow-agents/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_shadow_agents"] == 3
        assert data["total_shadow_hits"] == 14
        assert data["agents_not_found"] == 2
        assert data["agents_inactive"] == 1

    def test_stats_empty_returns_zeros(self, client, auth_headers, admin_user):
        """No shadow agents → all zeros (not errors)."""
        resp = client.get("/api/v1/shadow-agents/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_shadow_agents"] == 0
        assert data["total_shadow_hits"] == 0


# ── List Endpoint ────────────────────────────────────────────────────


class TestShadowList:
    """GET /api/v1/shadow-agents"""

    def test_list_returns_grouped_agents(self, client, auth_headers, shadow_data):
        """Admin sees all shadow agents grouped by agent_id."""
        resp = client.get("/api/v1/shadow-agents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        assert data["total_hits"] == 14

        # Check first item has expected fields
        item = data["items"][0]
        assert "agent_id" in item
        assert "deny_reason" in item
        assert "hit_count" in item
        assert "first_seen" in item
        assert "last_seen" in item

    def test_list_sorted_by_hit_count(self, client, auth_headers, shadow_data):
        """Results sorted by hit count descending."""
        resp = client.get("/api/v1/shadow-agents", headers=auth_headers)
        data = resp.json()
        hits = [item["hit_count"] for item in data["items"]]
        assert hits == sorted(hits, reverse=True)

    def test_list_filter_by_deny_reason(self, client, auth_headers, shadow_data):
        """Filter to only agent_not_found."""
        resp = client.get("/api/v1/shadow-agents?deny_reason=agent_not_found", headers=auth_headers)
        data = resp.json()
        for item in data["items"]:
            assert item["deny_reason"] == "agent_not_found"

    def test_list_min_hits_filter(self, client, auth_headers, shadow_data):
        """min_hits=5 filters out low-frequency probers."""
        resp = client.get("/api/v1/shadow-agents?min_hits=5", headers=auth_headers)
        data = resp.json()
        for item in data["items"]:
            assert item["hit_count"] >= 5

    def test_list_pagination(self, client, auth_headers, shadow_data):
        """Pagination works with limit and offset."""
        resp = client.get("/api/v1/shadow-agents?limit=1&offset=0", headers=auth_headers)
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] >= 3


# ── Detail Endpoint ──────────────────────────────────────────────────


class TestShadowDetail:
    """GET /api/v1/shadow-agents/{agent_id}"""

    def test_detail_returns_full_info(self, client, auth_headers, shadow_data):
        """Detail view returns top endpoints and recent events."""
        resp = client.get(f"/api/v1/shadow-agents/{SHADOW_AGENT_1}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == str(SHADOW_AGENT_1)
        assert data["hit_count"] >= 5
        assert len(data["top_endpoints"]) > 0
        assert len(data["recent_events"]) > 0

        # Top endpoints have correct structure
        ep = data["top_endpoints"][0]
        assert "endpoint" in ep
        assert "method" in ep
        assert "count" in ep

    def test_detail_recent_events_have_structure(self, client, auth_headers, shadow_data):
        """Recent events include all required fields."""
        resp = client.get(f"/api/v1/shadow-agents/{SHADOW_AGENT_1}", headers=auth_headers)
        data = resp.json()
        event = data["recent_events"][0]
        assert "id" in event
        assert "endpoint" in event
        assert "method" in event
        assert "deny_reason" in event
        assert "created_at" in event

    def test_detail_404_for_unknown(self, client, auth_headers, admin_user):
        """Unknown shadow agent returns 404."""
        unknown = uuid.uuid4()
        resp = client.get(f"/api/v1/shadow-agents/{unknown}", headers=auth_headers)
        assert resp.status_code == 404


# ── Access Control ───────────────────────────────────────────────────


class TestShadowAccessControl:
    """Non-admin users see only their own shadow agents."""

    def test_regular_user_sees_only_own(self, client, db_session, shadow_data, regular_user):
        """Non-admin user sees only inactive agents they own."""
        headers = {"X-API-Key": REGULAR_API_KEY}
        resp = client.get("/api/v1/shadow-agents/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Regular user should only see the inactive agent (user_id matches)
        # agent_not_found entries have user_id=NULL → not visible to non-admin
        assert data["agents_inactive"] >= 1
        assert data["agents_not_found"] == 0
