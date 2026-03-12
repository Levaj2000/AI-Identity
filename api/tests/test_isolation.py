"""Cross-tenant data isolation tests — Sprint Item #51.

Verifies that no API endpoint leaks data across user boundaries.
Every cross-tenant access must return 404 (not 403) to prevent
agent enumeration attacks.

These tests fill coverage gaps not covered by existing test files:
  - test_agents.py covers list isolation + get other user
  - test_keys.py covers create/list/revoke other user
  - test_credentials.py covers create wrong agent

THIS file covers:
  - Agent: update + delete other user's agent → 404
  - Credential: list/get/rotate/revoke/master-key-rotate → 404
  - Audit: list returns only own entries; verify on other user → 404
"""

import uuid

import pytest
from cryptography.fernet import Fernet

from api.tests.conftest import TEST_AGENT_ID, TEST_API_KEY, _create_test_agent
from common.audit import create_audit_entry
from common.config.settings import settings

# Fixed UUIDs for deterministic tests
OTHER_AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")

OTHER_AUTH_HEADERS = {"X-API-Key": "other-user-api-key-87654321"}

_TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


# ── Shared Fixtures ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_encryption_key():
    """Set a valid Fernet master key for credential isolation tests."""
    object.__setattr__(settings, "credential_encryption_key", _TEST_ENCRYPTION_KEY)
    yield
    object.__setattr__(settings, "credential_encryption_key", "")


@pytest.fixture
def test_agent(db_session, test_user):
    """Agent owned by the primary test user."""
    return _create_test_agent(db_session, test_user, agent_id=TEST_AGENT_ID)


@pytest.fixture
def other_agent(db_session, other_user):
    """Agent owned by the OTHER user — primary user must NOT access this."""
    return _create_test_agent(db_session, other_user, agent_id=OTHER_AGENT_ID)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": TEST_API_KEY}


# ── Agent Isolation ─────────────────────────────────────────────────────


class TestAgentIsolation:
    """Update and delete on another user's agent must return 404."""

    def test_update_other_users_agent(self, client, auth_headers, other_agent):
        """PUT /agents/{id} for another user's agent → 404."""
        resp = client.put(
            f"/api/v1/agents/{OTHER_AGENT_ID}",
            json={"name": "Hijacked Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_delete_other_users_agent(self, client, auth_headers, other_agent):
        """DELETE /agents/{id} for another user's agent → 404."""
        resp = client.delete(
            f"/api/v1/agents/{OTHER_AGENT_ID}",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ── Credential Isolation ────────────────────────────────────────────────


class TestCredentialIsolation:
    """All credential endpoints must deny access to other user's agents."""

    def _create_other_user_credential(self, client, other_agent, db_session):
        """Helper: create a credential on the other user's agent directly in DB."""
        from common.crypto.fernet import encrypt_credential
        from common.models import CredentialStatus, UpstreamCredential, UpstreamProvider

        cred = UpstreamCredential(
            agent_id=OTHER_AGENT_ID,
            provider=UpstreamProvider.openai.value,
            encrypted_key=encrypt_credential("sk-test-other-user-key", _TEST_ENCRYPTION_KEY),
            key_prefix="sk-test-",
            label="Other user credential",
            status=CredentialStatus.active.value,
        )
        db_session.add(cred)
        db_session.commit()
        db_session.refresh(cred)
        return cred

    def test_list_credentials_other_user(self, client, auth_headers, other_agent, db_session):
        """GET /agents/{id}/credentials on other user's agent → 404."""
        self._create_other_user_credential(client, other_agent, db_session)

        resp = client.get(
            f"/api/v1/agents/{OTHER_AGENT_ID}/credentials",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_credential_other_user(self, client, auth_headers, other_agent, db_session):
        """GET /agents/{id}/credentials/{cred_id} on other user's agent → 404."""
        cred = self._create_other_user_credential(client, other_agent, db_session)

        resp = client.get(
            f"/api/v1/agents/{OTHER_AGENT_ID}/credentials/{cred.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_rotate_credential_other_user(self, client, auth_headers, other_agent, db_session):
        """PUT /agents/{id}/credentials/{id}/rotate on other user's agent → 404."""
        cred = self._create_other_user_credential(client, other_agent, db_session)

        resp = client.put(
            f"/api/v1/agents/{OTHER_AGENT_ID}/credentials/{cred.id}/rotate",
            json={"api_key": "sk-new-rotated-key-12345"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_revoke_credential_other_user(self, client, auth_headers, other_agent, db_session):
        """DELETE /agents/{id}/credentials/{id} on other user's agent → 404."""
        cred = self._create_other_user_credential(client, other_agent, db_session)

        resp = client.delete(
            f"/api/v1/agents/{OTHER_AGENT_ID}/credentials/{cred.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_master_key_rotate_other_user(self, client, auth_headers, other_agent, db_session):
        """POST /agents/{id}/credentials/rotate-master-key on other user's agent → 404."""
        self._create_other_user_credential(client, other_agent, db_session)
        new_key = Fernet.generate_key().decode()

        resp = client.post(
            f"/api/v1/agents/{OTHER_AGENT_ID}/credentials/rotate-master-key",
            json={"new_master_key": new_key},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ── Audit Log Isolation ─────────────────────────────────────────────────


class TestAuditLogIsolation:
    """Audit endpoints must scope to the authenticated user's agents only."""

    def test_list_audit_logs_only_own_entries(
        self, client, auth_headers, test_agent, other_agent, db_session
    ):
        """GET /audit returns entries for own agent only, not other user's."""
        # Create audit entries for both agents
        create_audit_entry(
            db_session,
            agent_id=TEST_AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
        )
        create_audit_entry(
            db_session,
            agent_id=OTHER_AGENT_ID,
            endpoint="/v1/embeddings",
            method="POST",
            decision="allow",
        )

        # Primary user should only see their own agent's entries
        resp = client.get("/api/v1/audit", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["agent_id"] == str(TEST_AGENT_ID)

    def test_verify_chain_other_users_agent(self, client, auth_headers, other_agent):
        """GET /audit/verify?agent_id=... for other user's agent → 404."""
        resp = client.get(
            f"/api/v1/audit/verify?agent_id={OTHER_AGENT_ID}",
            headers=auth_headers,
        )
        assert resp.status_code == 404
