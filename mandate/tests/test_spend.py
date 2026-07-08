"""Spend-limit tests: pure evaluation matrix, signature stability across
runtime-state mutation (the schema-1.1 fix), and the verify endpoint's
within_spend_limit check.

Like test_signing.py, these deliberately do NOT touch MongoDB — the route's
persistence is thin I/O over evaluate_spend, which is what's locked down
here. Sync + ``asyncio.run`` per the house test style (no pytest-asyncio).
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.config.settings import settings
from mandate.app.routers.verify import verify_mandate
from mandate.app.schemas import (
    MandateDocument,
    MandateExceedance,
    MandateIssuer,
    MandateResponse,
    MandateStatus,
    MandateSubject,
    SpendLimit,
    VerifyMandateRequest,
)
from mandate.app.signing import _build_signable_payload, sign_mandate, verify_signature
from mandate.app.spend import (
    DENY_CURRENCY_MISMATCH,
    DENY_LIMIT_EXCEEDED,
    DENY_MANDATE_INACTIVE,
    evaluate_spend,
)

LIMIT = SpendLimit(limit_cents=10_000)  # $100.00


def _make_mandate(
    *,
    schema_version: str = "1.1",
    spend_limit: SpendLimit | None = LIMIT,
    spent_cents: int = 0,
    status: MandateStatus = MandateStatus.active,
) -> MandateDocument:
    now = datetime.now(UTC)
    return MandateDocument(
        mandate_id="mnd_cafef00d",
        schema_version=schema_version,
        status=status,
        issuer=MandateIssuer(org_id="org_test", user_id="user_test"),
        subject=MandateSubject(agent_id="agt_test", org_id="org_test"),
        scope=["spend:commerce"],
        spend_limit=spend_limit,
        spent_cents=spent_cents,
        valid_from=now,
        valid_until=now + timedelta(days=1),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def fresh_local_key(monkeypatch):
    priv = ec.generate_private_key(ec.SECP256R1())
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(settings, "forensic_signing_key_pem", pem, raising=False)
    monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
    return pem


# ── evaluate_spend matrix ──────────────────────────────────────────────────


class TestEvaluateSpend:
    def _eval(
        self,
        amount,
        *,
        spent=0,
        settlement=False,
        status=MandateStatus.active,
        limit=LIMIT,
        currency="USD",
    ):
        return evaluate_spend(
            status=status,
            spend_limit=limit,
            spent_cents=spent,
            amount_cents=amount,
            currency=currency,
            settlement=settlement,
        )

    def test_within_limit_accepted(self):
        out = self._eval(2_500, spent=4_000)
        assert out.accepted and not out.exceeded
        assert out.audit_decision == "allow"
        assert out.new_spent_cents == 6_500
        assert out.new_status == MandateStatus.active

    def test_exactly_at_limit_accepted(self):
        out = self._eval(6_000, spent=4_000)  # lands exactly on 10_000
        assert out.accepted and not out.exceeded
        assert out.new_spent_cents == 10_000

    def test_crossing_enforced_denied_budget_intact(self):
        out = self._eval(40_500, spent=9_500)
        assert not out.accepted and not out.exceeded
        assert out.audit_decision == "deny"
        assert out.deny_reason == DENY_LIMIT_EXCEEDED
        assert out.new_spent_cents == 9_500  # nothing recorded
        assert out.new_status == MandateStatus.active  # remaining budget usable

    def test_crossing_settlement_recorded_and_exceeded(self):
        out = self._eval(40_500, spent=9_500, settlement=True)
        assert out.accepted and out.exceeded
        assert out.audit_decision == "deny"  # the breach IS the deny record
        assert out.deny_reason == DENY_LIMIT_EXCEEDED
        assert out.new_spent_cents == 50_000  # $500 recorded against $100 limit
        assert out.new_status == MandateStatus.exceeded

    def test_exceeded_mandate_rejects_further_spend(self):
        out = self._eval(100, spent=50_000, status=MandateStatus.exceeded)
        assert not out.accepted
        assert out.deny_reason == DENY_MANDATE_INACTIVE
        assert out.new_status == MandateStatus.exceeded

    def test_revoked_mandate_rejects_spend(self):
        out = self._eval(100, status=MandateStatus.revoked)
        assert not out.accepted
        assert out.deny_reason == DENY_MANDATE_INACTIVE

    def test_currency_mismatch_denied(self):
        out = self._eval(100, currency="EUR")
        assert not out.accepted
        assert out.deny_reason == DENY_CURRENCY_MISMATCH
        assert out.new_spent_cents == 0

    def test_no_limit_tracks_without_limiting(self):
        out = self._eval(1_000_000, limit=None)
        assert out.accepted and not out.exceeded
        assert out.new_spent_cents == 1_000_000


# ── signature stability across runtime-state mutation (schema 1.1) ────────


class TestSignablepayloadVersioning:
    def test_v11_signature_survives_spend_and_status_mutation(self, fresh_local_key):
        mandate = _make_mandate()
        sig = asyncio.run(sign_mandate(mandate))
        mandate.signatures = [sig]

        # Simulate the settlement path mutating runtime state after issuance
        mandate.spent_cents = 50_000
        mandate.status = MandateStatus.exceeded
        mandate.exceedance = MandateExceedance(
            exceeded_at=datetime.now(UTC),
            attempted_cents=40_500,
            spent_cents=50_000,
            limit_cents=10_000,
            reference="ord_1042",
        )

        assert asyncio.run(verify_signature(mandate, sig)) is True

    def test_v11_signature_fails_on_grant_tamper(self, fresh_local_key):
        mandate = _make_mandate()
        sig = asyncio.run(sign_mandate(mandate))
        mandate.signatures = [sig]

        # Tampering with the GRANT (the limit) must still break the signature
        mandate.spend_limit = SpendLimit(limit_cents=100_000_000)
        assert asyncio.run(verify_signature(mandate, sig)) is False

    def test_v10_payload_excludes_post_1_0_fields(self):
        legacy = _make_mandate(schema_version="1.0", spend_limit=None)
        payload = _build_signable_payload(legacy).decode()
        # Fields that postdate 1.0 must not appear (their defaults would
        # break byte-for-byte verification of old signatures) …
        assert "spend_limit" not in payload
        assert "spent_cents" not in payload
        assert "exceedance" not in payload
        # … while 1.0 keeps its original (flawed) rule of signing status.
        assert '"status"' in payload

    def test_v11_payload_excludes_runtime_state_keeps_grant(self):
        mandate = _make_mandate()
        payload = _build_signable_payload(mandate).decode()
        assert '"status"' not in payload
        assert '"revocation"' not in payload
        assert '"spent_cents"' not in payload
        assert '"exceedance"' not in payload
        assert '"spend_limit"' in payload  # monetary authority IS the grant
        assert '"limit_cents":10000' in payload


# ── verify endpoint: within_spend_limit ────────────────────────────────────


class TestVerifyWithinSpendLimit:
    def _verify(self, mandate: MandateDocument):
        req = VerifyMandateRequest(mandate=MandateResponse(**mandate.model_dump()))
        return asyncio.run(verify_mandate(req, required_scope=None))

    def test_overspent_mandate_fails_even_if_status_tampered_active(self, fresh_local_key):
        mandate = _make_mandate()
        sig = asyncio.run(sign_mandate(mandate))
        mandate.signatures = [sig]

        # Breach happened; attacker flips status back to active to hide it.
        # spent/limit comparison catches it independently of status —
        # and the 1.1 signature still verifies (status is unsigned state),
        # so the failure is attributed to the right check.
        mandate.spent_cents = 50_000
        mandate.status = MandateStatus.active

        result = self._verify(mandate)
        assert result.checks["signatures_valid"] is True
        assert result.checks["within_spend_limit"] is False
        assert result.valid is False
        assert "Spend limit exceeded" in (result.error or "")

    def test_within_limit_passes(self, fresh_local_key):
        mandate = _make_mandate()
        sig = asyncio.run(sign_mandate(mandate))
        mandate.signatures = [sig]
        mandate.spent_cents = 9_999

        result = self._verify(mandate)
        assert result.checks["within_spend_limit"] is True
        assert result.valid is True

    def test_no_limit_check_vacuously_true(self, fresh_local_key):
        mandate = _make_mandate(spend_limit=None)
        sig = asyncio.run(sign_mandate(mandate))
        mandate.signatures = [sig]

        result = self._verify(mandate)
        assert result.checks["within_spend_limit"] is True
