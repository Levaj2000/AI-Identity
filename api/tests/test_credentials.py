"""Integration tests for upstream credential CRUD — api/app/routers/credentials.py.

Tests the full HTTP stack via FastAPI TestClient:
  - Create, list, get, rotate, revoke encrypted credentials
  - Master key rotation (re-encrypt all active credentials)
  - Security: DB contains only ciphertext, responses never include encrypted_key

Uses in-memory SQLite with the same conftest.py fixtures as other API tests.
"""

import uuid

import pytest
from cryptography.fernet import Fernet

from api.tests.conftest import TEST_AGENT_ID, TEST_API_KEY, _create_test_agent
from common.config.settings import settings
from common.crypto.fernet import decrypt_credential
from common.models import UpstreamCredential

# ── Fixtures ─────────────────────────────────────────────────────────────

# Store the test encryption key at module level so it's accessible in helpers
_TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def _set_encryption_key():
    """Set a valid Fernet master key for credential tests."""
    object.__setattr__(settings, "credential_encryption_key", _TEST_ENCRYPTION_KEY)
    yield
    object.__setattr__(settings, "credential_encryption_key", "")


@pytest.fixture
def test_agent(db_session, test_user):
    """Pre-created active agent for credential tests."""
    return _create_test_agent(db_session, test_user, agent_id=TEST_AGENT_ID)


@pytest.fixture
def auth_headers():
    """Default auth headers for the test user."""
    return {"X-API-Key": TEST_API_KEY}


def _create_credential(client, auth_headers, agent_id=None, provider="openai", api_key=None):
    """Helper to create a credential via the API and return the response."""
    aid = agent_id or TEST_AGENT_ID
    return client.post(
        f"/api/v1/agents/{aid}/credentials",
        headers=auth_headers,
        json={
            "provider": provider,
            "api_key": api_key or "sk-proj-testkey1234567890",
            "label": f"Test {provider} Key",
        },
    )


# ── TestCreateCredential ─────────────────────────────────────────────────


