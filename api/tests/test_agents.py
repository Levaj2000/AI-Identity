"""Tests for Agent CRUD endpoints."""

import uuid

from common.models import AgentKey, AuditLog, KeyStatus

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
        """Creating an agent without auth returns 401 (no credentials)."""
        resp = client.post("/api/v1/agents", json={"name": "No Auth"})
        assert resp.status_code == 401

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
            db_session.query(AgentKey).filter(AgentKey.agent_id == uuid.UUID(agent_id)).first()
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
        client.post("/api/v1/agents", json={"name": "Active"}, headers=auth_headers)
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
        create_resp = client.post("/api/v1/agents", json={"name": "Private"}, headers=auth_headers)
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
        create_resp = client.post("/api/v1/agents", json={"name": "Old Name"}, headers=auth_headers)
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

        keys = db_session.query(AgentKey).filter(AgentKey.agent_id == uuid.UUID(agent_id)).all()
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


# ── Capabilities & Metadata ──────────────────────────────────────────────


class TestCapabilitiesAndMetadata:
    def test_create_agent_with_capabilities_and_metadata(self, client, auth_headers):
        """Creating an agent with both capabilities and metadata stores them correctly."""
        resp = client.post(
            "/api/v1/agents",
            json={
                "name": "Full Agent",
                "capabilities": ["chat_completion", "image_generation", "function_calling"],
                "metadata": {
                    "framework": "langchain",
                    "environment": "production",
                    "owner_team": "platform",
                },
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        agent = resp.json()["agent"]
        assert agent["capabilities"] == ["chat_completion", "image_generation", "function_calling"]
        assert agent["metadata"] == {
            "framework": "langchain",
            "environment": "production",
            "owner_team": "platform",
        }

    def test_create_agent_defaults(self, client, auth_headers):
        """Capabilities default to [] and metadata defaults to {} when omitted."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Defaults Only"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        agent = resp.json()["agent"]
        assert agent["capabilities"] == []
        assert agent["metadata"] == {}

    def test_get_agent_returns_capabilities_and_metadata(self, client, auth_headers):
        """GET /agents/{id} returns capabilities and metadata."""
        create_resp = client.post(
            "/api/v1/agents",
            json={
                "name": "Detail Check",
                "capabilities": ["embeddings"],
                "metadata": {"version": "2.0"},
            },
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["capabilities"] == ["embeddings"]
        assert resp.json()["metadata"] == {"version": "2.0"}

    def test_list_agents_returns_capabilities_and_metadata(self, client, auth_headers):
        """GET /agents list includes capabilities and metadata on each agent."""
        client.post(
            "/api/v1/agents",
            json={
                "name": "Listed Agent",
                "capabilities": ["chat"],
                "metadata": {"env": "staging"},
            },
            headers=auth_headers,
        )

        resp = client.get("/api/v1/agents", headers=auth_headers)
        assert resp.status_code == 200
        agent = resp.json()["items"][0]
        assert agent["capabilities"] == ["chat"]
        assert agent["metadata"] == {"env": "staging"}

    def test_update_metadata(self, client, auth_headers):
        """Updating metadata replaces the entire dict."""
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Meta Agent", "metadata": {"old_key": "old_value"}},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"metadata": {"new_key": "new_value", "env": "production"}},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["metadata"] == {"new_key": "new_value", "env": "production"}

    def test_update_capabilities_and_metadata_together(self, client, auth_headers):
        """Updating both capabilities and metadata in a single request works."""
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Combo Agent"},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={
                "capabilities": ["chat_completion", "function_calling"],
                "metadata": {"framework": "crewai", "tier": "enterprise"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["capabilities"] == ["chat_completion", "function_calling"]
        assert resp.json()["metadata"] == {"framework": "crewai", "tier": "enterprise"}

    def test_filter_by_capability(self, client, auth_headers):
        """Filtering agents by capability returns only matching agents."""
        client.post(
            "/api/v1/agents",
            json={"name": "Chat Agent", "capabilities": ["chat_completion", "embeddings"]},
            headers=auth_headers,
        )
        client.post(
            "/api/v1/agents",
            json={"name": "Image Agent", "capabilities": ["image_generation"]},
            headers=auth_headers,
        )
        client.post(
            "/api/v1/agents",
            json={"name": "No Caps Agent"},
            headers=auth_headers,
        )

        # Filter for chat_completion — only Chat Agent
        resp = client.get("/api/v1/agents?capability=chat_completion", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Chat Agent"

        # Filter for image_generation — only Image Agent
        resp = client.get("/api/v1/agents?capability=image_generation", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Image Agent"

        # Filter for embeddings — only Chat Agent
        resp = client.get("/api/v1/agents?capability=embeddings", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Chat Agent"

    def test_filter_by_capability_no_match(self, client, auth_headers):
        """Filtering by a capability no agent has returns an empty list."""
        client.post(
            "/api/v1/agents",
            json={"name": "Basic Agent", "capabilities": ["chat"]},
            headers=auth_headers,
        )

        resp = client.get("/api/v1/agents?capability=nonexistent_capability", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_filter_by_capability_and_status(self, client, auth_headers):
        """Combining capability and status filters works."""
        client.post(
            "/api/v1/agents",
            json={"name": "Active Chat", "capabilities": ["chat"]},
            headers=auth_headers,
        )
        r2 = client.post(
            "/api/v1/agents",
            json={"name": "Revoked Chat", "capabilities": ["chat"]},
            headers=auth_headers,
        )
        # Revoke the second one
        revoke_id = r2.json()["agent"]["id"]
        client.delete(f"/api/v1/agents/{revoke_id}", headers=auth_headers)

        # Filter: capability=chat + status=active → only Active Chat
        resp = client.get("/api/v1/agents?capability=chat&status=active", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Active Chat"

    def test_create_capabilities_invalid_type(self, client, auth_headers):
        """Sending a string instead of a list for capabilities returns 422."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Bad Caps", "capabilities": "not_a_list"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_metadata_invalid_type(self, client, auth_headers):
        """Sending a string instead of a dict for metadata returns 422."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Bad Meta", "metadata": "not_a_dict"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_capabilities_invalid_type(self, client, auth_headers):
        """Sending a string instead of a list for capabilities in update returns 422."""
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Bad Update Caps"},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"capabilities": "not_a_list"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_metadata_invalid_type(self, client, auth_headers):
        """Sending a string instead of a dict for metadata in update returns 422."""
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Bad Update Meta"},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"metadata": ["not", "a", "dict"]},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ── EU AI Act risk class (Annex III) ────────────────────────────────────


class TestEuAiActRiskClass:
    """Agent.eu_ai_act_risk_class — dependency of #273 compliance export."""

    def test_create_without_risk_class_defaults_to_null(self, client, auth_headers):
        """Omitting the field leaves the agent unclassified."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Unclassified"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["agent"]["eu_ai_act_risk_class"] is None

    def test_create_with_annex_iii_category(self, client, auth_headers):
        """Valid Annex III codes are accepted and persisted."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "HR Screening Bot", "eu_ai_act_risk_class": "4(a)"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["agent"]["eu_ai_act_risk_class"] == "4(a)"

    def test_create_with_not_in_scope_sentinel(self, client, auth_headers):
        """'not_in_scope' is the explicit 'evaluated and out of scope' marker."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Internal Tool", "eu_ai_act_risk_class": "not_in_scope"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["agent"]["eu_ai_act_risk_class"] == "not_in_scope"

    def test_create_with_invalid_risk_class_returns_422(self, client, auth_headers):
        """Unknown codes are rejected before the DB is touched."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Bad Class", "eu_ai_act_risk_class": "9(z)"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_with_freeform_text_returns_422(self, client, auth_headers):
        """The field is not a freeform description — validation is strict."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Freeform", "eu_ai_act_risk_class": "high-risk"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_sets_risk_class(self, client, auth_headers):
        """PUT can set a classification on a previously-unclassified agent."""
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Classify Later"},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"eu_ai_act_risk_class": "3(a)"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["eu_ai_act_risk_class"] == "3(a)"

    def test_update_rejects_invalid_risk_class(self, client, auth_headers):
        """PUT validates the same allowlist as POST."""
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Bad Update"},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"eu_ai_act_risk_class": "ANNEX_III_3A"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_get_returns_risk_class(self, client, auth_headers):
        """GET surfaces the stored classification for export builder consumers."""
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Credit Scoring", "eu_ai_act_risk_class": "5(b)"},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["eu_ai_act_risk_class"] == "5(b)"


# ── Change-log v2.1 enrichment ──────────────────────────────────────────


class TestChangeLogV21Enrichment:
    """Source context + diff enrichment on agent lifecycle audit writes.

    See docs/specs/change-log-export-schema-v2.md §Source context and
    §Change payload. These assertions land on the raw AuditLog row
    because the export builder is already covered in
    common/tests/test_compliance_soc2.py.
    """

    def _lifecycle_entry(self, db_session, agent_id: str, action_type: str) -> AuditLog:
        """Fetch the most recent lifecycle audit row for an agent.

        Uses a Python-side filter on request_metadata because tests run
        against SQLite (no JSONB ``.astext`` operator); production runs
        Postgres and the export builder uses JSON path querying directly.
        """
        rows = (
            db_session.query(AuditLog)
            .filter(AuditLog.agent_id == uuid.UUID(agent_id))
            .order_by(AuditLog.id.desc())
            .all()
        )
        for row in rows:
            if (row.request_metadata or {}).get("action_type") == action_type:
                return row
        return None

    def test_create_records_ip_and_user_agent(self, client, auth_headers, db_session):
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Context Agent"},
            headers={**auth_headers, "user-agent": "ai-identity-test/1.0"},
        )
        agent_id = resp.json()["agent"]["id"]
        entry = self._lifecycle_entry(db_session, agent_id, "agent_created")
        # TestClient sets client.host to "testclient" by default.
        assert entry.request_metadata["ip_address"]
        assert entry.request_metadata["user_agent"] == "ai-identity-test/1.0"

    def test_update_records_ip_user_agent_and_diff(self, client, auth_headers, db_session):
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Before Name", "capabilities": ["old"]},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"name": "After Name", "capabilities": ["new"]},
            headers={**auth_headers, "user-agent": "diff-test/2.0"},
        )
        assert resp.status_code == 200

        entry = self._lifecycle_entry(db_session, agent_id, "agent_updated")
        meta = entry.request_metadata
        assert meta["user_agent"] == "diff-test/2.0"
        assert meta["ip_address"]
        diff = meta["diff"]
        assert diff["name"] == {"before": "Before Name", "after": "After Name"}
        assert diff["capabilities"] == {"before": ["old"], "after": ["new"]}
        # Unchanged fields must not appear in the diff.
        assert "description" not in diff
        assert "eu_ai_act_risk_class" not in diff

    def test_update_with_no_effective_change_omits_diff(self, client, auth_headers, db_session):
        """Setting a field to its current value should produce an empty diff.

        The writer then omits the `diff` key entirely so auditors don't
        see noise rows. The `agent_updated` entry still records ip/ua.
        """
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "Same Name"},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"name": "Same Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        entry = self._lifecycle_entry(db_session, agent_id, "agent_updated")
        assert "diff" not in entry.request_metadata
        assert "ip_address" in entry.request_metadata

    def test_delete_records_ip_and_user_agent(self, client, auth_headers, db_session):
        create_resp = client.post(
            "/api/v1/agents",
            json={"name": "To Delete"},
            headers=auth_headers,
        )
        agent_id = create_resp.json()["agent"]["id"]

        resp = client.delete(
            f"/api/v1/agents/{agent_id}",
            headers={**auth_headers, "user-agent": "revoke-test/1.0"},
        )
        assert resp.status_code == 200

        entry = self._lifecycle_entry(db_session, agent_id, "agent_revoked")
        assert entry.request_metadata["user_agent"] == "revoke-test/1.0"
        assert entry.request_metadata["ip_address"]
        # Original promoted fields must still be present.
        assert entry.request_metadata["old_status"] == "active"
        assert entry.request_metadata["new_status"] == "revoked"

    def test_request_id_captured_from_middleware(self, client, auth_headers, db_session):
        """v2.1.1: request.state.request_id (set by middleware) lands in
        the change_log. correlation_id continues to come from the
        denormalized top-level AuditLog column.
        """
        resp = client.post(
            "/api/v1/agents",
            json={"name": "ReqID Agent"},
            headers=auth_headers,
        )
        agent_id = resp.json()["agent"]["id"]
        entry = self._lifecycle_entry(db_session, agent_id, "agent_created")
        # Middleware always sets request_id; we just need it non-empty
        # and a hex-shaped string (8 chars per main.py's slicing).
        request_id = entry.request_metadata["request_id"]
        assert request_id, "request_id should be populated by middleware"
        assert len(request_id) == 8
        int(request_id, 16)  # raises if not hex

    def test_x_forwarded_for_wins_over_client_host(self, client, auth_headers, db_session):
        """Behind a load balancer, X-Forwarded-For gives the real client IP."""
        resp = client.post(
            "/api/v1/agents",
            json={"name": "Proxy Test"},
            headers={
                **auth_headers,
                "x-forwarded-for": "203.0.113.7, 10.0.0.1",
                "user-agent": "xff-test/1.0",
            },
        )
        agent_id = resp.json()["agent"]["id"]
        entry = self._lifecycle_entry(db_session, agent_id, "agent_created")
        assert entry.request_metadata["ip_address"] == "203.0.113.7"
