"""Tests for append-only audit log with HMAC integrity chain.

SECURITY-CRITICAL: These tests verify that the audit log provides
tamper-evident, append-only storage for SOC 2 compliance.
"""

import uuid
from datetime import UTC

from common.audit import compute_entry_hash, create_audit_entry, verify_chain
from common.models import AuditLog

# Fixed UUIDs for deterministic tests
AGENT_ID_1 = uuid.UUID("00000000-0000-0000-0000-000000000010")
AGENT_ID_2 = uuid.UUID("00000000-0000-0000-0000-000000000020")


def _create_test_entry(db, agent_id=AGENT_ID_1, endpoint="/v1/chat", decision="allow"):
    """Helper to create audit entries for tests."""
    return create_audit_entry(
        db,
        agent_id=agent_id,
        endpoint=endpoint,
        method="POST",
        decision=decision,
        request_metadata={"model": "gpt-4"},
    )


# ── Audit Entry Creation ────────────────────────────────────────────────


class TestCreateAuditEntry:
    """Verify audit entries are created with correct HMAC chain linkage."""

    def test_create_entry_genesis(self, db_session):
        """First audit entry has prev_hash='GENESIS' and a valid entry_hash."""
        entry = _create_test_entry(db_session)

        assert entry.prev_hash == "GENESIS"
        assert len(entry.entry_hash) == 64  # SHA-256 hex digest
        assert entry.id is not None
        assert entry.created_at is not None

    def test_create_entry_chain(self, db_session):
        """Second entry's prev_hash equals first entry's entry_hash."""
        entry1 = _create_test_entry(db_session)
        entry2 = _create_test_entry(db_session, endpoint="/v1/embeddings")

        assert entry2.prev_hash == entry1.entry_hash
        assert entry2.entry_hash != entry1.entry_hash

    def test_create_entry_hash_deterministic(self, db_session):
        """Recomputing the hash from stored fields matches entry_hash."""
        entry = _create_test_entry(db_session)

        # SQLite returns naive datetimes — normalize to UTC for hash consistency
        created_at = entry.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        recomputed = compute_entry_hash(
            agent_id=entry.agent_id,
            endpoint=entry.endpoint,
            method=entry.method,
            decision=entry.decision,
            cost_estimate_usd=(
                float(entry.cost_estimate_usd) if entry.cost_estimate_usd is not None else None
            ),
            latency_ms=entry.latency_ms,
            request_metadata=entry.request_metadata,
            created_at=created_at,
            prev_hash=entry.prev_hash,
        )
        assert recomputed == entry.entry_hash

    def test_create_entry_different_data_different_hash(self, db_session):
        """Changing any data field produces a different hash."""
        entry1 = _create_test_entry(db_session, decision="allow")
        entry2 = _create_test_entry(db_session, decision="deny")

        # entry2's hash differs because decision changed (and prev_hash changed)
        assert entry1.entry_hash != entry2.entry_hash


# ── Chain Verification ───────────────────────────────────────────────────


class TestVerifyChain:
    """Verify the integrity chain catches tampering and deletions."""

    def test_verify_empty_table(self, db_session):
        """Verifying an empty table returns valid=True, total_entries=0."""
        result = verify_chain(db_session)

        assert result.valid is True
        assert result.total_entries == 0
        assert result.entries_verified == 0

    def test_verify_intact_chain(self, db_session):
        """Chain with 5 entries verifies successfully."""
        for i in range(5):
            _create_test_entry(db_session, endpoint=f"/v1/endpoint-{i}")

        result = verify_chain(db_session)

        assert result.valid is True
        assert result.total_entries == 5
        assert result.entries_verified == 5
        assert result.message == "Chain integrity verified"

    def test_verify_detects_tampered_hash(self, db_session):
        """Tampering with an entry_hash is detected."""
        _create_test_entry(db_session)
        entry2 = _create_test_entry(db_session, endpoint="/v1/tampered")
        _create_test_entry(db_session, endpoint="/v1/after-tamper")

        # Tamper with entry2's hash directly in DB (SQLite allows this)
        db_session.execute(
            AuditLog.__table__.update()
            .where(AuditLog.id == entry2.id)
            .values(entry_hash="deadbeef" * 8)
        )
        db_session.commit()

        result = verify_chain(db_session)

        assert result.valid is False
        assert result.first_broken_id == entry2.id
        assert "Hash mismatch" in result.message

    def test_verify_detects_broken_chain(self, db_session):
        """Deleting an entry from the middle breaks the chain."""
        _create_test_entry(db_session)
        entry2 = _create_test_entry(db_session, endpoint="/v1/middle")
        _create_test_entry(db_session, endpoint="/v1/after-delete")

        # Delete middle entry directly (SQLite allows this)
        db_session.execute(AuditLog.__table__.delete().where(AuditLog.id == entry2.id))
        db_session.commit()

        result = verify_chain(db_session)

        assert result.valid is False
        assert "Chain broken" in result.message

    def test_verify_per_agent_filter(self, db_session):
        """Per-agent verification checks only that agent's hashes."""
        # Interleave entries from two agents
        _create_test_entry(db_session, agent_id=AGENT_ID_1, endpoint="/v1/a1-1")
        _create_test_entry(db_session, agent_id=AGENT_ID_2, endpoint="/v1/a2-1")
        _create_test_entry(db_session, agent_id=AGENT_ID_1, endpoint="/v1/a1-2")

        result = verify_chain(db_session, agent_id=AGENT_ID_1)

        assert result.valid is True
        assert result.entries_verified == 2  # Only agent_1's entries


