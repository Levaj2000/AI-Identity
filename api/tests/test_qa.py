"""Tests for the QA checklist endpoints — Clerk-token pass-through.

The QA runner authenticates its outbound self-calls by replaying the caller's
Clerk session JWT (the legacy ``X-API-Key=email`` credential was removed in
prod, security Insight #89). These tests verify both the admin and onboarding
endpoints forward that token to the runner, and that a caller arriving without
a Bearer token is rejected before the runner ever runs.
"""

import pytest

from api.app.auth import get_current_user
from api.app.qa_runner import QARunResult


@pytest.fixture
def auth_override(test_user):
    """Force auth to resolve to the test user, bypassing Clerk JWKS verification.

    The QA endpoints read the raw Authorization header themselves (to replay it),
    so tests still send a real Bearer header — this override only stands in for
    the network-bound Clerk signature check.
    """
    from api.app.main import app

    app.dependency_overrides[get_current_user] = lambda: test_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _fake_result() -> QARunResult:
    return QARunResult(checks=[], passed=15, failed=0, total=15, duration_ms=300)


class TestQATokenPassthrough:
    def test_admin_run_forwards_caller_bearer_token(self, client, auth_override, monkeypatch):
        captured: dict = {}

        async def _fake_run(api_url, gateway_url, auth_token):
            captured["auth_token"] = auth_token
            return _fake_result()

        monkeypatch.setattr("api.app.routers.qa.run_qa_checks", _fake_run)

        resp = client.post(
            "/api/v1/qa/run",
            headers={"Authorization": "Bearer clerk-session-jwt-abc"},
        )

        assert resp.status_code == 201
        assert captured["auth_token"] == "clerk-session-jwt-abc"
        body = resp.json()
        assert body["passed_count"] == 15
        assert body["total_count"] == 15
        assert body["mode"] == "admin"

    def test_onboarding_run_forwards_caller_bearer_token(self, client, auth_override, monkeypatch):
        captured: dict = {}

        async def _fake_run(api_url, gateway_url, auth_token):
            captured["auth_token"] = auth_token
            return _fake_result()

        monkeypatch.setattr("api.app.routers.qa.run_qa_checks", _fake_run)

        resp = client.post(
            "/api/v1/qa/run/onboarding",
            headers={"Authorization": "Bearer clerk-session-jwt-xyz"},
        )

        assert resp.status_code == 201
        assert captured["auth_token"] == "clerk-session-jwt-xyz"
        assert resp.json()["mode"] == "onboarding"

    def test_run_without_bearer_token_is_rejected(self, client, auth_override, monkeypatch):
        calls = {"n": 0}

        async def _fake_run(*args, **kwargs):
            calls["n"] += 1
            return _fake_result()

        monkeypatch.setattr("api.app.routers.qa.run_qa_checks", _fake_run)

        # No Authorization header — auth is overridden, but the endpoint still
        # requires a Bearer token to replay, so it must 400 before running.
        resp = client.post("/api/v1/qa/run")

        assert resp.status_code == 400
        assert "Bearer" in resp.json()["error"]["message"]
        assert calls["n"] == 0  # runner never invoked without a token to forward
