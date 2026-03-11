"""Tests for Agent Key management endpoints — create, list, revoke, rotate."""

import uuid
from datetime import UTC, datetime, timedelta

from common.auth.keys import hash_key
from common.models import AgentKey, KeyStatus


def _create_agent(client, auth_headers, name="Test Agent"):
    """Helper: create an agent and return (agent_id, initial_api_key)."""
    resp = client.post(
        "/api/v1/agents",
        json={"name": name},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    return data["agent"]["id"], data["api_key"]


# ── POST /api/v1/agents/{id}/keys ────────────────────────────────────────


class TestCreateKey:
    def test_create_key_success(self, client, auth_headers):
        """Creating a key returns 201 with show-once plaintext key."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()

        # Show-once plaintext key
        assert "api_key" in data
        assert data["api_key"].startswith("aid_sk_")

        # Key metadata
        key = data["key"]
        assert key["agent_id"] == agent_id
        assert key["status"] == "active"
        assert key["key_prefix"] == data["api_key"][:12]

    def test_create_key_hash_stored(self, client, auth_headers, db_session):
        """The key is stored as a SHA-256 hash, not plaintext."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys",
            headers=auth_headers,
        )
        plaintext_key = resp.json()["api_key"]
        key_id = resp.json()["key"]["id"]

        # Query the DB directly
        key_record = db_session.query(AgentKey).filter(AgentKey.id == key_id).first()
        assert key_record is not None
        assert key_record.key_hash != plaintext_key  # Not stored plaintext
        assert len(key_record.key_hash) == 64  # SHA-256 hex length
        assert key_record.key_hash == hash_key(plaintext_key)  # Hash matches

    def test_create_key_revoked_agent(self, client, auth_headers):
        """Cannot issue a key for a revoked agent."""
        agent_id, _ = _create_agent(client, auth_headers)
        client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_create_key_not_found(self, client, auth_headers):
        """Creating a key for a nonexistent agent returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/agents/{fake_id}/keys",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_create_key_other_user(self, client, auth_headers, other_user):
        """Cannot create a key for another user's agent."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys",
            headers={"X-API-Key": "other-user-api-key-87654321"},
        )
        assert resp.status_code == 404


# ── GET /api/v1/agents/{id}/keys ─────────────────────────────────────────


class TestListKeys:
    def test_list_keys_returns_prefix_not_hash(self, client, auth_headers):
        """Listed keys expose prefix and status, never the hash or plaintext."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.get(
            f"/api/v1/agents/{agent_id}/keys",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        key = data["items"][0]
        assert "key_prefix" in key
        assert "status" in key
        assert "created_at" in key
        # Must NOT contain secret fields
        assert "key_hash" not in key
        assert "api_key" not in key

    def test_list_keys_after_create(self, client, auth_headers):
        """Agent starts with 1 key; POST /keys adds another."""
        agent_id, _ = _create_agent(client, auth_headers)

        # Initially: 1 key from agent creation
        resp = client.get(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        assert resp.json()["total"] == 1

        # Create a second key
        client.post(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)

        # Now: 2 keys
        resp = client.get(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        assert resp.json()["total"] == 2

    def test_list_keys_status_filter(self, client, auth_headers):
        """Filtering by status works."""
        agent_id, _ = _create_agent(client, auth_headers)

        # Create a second key then revoke it
        create_resp = client.post(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        key_id = create_resp.json()["key"]["id"]
        client.delete(f"/api/v1/agents/{agent_id}/keys/{key_id}", headers=auth_headers)

        # Filter active — should be 1 (the initial key)
        resp = client.get(
            f"/api/v1/agents/{agent_id}/keys?status=active",
            headers=auth_headers,
        )
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["status"] == "active"

        # Filter revoked — should be 1 (the one we just revoked)
        resp = client.get(
            f"/api/v1/agents/{agent_id}/keys?status=revoked",
            headers=auth_headers,
        )
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["status"] == "revoked"

    def test_list_keys_other_user(self, client, auth_headers, other_user):
        """Cannot list keys for another user's agent."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.get(
            f"/api/v1/agents/{agent_id}/keys",
            headers={"X-API-Key": "other-user-api-key-87654321"},
        )
        assert resp.status_code == 404


# ── DELETE /api/v1/agents/{id}/keys/{key_id} ─────────────────────────────


