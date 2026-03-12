"""Tests for agent key type separation (aid_sk_ vs aid_admin_).

Verifies that:
  - Runtime keys (aid_sk_) are created by default
  - Admin keys (aid_admin_) can be explicitly created
  - Key type is returned in API responses
  - Rotation preserves the key type
  - Key type detection from prefix works
"""

import uuid

from common.auth.keys import detect_key_type, generate_api_key, validate_key_format
from common.config.settings import settings
from common.models import AgentKey, KeyType

# ── Key Generation Tests ────────────────────────────────────────────


class TestKeyGeneration:
    """Test that key generation produces correct prefixes for each type."""

    def test_runtime_key_has_sk_prefix(self):
        key = generate_api_key(key_type="runtime")
        assert key.startswith(settings.api_key_prefix)
        assert key.startswith("aid_sk_")

    def test_admin_key_has_admin_prefix(self):
        key = generate_api_key(key_type="admin")
        assert key.startswith(settings.admin_key_prefix)
        assert key.startswith("aid_admin_")

    def test_default_key_type_is_runtime(self):
        key = generate_api_key()
        assert key.startswith("aid_sk_")

    def test_both_key_types_pass_validation(self):
        runtime = generate_api_key(key_type="runtime")
        admin = generate_api_key(key_type="admin")
        assert validate_key_format(runtime)
        assert validate_key_format(admin)

    def test_runtime_keys_are_unique(self):
        keys = {generate_api_key(key_type="runtime") for _ in range(10)}
        assert len(keys) == 10

    def test_admin_keys_are_unique(self):
        keys = {generate_api_key(key_type="admin") for _ in range(10)}
        assert len(keys) == 10


# ── Key Type Detection Tests ────────────────────────────────────────


class TestKeyTypeDetection:
    """Test that key type can be detected from prefix."""

    def test_detect_runtime_key(self):
        key = generate_api_key(key_type="runtime")
        assert detect_key_type(key) == "runtime"

    def test_detect_admin_key(self):
        key = generate_api_key(key_type="admin")
        assert detect_key_type(key) == "admin"

    def test_detect_unknown_prefix_raises(self):
        import pytest

        with pytest.raises(ValueError, match="Unrecognized key prefix"):
            detect_key_type("unknown_prefix_abc123")


# ── API Key Creation Tests ──────────────────────────────────────────


class TestKeyCreationAPI:
    """Test key creation endpoint with key_type parameter."""

    def test_create_runtime_key_default(self, client, auth_headers, test_user, db_session):
        """Default key type is runtime."""
        from api.tests.conftest import TEST_AGENT_ID, _create_test_agent

        _create_test_agent(db_session, test_user)

        resp = client.post(f"/api/v1/agents/{TEST_AGENT_ID}/keys", headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["key"]["key_type"] == "runtime"
        assert data["api_key"].startswith("aid_sk_")

    def test_create_runtime_key_explicit(self, client, auth_headers, test_user, db_session):
        """Explicit runtime key type."""
        from api.tests.conftest import TEST_AGENT_ID, _create_test_agent

        _create_test_agent(db_session, test_user)

        resp = client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/keys?key_type=runtime",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["key"]["key_type"] == "runtime"
        assert data["api_key"].startswith("aid_sk_")

    def test_create_admin_key(self, client, auth_headers, test_user, db_session):
        """Admin key creation with aid_admin_ prefix."""
        from api.tests.conftest import TEST_AGENT_ID, _create_test_agent

        _create_test_agent(db_session, test_user)

        resp = client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/keys?key_type=admin",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["key"]["key_type"] == "admin"
        assert data["api_key"].startswith("aid_admin_")

    def test_invalid_key_type_rejected(self, client, auth_headers, test_user, db_session):
        """Invalid key type returns 422."""
        from api.tests.conftest import TEST_AGENT_ID, _create_test_agent

        _create_test_agent(db_session, test_user)

        resp = client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/keys?key_type=superadmin",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_list_keys_shows_type(self, client, auth_headers, test_user, db_session):
        """Key type is visible in list response."""
        from api.tests.conftest import TEST_AGENT_ID, _create_test_agent

        _create_test_agent(db_session, test_user)

        # Create one of each type
        client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/keys?key_type=runtime",
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/keys?key_type=admin",
            headers=auth_headers,
        )

        resp = client.get(f"/api/v1/agents/{TEST_AGENT_ID}/keys", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        types = {k["key_type"] for k in data["items"]}
        # Initial key (runtime) + 2 new keys = we should see both types
        assert "runtime" in types
        assert "admin" in types


# ── Key Rotation Tests ──────────────────────────────────────────────


class TestKeyRotationPreservesType:
    """Test that key rotation preserves the key_type of the old key."""

    def test_rotate_runtime_key_stays_runtime(
        self, client, auth_headers, test_user, db_session
    ):
        """Rotating a runtime key produces a new runtime key."""
        from api.tests.conftest import TEST_AGENT_ID, _create_test_agent

        _create_test_agent(db_session, test_user)

        resp = client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/keys/rotate",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["new_key"]["key_type"] == "runtime"
        assert data["api_key"].startswith("aid_sk_")

    def test_rotate_admin_key_stays_admin(
        self, client, auth_headers, test_user, db_session
    ):
        """Rotating an admin key produces a new admin key."""
        from api.tests.conftest import TEST_AGENT_ID, _create_test_agent

        _create_test_agent(db_session, test_user)

        # First, revoke the initial runtime key so admin becomes the oldest active
        initial_keys = (
            db_session.query(AgentKey)
            .filter(AgentKey.agent_id == uuid.UUID(str(TEST_AGENT_ID)))
            .all()
        )
        for k in initial_keys:
            k.status = "revoked"
        db_session.commit()

        # Create an admin key
        resp = client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/keys?key_type=admin",
            headers=auth_headers,
        )
        assert resp.status_code == 201

        # Rotate it — should stay admin
        resp = client.post(
            f"/api/v1/agents/{TEST_AGENT_ID}/keys/rotate",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["new_key"]["key_type"] == "admin"
        assert data["api_key"].startswith("aid_admin_")


# ── Agent Creation Tests ────────────────────────────────────────────


class TestAgentCreationKeyType:
    """Test that agent creation always issues a runtime key."""

    def test_agent_creation_key_is_runtime(self, client, auth_headers):
        resp = client.post(
            "/api/v1/agents",
            headers=auth_headers,
            json={"name": "New Agent"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["api_key"].startswith("aid_sk_")


# ── KeyType Model Tests ─────────────────────────────────────────────


class TestKeyTypeEnum:
    """Test the KeyType enum."""

    def test_enum_values(self):
        assert KeyType.runtime == "runtime"
        assert KeyType.admin == "admin"

    def test_enum_str(self):
        assert str(KeyType.runtime) == "runtime"
        assert str(KeyType.admin) == "admin"
