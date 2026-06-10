"""Tests for POST /api/v1/keys/verify — runtime key resolution endpoint.

Covers the happy path (valid active runtime key resolves to its agent +
metadata) and every documented failure mode in the ``reason`` enum:
malformed_key, key_not_found, key_revoked, key_rotated, key_expired,
agent_suspended, agent_revoked.
"""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient

from common.auth.keys import generate_api_key, get_key_prefix, hash_key
from common.config.settings import settings
from common.models import Agent, AgentKey, KeyStatus, KeyType, get_db


def _make_agent_with_key(
    db,
    user,
    *,
    role="cto",
    agent_status="active",
    key_status="active",
    expires_at=None,
):
    agent = Agent(
        id=uuid.uuid4(),
        user_id=user.id,
        name=f"{role}-agent",
        status=agent_status,
        capabilities=[],
        metadata_={"role": role, "sprint": "11"},
    )
    db.add(agent)

    plaintext = generate_api_key(key_type="runtime")
    key = AgentKey(
        agent_id=agent.id,
        key_hash=hash_key(plaintext),
        key_prefix=get_key_prefix(plaintext),
        key_type=KeyType.runtime.value,
        status=key_status,
        expires_at=expires_at,
    )
    db.add(key)
    db.commit()
    db.refresh(agent)
    return agent, plaintext


class TestVerifyKeyHappyPath:
    def test_valid_runtime_key_returns_agent_metadata(
        self, client, db_session, test_user, auth_headers
    ):
        agent, plaintext = _make_agent_with_key(db_session, test_user, role="cto")

        resp = client.post(
            "/api/v1/keys/verify",
            json={"key": plaintext},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["agent_id"] == str(agent.id)
        assert body["agent_name"] == "cto-agent"
        assert body["metadata"]["role"] == "cto"
        assert body["metadata"]["sprint"] == "11"
        assert body["agent_status"] == "active"
        assert body["key_type"] == "runtime"
        assert body["key_prefix"].startswith("aid_sk_")
        assert body["reason"] is None


class TestVerifyKeyFailureModes:
    def test_malformed_key_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/v1/keys/verify",
            json={"key": "not-an-aid-key-at-all"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["reason"] == "malformed_key"
        assert body["agent_id"] is None

    def test_unknown_key_returns_key_not_found(self, client, auth_headers):
        # Well-formed prefix but no matching key in DB
        resp = client.post(
            "/api/v1/keys/verify",
            json={"key": "aid_sk_" + "x" * 32},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["reason"] == "key_not_found"

    def test_revoked_key_returns_key_revoked(self, client, db_session, test_user, auth_headers):
        _, plaintext = _make_agent_with_key(
            db_session, test_user, key_status=KeyStatus.revoked.value
        )
        resp = client.post(
            "/api/v1/keys/verify",
            json={"key": plaintext},
            headers=auth_headers,
        )
        assert resp.json()["valid"] is False
        assert resp.json()["reason"] == "key_revoked"

    def test_rotated_key_returns_key_rotated(self, client, db_session, test_user, auth_headers):
        _, plaintext = _make_agent_with_key(
            db_session, test_user, key_status=KeyStatus.rotated.value
        )
        assert (
            client.post(
                "/api/v1/keys/verify",
                json={"key": plaintext},
                headers=auth_headers,
            ).json()["reason"]
            == "key_rotated"
        )

    def test_expired_key_returns_key_expired(self, client, db_session, test_user, auth_headers):
        past = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
        _, plaintext = _make_agent_with_key(db_session, test_user, expires_at=past)
        assert (
            client.post(
                "/api/v1/keys/verify",
                json={"key": plaintext},
                headers=auth_headers,
            ).json()["reason"]
            == "key_expired"
        )

    def test_revoked_agent_returns_agent_revoked(self, client, db_session, test_user, auth_headers):
        _, plaintext = _make_agent_with_key(db_session, test_user, agent_status="revoked")
        assert (
            client.post(
                "/api/v1/keys/verify",
                json={"key": plaintext},
                headers=auth_headers,
            ).json()["reason"]
            == "agent_revoked"
        )


_SERVICE_TOKEN = "svc_tok_verify_0123456789abcdef0123456789ab"


@pytest.fixture
def raw_verify_client(db_session):
    """TestClient overriding ONLY get_db — the real require_verify_service runs.

    The shared `client` fixture shims the service-token dependency; these tests
    exercise the actual X-Service-Token auth.
    """
    from api.app.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestVerifyServiceTokenAuth:
    """Real-auth tests (no harness override) for the dedicated X-Service-Token."""

    def test_valid_service_token_authorizes(
        self, raw_verify_client, db_session, test_user, monkeypatch
    ):
        monkeypatch.setattr(settings, "verify_service_token", _SERVICE_TOKEN)
        agent, plaintext = _make_agent_with_key(db_session, test_user, role="cto")
        resp = raw_verify_client.post(
            "/api/v1/keys/verify",
            json={"key": plaintext},
            headers={"X-Service-Token": _SERVICE_TOKEN},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is True
        assert resp.json()["agent_id"] == str(agent.id)

    def test_missing_service_token_rejected(
        self, raw_verify_client, db_session, test_user, monkeypatch
    ):
        monkeypatch.setattr(settings, "verify_service_token", _SERVICE_TOKEN)
        _, plaintext = _make_agent_with_key(db_session, test_user)
        resp = raw_verify_client.post("/api/v1/keys/verify", json={"key": plaintext})
        assert resp.status_code == 401

    def test_wrong_service_token_rejected(
        self, raw_verify_client, db_session, test_user, monkeypatch
    ):
        monkeypatch.setattr(settings, "verify_service_token", _SERVICE_TOKEN)
        _, plaintext = _make_agent_with_key(db_session, test_user)
        resp = raw_verify_client.post(
            "/api/v1/keys/verify",
            json={"key": plaintext},
            headers={"X-Service-Token": "wrong-token-value"},
        )
        assert resp.status_code == 401

    def test_email_as_x_api_key_does_not_authorize(
        self, raw_verify_client, db_session, test_user, monkeypatch
    ):
        # Regression: the removed email-as-key path (Insight #89) must not sneak
        # back via the verify endpoint. X-API-Key is irrelevant here; only the
        # dedicated service token authorizes.
        monkeypatch.setattr(settings, "verify_service_token", _SERVICE_TOKEN)
        _, plaintext = _make_agent_with_key(db_session, test_user)
        resp = raw_verify_client.post(
            "/api/v1/keys/verify",
            json={"key": plaintext},
            headers={"X-API-Key": test_user.email},
        )
        assert resp.status_code == 401


class TestVerifyKeyAuth:
    def test_plaintext_key_never_in_response_when_invalid(self, client, auth_headers):
        # Defense-in-depth: confirm the response body never echoes the key
        # back, even on failure paths.
        evil_key = "aid_sk_" + "deadbeef" * 4
        resp = client.post(
            "/api/v1/keys/verify",
            json={"key": evil_key},
            headers=auth_headers,
        )
        assert evil_key not in resp.text


class TestVerifyKeyValidation:
    def test_short_key_rejected_by_pydantic(self, client, auth_headers):
        resp = client.post("/api/v1/keys/verify", json={"key": "x"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_missing_key_field_rejected(self, client, auth_headers):
        resp = client.post("/api/v1/keys/verify", json={}, headers=auth_headers)
        assert resp.status_code == 422
