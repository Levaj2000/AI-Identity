"""Tests for gateway/app/mandate_check.py — presentation + settlement layers.

No DB, no live Mandate Service: presentation runs on real tokens minted
in-test; settlement uses httpx.MockTransport as the network seam.
"""

import datetime as dt
import json

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from common.biscuit import attenuate_spend_ceiling, mint_mandate_biscuit
from common.config.settings import settings
from gateway.app import mandate_check
from gateway.app.circuit_breaker import CircuitBreaker
from gateway.app.mandate_check import check_presentation, settle_draw

AGENT_ID = "0b6ef1a2-9f14-4c1e-8f7a-2d5c3e9b1a70"
MANDATE_ID = "mnd_ab12cd34"


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
        subject_agent_id=AGENT_ID,
        subject_org_id="org_demo",
        scope=["spend:commerce"],
        valid_from=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        limit_cents=10_000,
    )


@pytest.fixture(autouse=True)
def _configured(monkeypatch, root_pem):
    monkeypatch.setattr(settings, "biscuit_root_key_pem", root_pem)
    monkeypatch.setattr(settings, "mandate_draw_token", "test-token")
    # Fresh breaker per test so failure-recording tests can't leak state.
    monkeypatch.setattr(
        mandate_check, "mandate_circuit_breaker", CircuitBreaker(name="mandate-service-test")
    )


class TestCheckPresentation:
    def test_valid_presentation_allowed(self, minted):
        outcome = check_presentation(
            minted.token,
            agent_id=AGENT_ID,
            amount_cents=3_000,
            scope="spend:commerce",
            currency="USD",
        )
        assert outcome.allowed
        assert outcome.audit_metadata["credential_format"] == "biscuit"
        assert outcome.audit_metadata["mandate_id"] == MANDATE_ID

    def test_attenuated_over_ceiling_denied_offline(self, minted):
        narrowed = attenuate_spend_ceiling(
            minted.token, minted.root_public_key, ceiling_cents=2_000
        )
        outcome = check_presentation(
            narrowed,
            agent_id=AGENT_ID,
            amount_cents=4_000,
            scope="spend:commerce",
            currency="USD",
        )
        assert not outcome.allowed
        assert outcome.status_code == 403
        assert outcome.deny_reason == "biscuit_denied"
        assert outcome.audit_metadata["biscuit_block_count"] == 2

    def test_no_trust_anchor_fails_closed(self, minted, monkeypatch):
        monkeypatch.setattr(settings, "biscuit_root_key_pem", "")
        outcome = check_presentation(
            minted.token,
            agent_id=AGENT_ID,
            amount_cents=100,
            scope="spend:commerce",
            currency="USD",
        )
        assert not outcome.allowed
        assert outcome.status_code == 503
        assert outcome.deny_reason == "mandate_unavailable"


def _transport(status_code: int, body: dict | None = None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert json.loads(request.content)["amount_cents"] > 0
        return httpx.Response(status_code, json=body or {})

    return httpx.MockTransport(handler)


class TestSettleDraw:
    def test_accepted_draw(self):
        draw = {
            "mandate_id": MANDATE_ID,
            "accepted": True,
            "exceeded": False,
            "status": "active",
            "spent_cents": 3_000,
            "limit_cents": 10_000,
            "remaining_cents": 7_000,
            "deny_reason": None,
        }
        outcome = settle_draw(
            MANDATE_ID,
            amount_cents=3_000,
            currency="USD",
            settlement=False,
            transport=_transport(200, draw),
        )
        assert outcome.allowed
        assert outcome.draw["remaining_cents"] == 7_000
        assert outcome.audit_metadata["mandate_spent_cents"] == 3_000

    def test_denied_draw_relayed(self):
        draw = {
            "mandate_id": MANDATE_ID,
            "accepted": False,
            "exceeded": False,
            "status": "active",
            "spent_cents": 9_500,
            "limit_cents": 10_000,
            "remaining_cents": 500,
            "deny_reason": "spend_limit_exceeded",
        }
        outcome = settle_draw(
            MANDATE_ID,
            amount_cents=4_050,
            currency="USD",
            settlement=False,
            transport=_transport(200, draw),
        )
        assert not outcome.allowed
        assert outcome.status_code == 403
        assert outcome.deny_reason == "mandate_denied"
        assert outcome.audit_metadata["deny_reason"] == "spend_limit_exceeded"

    def test_server_error_fails_closed_and_records_failure(self):
        outcome = settle_draw(
            MANDATE_ID,
            amount_cents=100,
            currency="USD",
            settlement=False,
            transport=_transport(500),
        )
        assert not outcome.allowed
        assert outcome.status_code == 503
        assert outcome.deny_reason == "mandate_unavailable"
        assert mandate_check.mandate_circuit_breaker.status.failure_count == 1

    def test_unreachable_fails_closed(self):
        def boom(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        outcome = settle_draw(
            MANDATE_ID,
            amount_cents=100,
            currency="USD",
            settlement=False,
            transport=httpx.MockTransport(boom),
        )
        assert not outcome.allowed
        assert outcome.status_code == 503
        assert outcome.deny_reason == "mandate_unavailable"

    def test_no_draw_token_fails_closed(self, monkeypatch):
        monkeypatch.setattr(settings, "mandate_draw_token", "")
        outcome = settle_draw(
            MANDATE_ID,
            amount_cents=100,
            currency="USD",
            settlement=False,
            transport=_transport(200, {}),
        )
        assert not outcome.allowed
        assert outcome.status_code == 503