class TestCreateCredential:
    def test_create_credential_success(self, client, auth_headers, test_agent):
        resp = _create_credential(client, auth_headers)
        assert resp.status_code == 201

        data = resp.json()
        assert data["message"] == "Credential encrypted and stored successfully"
        cred = data["credential"]
        assert cred["provider"] == "openai"
        assert cred["status"] == "active"
        assert cred["key_prefix"] == "sk-proj-"
        assert cred["label"] == "Test openai Key"
        assert cred["agent_id"] == str(TEST_AGENT_ID)

    def test_create_credential_stored_encrypted(self, client, auth_headers, test_agent, db_session):
        """The DB should contain ciphertext, not the plaintext key."""
        plaintext = "sk-proj-PLAINTEXT-VISIBLE-KEY"
        _create_credential(client, auth_headers, api_key=plaintext)

        cred = db_session.query(UpstreamCredential).first()
        assert cred is not None
        # encrypted_key must NOT be the plaintext
        assert cred.encrypted_key != plaintext
        assert plaintext not in cred.encrypted_key
        # But it should decrypt to the plaintext
        decrypted = decrypt_credential(cred.encrypted_key, settings.credential_encryption_key)
        assert decrypted == plaintext

    def test_create_credential_key_prefix_matches(self, client, auth_headers, test_agent):
        """key_prefix should be the first 8 chars of the submitted api_key."""
        api_key = "sk-test-abcdefghijk"
        resp = _create_credential(client, auth_headers, api_key=api_key)
        assert resp.json()["credential"]["key_prefix"] == "sk-test-"

    def test_create_credential_no_master_key(self, client, auth_headers, test_agent):
        """Without encryption key, creation should fail with 500."""
        object.__setattr__(settings, "credential_encryption_key", "")
        resp = _create_credential(client, auth_headers)
        assert resp.status_code == 500

    def test_create_credential_wrong_agent(self, client, auth_headers, test_agent, other_user):
        """Cannot create credentials for another user's agent."""
        other_agent_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        resp = _create_credential(client, auth_headers, agent_id=other_agent_id)
        assert resp.status_code == 404

    def test_create_credential_nonexistent_agent(self, client, auth_headers, test_user):
        """404 for nonexistent agent (test_user exists but no agent)."""
        fake_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        resp = _create_credential(client, auth_headers, agent_id=fake_id)
        assert resp.status_code == 404

    def test_create_multiple_per_agent(self, client, auth_headers, test_agent):
        """An agent can have multiple credentials."""
        resp1 = _create_credential(
            client, auth_headers, provider="openai", api_key="sk-proj-key1xxxx"
        )
        resp2 = _create_credential(
            client, auth_headers, provider="anthropic", api_key="sk-ant-key2xxxxx"
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["credential"]["id"] != resp2.json()["credential"]["id"]


# ── TestListCredentials ──────────────────────────────────────────────────


class TestListCredentials:
    def test_list_empty(self, client, auth_headers, test_agent):
        resp = client.get(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_populated(self, client, auth_headers, test_agent):
        _create_credential(client, auth_headers, provider="openai", api_key="sk-proj-key1xxxx")
        _create_credential(client, auth_headers, provider="anthropic", api_key="sk-ant-key2xxxxx")

        resp = client.get(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_filter_by_status(self, client, auth_headers, test_agent):
        _create_credential(client, auth_headers, api_key="sk-proj-key1xxxx")

        # Revoke it
        resp = client.get(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials",
            headers=auth_headers,
        )
        cred_id = resp.json()["items"][0]["id"]
        client.delete(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/{cred_id}",
            headers=auth_headers,
        )

        # Filter by active — should be empty
        resp = client.get(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials?status=active",
            headers=auth_headers,
        )
        assert resp.json()["total"] == 0

        # Filter by revoked — should have 1
        resp = client.get(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials?status=revoked",
            headers=auth_headers,
        )
        assert resp.json()["total"] == 1

    def test_list_never_contains_encrypted_key(self, client, auth_headers, test_agent):
        """The encrypted_key field must NEVER appear in API responses."""
        _create_credential(client, auth_headers, api_key="sk-proj-key1xxxx")

        resp = client.get(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials",
            headers=auth_headers,
        )
        for item in resp.json()["items"]:
            assert "encrypted_key" not in item


# ── TestGetCredential ────────────────────────────────────────────────────


class TestGetCredential:
    def test_get_credential(self, client, auth_headers, test_agent):
        create_resp = _create_credential(client, auth_headers)
        cred_id = create_resp.json()["credential"]["id"]

        resp = client.get(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/{cred_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == cred_id
        assert "encrypted_key" not in resp.json()

    def test_get_credential_not_found(self, client, auth_headers, test_agent):
        resp = client.get(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/99999",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ── TestRotateCredential ─────────────────────────────────────────────────


class TestRotateCredential:
    def test_rotate_credential_success(self, client, auth_headers, test_agent, db_session):
        """Rotating replaces the encrypted key and updates key_prefix."""
        create_resp = _create_credential(client, auth_headers, api_key="sk-proj-oldkey12")
        cred_id = create_resp.json()["credential"]["id"]

        new_key = "sk-new--replacementkey"
        resp = client.put(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/{cred_id}/rotate",
            headers=auth_headers,
            json={"api_key": new_key},
        )
        assert resp.status_code == 200
        assert resp.json()["key_prefix"] == "sk-new--"

        # Verify DB has new encrypted value
        db_session.expire_all()
        cred = db_session.query(UpstreamCredential).filter_by(id=cred_id).first()
        decrypted = decrypt_credential(cred.encrypted_key, settings.credential_encryption_key)
        assert decrypted == new_key

    def test_rotate_ciphertext_changes(self, client, auth_headers, test_agent, db_session):
        """The DB ciphertext should change after rotation."""
        create_resp = _create_credential(client, auth_headers, api_key="sk-proj-oldcrypt1")
        cred_id = create_resp.json()["credential"]["id"]

        old_ciphertext = (
            db_session.query(UpstreamCredential).filter_by(id=cred_id).first()
        ).encrypted_key

        client.put(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/{cred_id}/rotate",
            headers=auth_headers,
            json={"api_key": "sk-proj-newcrypt1"},
        )

        db_session.expire_all()
        new_ciphertext = (
            db_session.query(UpstreamCredential).filter_by(id=cred_id).first()
        ).encrypted_key
        assert new_ciphertext != old_ciphertext

    def test_rotate_revoked_credential_fails(self, client, auth_headers, test_agent):
        """Cannot rotate a revoked credential."""
        create_resp = _create_credential(client, auth_headers, api_key="sk-proj-willrevk")
        cred_id = create_resp.json()["credential"]["id"]

        # Revoke first
        client.delete(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/{cred_id}",
            headers=auth_headers,
        )

        resp = client.put(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/{cred_id}/rotate",
            headers=auth_headers,
            json={"api_key": "sk-proj-newnew12"},
        )
        assert resp.status_code == 400


# ── TestRevokeCredential ─────────────────────────────────────────────────


class TestRevokeCredential:
    def test_revoke_credential(self, client, auth_headers, test_agent):
        create_resp = _create_credential(client, auth_headers)
        cred_id = create_resp.json()["credential"]["id"]

        resp = client.delete(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/{cred_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

    def test_revoke_already_revoked(self, client, auth_headers, test_agent):
        create_resp = _create_credential(client, auth_headers)
        cred_id = create_resp.json()["credential"]["id"]

        client.delete(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/{cred_id}",
            headers=auth_headers,
        )
        resp = client.delete(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/{cred_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 400


# ── TestMasterKeyRotation ────────────────────────────────────────────────


class TestMasterKeyRotation:
    def test_rotate_master_key_success(self, client, auth_headers, test_agent):
        """All active credentials should be re-encrypted with the new key."""
        _create_credential(client, auth_headers, api_key="sk-proj-key1xxxx")
        _create_credential(client, auth_headers, provider="anthropic", api_key="sk-ant-key2xxxxx")

        new_key = Fernet.generate_key().decode()
        resp = client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/rotate-master-key",
            headers=auth_headers,
            json={"new_master_key": new_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["credentials_re_encrypted"] == 2

    def test_rotate_master_key_invalid(self, client, auth_headers, test_agent):
        """Invalid new master key should return 400."""
        resp = client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/rotate-master-key",
            headers=auth_headers,
            json={"new_master_key": "not-a-valid-fernet-key-but-long-enough-to-pass-min-length"},
        )
        assert resp.status_code == 400

    def test_rotate_master_key_verify_decryption(
        self, client, auth_headers, test_agent, db_session
    ):
        """After rotation, credentials should decrypt with the new key."""
        plaintext = "sk-proj-verifyrotation"
        _create_credential(client, auth_headers, api_key=plaintext)

        new_key = Fernet.generate_key().decode()
        client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/credentials/rotate-master-key",
            headers=auth_headers,
            json={"new_master_key": new_key},
        )

        db_session.expire_all()
        cred = db_session.query(UpstreamCredential).first()
        decrypted = decrypt_credential(cred.encrypted_key, new_key)
        assert decrypted == plaintext
