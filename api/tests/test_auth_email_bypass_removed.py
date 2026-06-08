"""Regression test for Insight #89 — the legacy X-API-Key=email auth bypass.

The old `get_current_user` matched the `X-API-Key` header directly against
`users.email`. Email is not a secret, so any known/guessed email authenticated
as that user. This was removed 2026-06-08. These tests assert it stays removed
by exercising the REAL auth path (no `get_current_user` override).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from common.models import User, get_db

# Any endpoint guarded by get_current_user works; agents list is simple.
PROTECTED_ENDPOINT = "/api/v1/agents"


@pytest.fixture
def raw_client(db_session):
    """TestClient that overrides ONLY get_db — real get_current_user runs."""
    from api.app.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_email(db_session):
    """A real, registered user's email — the exact value the attack abuses."""
    email = "victim@example.com"
    db_session.add(User(id=uuid.uuid4(), email=email, role="owner", tier="free"))
    db_session.commit()
    return email


def test_registered_email_as_api_key_is_rejected(raw_client, registered_email):
    """The Insight #89 attack: a known registered email used as X-API-Key → 401."""
    resp = raw_client.get(PROTECTED_ENDPOINT, headers={"X-API-Key": registered_email})
    assert resp.status_code == 401
    assert "no longer accepted" in resp.json()["error"]["message"].lower()


def test_arbitrary_api_key_is_rejected(raw_client):
    """Any non-empty X-API-Key fails closed — no email lookup happens."""
    resp = raw_client.get(PROTECTED_ENDPOINT, headers={"X-API-Key": "anything-1234567890"})
    assert resp.status_code == 401
    assert "no longer accepted" in resp.json()["error"]["message"].lower()


def test_no_credentials_is_rejected(raw_client):
    """No auth header at all → 401 Authentication required."""
    resp = raw_client.get(PROTECTED_ENDPOINT)
    assert resp.status_code == 401
