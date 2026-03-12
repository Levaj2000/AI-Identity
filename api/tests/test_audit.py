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
        assert data["total"] == 2
        assert len(data["items"]) == 2
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
        assert data["total_entries"] == 3
        assert data["entries_verified"] == 3
