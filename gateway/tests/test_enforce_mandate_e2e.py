"""Endpoint-level tests for /gateway/enforce with X-Agent-Mandate.

Real minted Biscuits drive the offline layer; the settlement layer is
stubbed at gateway.app.mandate_check.settle_draw (its own unit tests cover
the httpx seam). Covers the wiring the demo script exercises live.
"""

import datetime as dt

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from common.biscuit import attenuate_spend_ceiling, mint_mandate_biscuit
from common.config.settings import settings
from gateway.app import mandate_check
from gateway.app.mandate_check import MandateCheckOutcome
from gateway.tests.conftest import TEST_AGENT_ID

MANDATE_ID = "mnd_e2e00001"


@pytest.fixture(scope="module")
def root_pem() -> str:
    key = Ed25519PrivateKey.generate()
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


@pytest.fixture(scope="module")
def minted(root_pem):
    return mint_mandate_biscuit(
        private_key_pem=root_pem,
        mandate_id=MANDATE_ID,
        subject_agent_id=str(TEST_AGENT_ID),
        subject_org_id="org_demo",
        scope=["spend:commerce"],
        valid_from=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        limit_cents=10_000,
    )


@pytest.fixture(autouse=True)
def _configured(monkeypatch, root_pem):
    monkeypatch.setattr(settings, "biscuit_root_key_pem", root_pem)
    monkeypatch.setattr(settings, "mandate_draw_token", "test-token")


@pytest.fixture
def settle_calls(monkeypatch):
    """Stub settle_draw; returns the recorded call list."""
    calls: list[dict] = []

    def fake_settle(mandate_id, *, amount_cents, currency, settlement, reference=None):
        calls.append(
            {
                "mandate_id": mandate_id,
                "amount_cents": amount_cents,
                "settlement": settlement,
            }
        )
        return MandateCheckOutcome(
            allowed=True,
            audit_metadata={"mandate_id": mandate_id},
            draw={
                "mandate_id": mandate_id,
                "accepted": True,
                "exceeded": False,
                "status": "active",
                "spent_cents": amount_cents,
                "limit_cents": 10_000,
                "remaining_cents": 10_000 - amount_cents,
                "deny_reason": None,
            },
        )

    monkeypatch.setattr(mandate_check, "settle_draw", fake_settle)
    return calls


def _enforce(client, token: str | None, amount: int | None = 3_000, **extra):
    params = {
        "agent_id": str(TEST_AGENT_ID),
        "endpoint": "/v1/commerce/checkout",
        "method": "POST",
    }
    if amount is not None:
        params["spend_amount_cents"] = amount
    params.update(extra)
    headers = {"X-Agent-Mandate": token} if token is not None else {}
    return client.post("/gateway/enforce", params=params, headers=headers)


def test_allow_flow_settles_and_returns_mandate(
    client, test_agent, test_policy, minted, settle_calls
):
    resp = _enforce(client, minted.token)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "allow"
    assert body["mandate"]["remaining_cents"] == 7_000
    assert settle_calls == [{"mandate_id": MANDATE_ID, "amount_cents": 3_000, "settlement": False}]


def test_attenuated_over_ceiling_denied_without_settlement(
    client, test_agent, test_policy, minted, settle_calls
):
    narrowed = attenuate_spend_ceiling(minted.token, minted.root_public_key, ceiling_cents=2_000)
    resp = _enforce(client, narrowed, amount=4_000)
    assert resp.status_code == 403
    assert resp.json()["deny_reason"] == "biscuit_denied"
    assert settle_calls == []  # denied offline — mandate service never consulted


def test_wrong_subject_denied(client, test_agent, test_policy, root_pem, settle_calls):
    other = mint_mandate_biscuit(
        private_key_pem=root_pem,
        mandate_id="mnd_other001",
        subject_agent_id="99999999-9999-9999-9999-999999999999",
        subject_org_id="org_demo",
        scope=["spend:commerce"],
        valid_from=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        limit_cents=10_000,
    )
    resp = _enforce(client, other.token)
    assert resp.status_code == 403
    assert resp.json()["deny_reason"] == "biscuit_denied"
    assert settle_calls == []


def test_token_without_amount_is_400(client, test_agent, test_policy, minted, settle_calls):
    resp = _enforce(client, minted.token, amount=None)
    assert resp.status_code == 400
    assert settle_calls == []


def test_mandate_service_down_fails_closed(client, test_agent, test_policy, minted, monkeypatch):
    def unavailable(mandate_id, **kwargs):
        return MandateCheckOutcome(
            allowed=False,
            status_code=503,
            deny_reason="mandate_unavailable",
            message="Mandate service unreachable — request denied (fail-closed)",
        )

    monkeypatch.setattr(mandate_check, "settle_draw", unavailable)
    resp = _enforce(client, minted.token)
    assert resp.status_code == 503
    assert resp.json()["deny_reason"] == "mandate_unavailable"


def test_policy_deny_never_reaches_settlement(
    client, test_agent, test_policy, minted, settle_calls
):
    # /admin/* is outside the policy's allowed /v1/* endpoints
    resp = _enforce(client, minted.token, endpoint="/admin/keys")
    assert resp.status_code == 403
    assert resp.json()["deny_reason"] == "policy_denied"
    assert settle_calls == []


def test_no_token_no_mandate_semantics(client, test_agent, test_policy, settle_calls):
    resp = _enforce(client, None, amount=None)
    assert resp.status_code == 200
    assert "mandate" not in resp.json()
    assert settle_calls == []