# ── Audit Endpoints ──────────────────────────────────────────────────────


class TestAuditEndpoints:
    """Verify the audit REST endpoints return correct responses."""

    def _create_agent(self, client, auth_headers, name="Audit Test Agent"):
        """Helper to create an agent and return its ID."""
        resp = client.post("/api/v1/agents", headers=auth_headers, json={"name": name})
        return resp.json()["agent"]["id"]

    def test_list_audit_logs(self, client, auth_headers, db_session):
        """GET /api/v1/audit returns paginated entries for user's agents."""
        agent_id = self._create_agent(client, auth_headers)

        # Create audit entries for this agent
        create_audit_entry(
            db_session,
            agent_id=uuid.UUID(agent_id),
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
        )
        create_audit_entry(
            db_session,
            agent_id=uuid.UUID(agent_id),
            endpoint="/v1/embeddings",
            method="POST",
            decision="deny",
        )

        resp = client.get("/api/v1/audit", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        # 2 manual entries + 1 from agent creation audit trail
        assert data["total"] == 3
        assert len(data["items"]) == 3
        # Check integrity fields are present
        assert "entry_hash" in data["items"][0]
        assert "prev_hash" in data["items"][0]

    def test_verify_endpoint_intact(self, client, auth_headers, db_session):
        """GET /api/v1/audit/verify returns valid=True for intact chain."""
        agent_id = self._create_agent(client, auth_headers)

        # Create a small chain
        for i in range(3):
            create_audit_entry(
                db_session,
                agent_id=uuid.UUID(agent_id),
                endpoint=f"/v1/endpoint-{i}",
                method="GET",
                decision="allow",
            )

        resp = client.get("/api/v1/audit/verify", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        # 3 manual entries + 1 from agent creation audit trail
        assert data["total_entries"] == 4
        assert data["entries_verified"] == 4


# ── Forensics Endpoints ─────────────────────────────────────────────────


class TestForensicsEndpoints:
    """Verify the AI Forensics API endpoints."""

    def _create_agent(self, client, auth_headers, name="Forensics Test Agent"):
        """Helper to create an agent and return its ID."""
        resp = client.post("/api/v1/agents", headers=auth_headers, json={"name": name})
        return resp.json()["agent"]["id"]

    def _seed_entries(self, db_session, agent_id, count=5):
        """Create a mix of audit entries for testing."""
        decisions = ["allow", "allow", "deny", "allow", "error"]
        endpoints = ["/v1/chat", "/v1/embeddings", "/v1/chat", "/v1/completions", "/v1/chat"]
        for i in range(count):
            create_audit_entry(
                db_session,
                agent_id=uuid.UUID(agent_id),
                endpoint=endpoints[i % len(endpoints)],
                method="POST",
                decision=decisions[i % len(decisions)],
                cost_estimate_usd=0.01 * (i + 1),
                latency_ms=50 + i * 10,
            )

    def test_audit_stats(self, client, auth_headers, db_session):
        """GET /api/v1/audit/stats returns correct aggregated counts."""
        agent_id = self._create_agent(client, auth_headers)
        self._seed_entries(db_session, agent_id)

        resp = client.get("/api/v1/audit/stats", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        # 5 manual + 1 from agent creation = 6 total
        assert data["total_events"] == 6
        assert data["allowed_count"] >= 3
        assert data["denied_count"] >= 1
        assert data["total_cost_usd"] > 0
        assert len(data["top_endpoints"]) > 0

    def test_audit_stats_filtered_by_agent(self, client, auth_headers, db_session):
        """GET /api/v1/audit/stats scopes to specific agent."""
        agent_id = self._create_agent(client, auth_headers)
        self._seed_entries(db_session, agent_id)

        resp = client.get(
            f"/api/v1/audit/stats?agent_id={agent_id}",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 6  # 5 manual + 1 creation

    def test_audit_stats_wrong_agent(self, client, auth_headers):
        """GET /api/v1/audit/stats returns 404 for non-owned agent."""
        fake_id = uuid.uuid4()
        resp = client.get(
            f"/api/v1/audit/stats?agent_id={fake_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_audit_reconstruct(self, client, auth_headers, db_session):
        """GET /api/v1/audit/reconstruct returns events + chain + policy."""
        agent_id = self._create_agent(client, auth_headers)
        self._seed_entries(db_session, agent_id)

        # Create a policy for the agent
        client.post(
            f"/api/v1/agents/{agent_id}/policies",
            headers=auth_headers,
            json={"rules": {"allowed_endpoints": ["/v1/chat"]}},
        )

        resp = client.get(
            f"/api/v1/audit/reconstruct?agent_id={agent_id}"
            "&start_date=2020-01-01T00:00:00"
            "&end_date=2030-01-01T00:00:00",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == agent_id
        assert len(data["events"]) >= 5
        assert data["chain_verification"]["valid"] is True
        assert data["active_policy"] is not None
        assert data["stats"]["total_events"] >= 5

    def test_audit_reconstruct_wrong_agent(self, client, auth_headers):
        """GET /api/v1/audit/reconstruct returns 404 for non-owned agent."""
        fake_id = uuid.uuid4()
        resp = client.get(
            f"/api/v1/audit/reconstruct?agent_id={fake_id}"
            "&start_date=2020-01-01T00:00:00"
            "&end_date=2030-01-01T00:00:00",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_audit_report_json(self, client, auth_headers, db_session):
        """GET /api/v1/audit/report returns JSON forensics report."""
        agent_id = self._create_agent(client, auth_headers)
        self._seed_entries(db_session, agent_id)

        resp = client.get(
            f"/api/v1/audit/report?agent_id={agent_id}"
            "&start_date=2020-01-01T00:00:00"
            "&end_date=2030-01-01T00:00:00"
            "&format=json",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "report_id" in data
        assert data["agent"]["id"] == agent_id
        assert len(data["events"]) >= 5
        assert data["chain_verification"]["valid"] is True
        assert data["stats"]["total_events"] >= 5

    def test_audit_report_csv(self, client, auth_headers, db_session):
        """GET /api/v1/audit/report?format=csv returns CSV download."""
        agent_id = self._create_agent(client, auth_headers)
        self._seed_entries(db_session, agent_id)

        resp = client.get(
            f"/api/v1/audit/report?agent_id={agent_id}"
            "&start_date=2020-01-01T00:00:00"
            "&end_date=2030-01-01T00:00:00"
            "&format=csv",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        content = resp.text
        assert "id,agent_id,endpoint" in content
        assert "Chain Verification Certificate" in content

    def test_list_audit_logs_date_filter(self, client, auth_headers, db_session):
        """GET /api/v1/audit with start_date/end_date filters by time."""
        agent_id = self._create_agent(client, auth_headers)
        self._seed_entries(db_session, agent_id)

        # Future date should return no manual entries
        resp = client.get(
            "/api/v1/audit?start_date=2030-01-01T00:00:00",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_list_audit_logs_endpoint_filter(self, client, auth_headers, db_session):
        """GET /api/v1/audit with endpoint filter does partial match."""
        agent_id = self._create_agent(client, auth_headers)
        self._seed_entries(db_session, agent_id)

        resp = client.get(
            "/api/v1/audit?endpoint=chat",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        # Should find entries with /v1/chat endpoint
        assert data["total"] >= 1
        for item in data["items"]:
            assert "chat" in item["endpoint"]
