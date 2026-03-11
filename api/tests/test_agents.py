"""Tests for Agent CRUD endpoints."""

import uuid

from common.models import Agent, AgentKey, AgentStatus, KeyStatus


# ── POST /api/v1/agents ─────────────────────────────────────────────────


class TestCreateAgent:
    def test_create_agent_success(self, client, auth_headers):
        """Creating an agent returns 201 with agent + show-once API key."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "My Agent", "description": "Test agent", "capabilities": ["chat"]},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()

        assert "agent" in data
        assert "api_key" in data

        agent = data["agent"]
        assert agent["name"] == "My Agent"
        assert agent["description"] == "Test agent"
        assert agent["status"] == "active"
        assert agent["capabilities"] == ["chat"]
        assert agent["metadata"] == {}

        # Agent ID is a UUID
        uuid.UUID(agent["id"])

        # API key starts with expected prefix
        assert data["api_key"].startswith("aid_sk_")

    def test_create_agent_minimal(self, client, auth_headers):
        """Creating an agent with only name works."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Minimal Agent"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        agent = resp.json()["agent"]
        assert agent["name"] == "Minimal Agent"
        assert agent["capabilities"] == []

    def test_create_agent_no_auth(self, client):
        """Creating an agent without auth returns 422 (missing header)."""
        resp = client.post("/api/v1/agents", json={"name": "No Auth"})
        assert resp.status_code == 422

    def test_create_agent_bad_auth(self, client):
        """Creating an agent with invalid API key returns 401."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Bad Auth"},
            headers={"X-API-Key": "nonexistent-key-12345678"},
        )
        assert resp.status_code == 401

    def test_create_agent_empty_name(self, client, auth_headers):
        """Creating an agent with empty name returns 422."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_agent_stores_key_hash(self, client, auth_headers, db_session):
        """The agent key is stored as a SHA-256 hash, not plaintext."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Hash Check"},
            headers=auth_headers,
        )
        api_key = resp.json()["api_key"]
        agent_id = resp.json()["agent"]["id"]

        key_record = (
            db_session.query(AgentKey)
            .filter(AgentKey.agent_id == uuid.UUID(agent_id))
            .first()
        )
        assert key_record is not None
        assert key_record.key_hash != api_key  # Not stored plaintext
        assert len(key_record.key_hash) == 64  # SHA-256 hex length
        assert key_record.status == KeyStatus.active.value


# ── GET /api/v1/agents ──────────────────────────────────────────────────


class TestListAgents:
    def test_list_agents_empty(self, client, auth_headers):
        """Listing agents when none exist returns empty list."""
        resp = client.get("/api/v1/agents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_list_agents_returns_own_agents(self, client, auth_headers):
        """Listing agents returns only the current user's agents."""
        # Create 2 agents
        client.post("/api/v1/agents", json={"name": "Agent 1"}, headers=auth_headers)
        client.post("/api/v1/agents", json={"name": "Agent 2"}, headers=auth_headers)

        resp = client.get("/api/v1/agents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_agents_status_filter(self, client, auth_headers):
        """Filtering by status=active excludes revoked agents."""
        # Create and then revoke one
        r1 = client.post("/api/v1/agents", json={"name": "Active"}, headers=auth_headers)
        r2 = client.post("/api/v1/agents", json={"name": "To Revoke"}, headers=auth_headers)
        revoke_id = r2.json()["agent"]["id"]
        client.delete(f"/api/v1/agents/{revoke_id}", headers=auth_headers)

        resp = client.get("/api/v1/agents?status=active", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Active"

    def test_list_agents_pagination(self, client, auth_headers):
        """Pagination with limit and offset works."""
        for i in range(5):
            client.post("/api/v1/agents", json={"name": f"Agent {i}"}, headers=auth_headers)

        resp = client.get("/api/v1/agents?limit=2&offset=2", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 2

    def test_list_agents_isolation(self, client, auth_headers, other_user):
        """Users cannot see other users' agents."""
        client.post("/api/v1/agents", json={"name": "My Agent"}, headers=auth_headers)

        # Other user's list should be empty
        resp = client.get(
            "/api/v1/agents",
            headers={"X-API-Key": "other-user-api-key-87654321"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ── GET /api/v1/agents/{id} ─────────────────────────────────────────────


class TestGetAgent:
    def test_get_agent_success(self, client, auth_headers):
        """Getting an agent by ID returns full details."""
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Detail Agent", "capabilities": ["read", "write"]},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert resp.status_code == 200
        agent = resp.json()
        assert agent["id"] == agent_id
        assert agent["name"] == "Detail Agent"
        assert agent["capabilities"] == ["read", "write"]

    def test_get_agent_not_found(self, client, auth_headers):
        """Getting a nonexistent agent returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/agents/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_agent_other_user(self, client, auth_headers, other_user):
        """Cannot get another user's agent — returns 404."""
        create_resp = client.post(
            "/api/v1/agents", json={"name": "Private"}, headers=auth_headers
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.get(
            f"/api/v1/agents/{agent_id}",
            headers={"X-API-Key": "other-user-api-key-87654321"},
        )
        assert resp.status_code == 404


# ── PUT /api/v1/agents/{id} ─────────────────────────────────────────────


class TestUpdateAgent:
    def test_update_agent_name(self, client, auth_headers):
        """Updating an agent's name works."""
        create_resp = client.post(
            "/api/v1/agents", json={"name": "Old Name"}, headers=auth_headers
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_update_agent_capabilities(self, client, auth_headers):
        """Updating capabilities replaces the list."""
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Cap Agent", "capabilities": ["old"]},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"capabilities": ["new1", "new2"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["capabilities"] == ["new1", "new2"]

    def test_update_agent_suspend(self, client, auth_headers):
        """Setting status to suspended works."""
        create_resp = client.post(
            "/api/v1/agents", json={"name": "Suspend Me"}, headers=auth_headers
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"status": "suspended"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "suspended"

    def test_update_revoked_agent_fails(self, client, auth_headers):
        """Cannot update a revoked agent."""
        create_resp = client.post(
            "/api/v1/agents", json={"name": "To Revoke"}, headers=auth_headers
        )
        agent_id = create_resp.json()["agent"]["id"]
        client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"name": "Nope"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_update_agent_no_fields(self, client, auth_headers):
        """Sending an empty update body returns 422."""
        create_resp = client.post(
            "/api/v1/agents", json={"name": "No Update"}, headers=auth_headers
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_agent_invalid_status(self, client, auth_headers):
        """Setting status to 'revoked' via update is not allowed."""
        create_resp = client.post(
            "/api/v1/agents", json={"name": "Bad Status"}, headers=auth_headers
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"status": "revoked"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_agent_not_found(self, client, auth_headers):
        """Updating a nonexistent agent returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.put(
            f"/api/v1/agents/{fake_id}",
            json={"name": "Ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ── DELETE /api/v1/agents/{id} ──────────────────────────────────────────


class TestDeleteAgent:
    def test_delete_agent_soft_deletes(self, client, auth_headers):
        """Deleting sets status=revoked (soft delete)."""
        create_resp = client.post(
            "/api/v1/agents", json={"name": "Delete Me"}, headers=auth_headers
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

        # Agent still exists in DB (soft delete)
        get_resp = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "revoked"

    def test_delete_agent_revokes_keys(self, client, auth_headers, db_session):
        """Deleting an agent revokes all its active keys."""
        create_resp = client.post(
            "/api/v1/agents", json={"name": "Key Revoke"}, headers=auth_headers
        )
        agent_id = create_resp.json()["agent"]["id"]

        client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)

        keys = (
            db_session.query(AgentKey)
            .filter(AgentKey.agent_id == uuid.UUID(agent_id))
            .all()
        )
        assert len(keys) == 1
        assert keys[0].status == KeyStatus.revoked.value

    def test_delete_agent_already_revoked(self, client, auth_headers):
        """Deleting an already revoked agent returns 400."""
        create_resp = client.post(
            "/api/v1/agents", json={"name": "Double Delete"}, headers=auth_headers
        )
        agent_id = create_resp.json()["agent"]["id"]

        client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        resp = client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert resp.status_code == 400

    def test_delete_agent_not_found(self, client, auth_headers):
        """Deleting a nonexistent agent returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"/api/v1/agents/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404