class TestRevokeKey:
    def test_revoke_key_success(self, client, auth_headers):
        """Revoking a key sets status to revoked."""
        agent_id, _ = _create_agent(client, auth_headers)
        create_resp = client.post(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        key_id = create_resp.json()["key"]["id"]

        resp = client.delete(
            f"/api/v1/agents/{agent_id}/keys/{key_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

    def test_revoke_key_already_revoked(self, client, auth_headers):
        """Revoking an already-revoked key returns 400."""
        agent_id, _ = _create_agent(client, auth_headers)
        create_resp = client.post(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        key_id = create_resp.json()["key"]["id"]

        # Revoke once
        client.delete(f"/api/v1/agents/{agent_id}/keys/{key_id}", headers=auth_headers)
        # Revoke again
        resp = client.delete(f"/api/v1/agents/{agent_id}/keys/{key_id}", headers=auth_headers)
        assert resp.status_code == 400

    def test_revoke_key_not_found(self, client, auth_headers):
        """Revoking a nonexistent key returns 404."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.delete(
            f"/api/v1/agents/{agent_id}/keys/99999",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_revoke_key_other_user(self, client, auth_headers, other_user):
        """Cannot revoke a key on another user's agent."""
        agent_id, _ = _create_agent(client, auth_headers)
        create_resp = client.post(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        key_id = create_resp.json()["key"]["id"]

        resp = client.delete(
            f"/api/v1/agents/{agent_id}/keys/{key_id}",
            headers={"X-API-Key": "other-user-api-key-87654321"},
        )
        assert resp.status_code == 404


# ── Revoked Key Auth ─────────────────────────────────────────────────────


class TestRevokedKeyAuth:
    def test_revoked_key_hash_not_active(self, client, auth_headers, db_session):
        """A revoked key's hash is still in DB but marked revoked — cannot be used for auth."""
        agent_id, _ = _create_agent(client, auth_headers)
        create_resp = client.post(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        plaintext_key = create_resp.json()["api_key"]
        key_id = create_resp.json()["key"]["id"]

        # Revoke the key
        client.delete(f"/api/v1/agents/{agent_id}/keys/{key_id}", headers=auth_headers)

        # Verify: hash is in DB but status is revoked
        key_hash = hash_key(plaintext_key)
        key_record = db_session.query(AgentKey).filter(AgentKey.key_hash == key_hash).first()
        assert key_record is not None
        assert key_record.status == KeyStatus.revoked.value

        # An auth lookup for active keys would NOT find this key
        active_key = (
            db_session.query(AgentKey)
            .filter(
                AgentKey.key_hash == key_hash,
                AgentKey.status == KeyStatus.active.value,
            )
            .first()
        )
        assert active_key is None


# ── POST /api/v1/agents/{id}/keys/rotate ─────────────────────────────────


class TestRotateKey:
    def test_rotate_key_success(self, client, auth_headers):
        """Rotating returns 201 with new active key and old key set to rotated."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys/rotate",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()

        # New key
        assert data["api_key"].startswith("aid_sk_")
        assert data["new_key"]["status"] == "active"

        # Old key
        assert data["rotated_key"]["status"] == "rotated"
        assert data["rotated_key"]["expires_at"] is not None

    def test_rotate_key_new_key_differs(self, client, auth_headers):
        """The new key prefix differs from the rotated key prefix."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys/rotate",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["new_key"]["key_prefix"] != data["rotated_key"]["key_prefix"]

    def test_rotate_key_oldest_active_rotated(self, client, auth_headers):
        """With multiple active keys, the oldest one gets rotated."""
        agent_id, _ = _create_agent(client, auth_headers)

        # Create a second key — now we have 2 active keys
        second_resp = client.post(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        second_key_id = second_resp.json()["key"]["id"]

        # Before rotation: 2 active keys
        keys_resp = client.get(
            f"/api/v1/agents/{agent_id}/keys?status=active",
            headers=auth_headers,
        )
        assert keys_resp.json()["total"] == 2

        # Rotate — should rotate one key (the oldest by created_at ASC)
        rotate_resp = client.post(
            f"/api/v1/agents/{agent_id}/keys/rotate",
            headers=auth_headers,
        )
        rotated_key_id = rotate_resp.json()["rotated_key"]["id"]
        assert rotate_resp.json()["rotated_key"]["status"] == "rotated"

        # After rotation: the second key and the new key should be active
        # The rotated key should not be active
        keys_after = client.get(
            f"/api/v1/agents/{agent_id}/keys?status=active",
            headers=auth_headers,
        )
        active_ids = [k["id"] for k in keys_after.json()["items"]]
        assert second_key_id in active_ids
        assert rotated_key_id not in active_ids

    def test_rotate_key_grace_period(self, client, auth_headers, db_session):
        """Old key still has status=rotated (not revoked) within grace period."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys/rotate",
            headers=auth_headers,
        )
        old_key_id = resp.json()["rotated_key"]["id"]

        # Check DB: old key is rotated with future expiry
        key_record = db_session.query(AgentKey).filter(AgentKey.id == old_key_id).first()
        assert key_record.status == KeyStatus.rotated.value
        # SQLite stores naive datetimes, so compare naively
        now_naive = datetime.utcnow()
        expires = (
            key_record.expires_at.replace(tzinfo=None)
            if key_record.expires_at.tzinfo
            else key_record.expires_at
        )
        assert expires > now_naive

    def test_rotate_key_expired_auto_revoked(self, client, auth_headers, db_session):
        """After grace period expires, the rotated key is auto-revoked on next list call."""
        agent_id, _ = _create_agent(client, auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys/rotate",
            headers=auth_headers,
        )
        old_key_id = resp.json()["rotated_key"]["id"]

        # Simulate expiry: set expires_at to the past
        key_record = db_session.query(AgentKey).filter(AgentKey.id == old_key_id).first()
        key_record.expires_at = datetime.now(UTC) - timedelta(hours=1)
        db_session.commit()

        # Listing keys triggers cleanup
        list_resp = client.get(
            f"/api/v1/agents/{agent_id}/keys",
            headers=auth_headers,
        )
        # Find the old key in the list — should now be revoked
        old_key_data = next(k for k in list_resp.json()["items"] if k["id"] == old_key_id)
        assert old_key_data["status"] == "revoked"

    def test_rotate_key_revoked_agent(self, client, auth_headers):
        """Cannot rotate keys for a revoked agent."""
        agent_id, _ = _create_agent(client, auth_headers)
        client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys/rotate",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_rotate_key_no_active_key(self, client, auth_headers):
        """Cannot rotate when there are no active keys."""
        agent_id, _ = _create_agent(client, auth_headers)

        # Get the initial key and revoke it
        keys_resp = client.get(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        key_id = keys_resp.json()["items"][0]["id"]
        client.delete(f"/api/v1/agents/{agent_id}/keys/{key_id}", headers=auth_headers)

        resp = client.post(
            f"/api/v1/agents/{agent_id}/keys/rotate",
            headers=auth_headers,
        )
        assert resp.status_code == 400
