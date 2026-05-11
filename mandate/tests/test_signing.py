"""Crypto round-trip tests for the Mandate Service signer/verifier.

These tests exercise the sign → verify → tamper path end-to-end against
a freshly-generated local PEM key. They deliberately do NOT touch MongoDB —
the goal is to lock down the signature trust model, not the storage layer.

Each test sets ``settings.forensic_signing_key_pem`` to a fresh ECDSA-P256
key so a regression in the verifier's allowlist (``_is_trusted_key_id``) or
in the tristate semantics of ``verify_signature`` will fail the suite.

Tests are written sync + ``asyncio.run`` to avoid pulling pytest-asyncio
into the dev dependency set (see PR #246 for why test-only deps that pin
older pytest are problematic here).
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
    MandateIssuer,
    MandateResponse,
    MandateSignature,
    MandateStatus,
    MandateSubject,
    SignatureAlgorithm,
    VerifyMandateRequest,
)
from mandate.app.signing import sign_mandate, verify_signature


@pytest.fixture
def fresh_local_key(monkeypatch):
    """Configure a fresh ECDSA-P256 PEM key for the duration of the test."""
    priv = ec.generate_private_key(ec.SECP256R1())
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(settings, "forensic_signing_key_pem", pem, raising=False)
    monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
    return pem


def _make_mandate(signatures: list[MandateSignature] | None = None) -> MandateDocument:
    now = datetime.now(UTC)
    return MandateDocument(
        mandate_id="mnd_deadbeef",
        status=MandateStatus.active,
        issuer=MandateIssuer(org_id="org_test", user_id="user_test"),
        subject=MandateSubject(agent_id="agt_test", org_id="org_test"),
        scope=["read:audit"],
        valid_from=now,
        valid_until=now + timedelta(days=1),
        signatures=signatures or [],
        created_at=now,
        updated_at=now,
    )


def _to_response(m: MandateDocument) -> MandateResponse:
    return MandateResponse(**m.model_dump())


def test_sign_then_verify_round_trip(fresh_local_key):
    async def run():
        mandate = _make_mandate()
        sig = await sign_mandate(mandate)
        mandate.signatures = [sig]
        return await verify_signature(mandate, sig)

    assert asyncio.run(run()) is True


def test_tampered_payload_fails_verification(fresh_local_key):
    async def run():
        mandate = _make_mandate()
        sig = await sign_mandate(mandate)
        mandate.signatures = [sig]
        # Mutate the signed scope — signature was over the original payload
        mandate.scope = ["write:everything"]
        return await verify_signature(mandate, sig)

    assert asyncio.run(run()) is False


def test_untrusted_key_id_rejected(fresh_local_key):
    """A signature whose key_id is not in our trust list must not verify,
    even if the bytes were produced by some other valid key. This is the
    spoofing path we explicitly closed: attacker signs with their own key,
    embeds the resource path, hopes the verifier fetches it blindly.
    """

    async def run():
        mandate = _make_mandate()
        sig = await sign_mandate(mandate)
        tampered_sig = MandateSignature(
            algorithm=sig.algorithm,
            key_id="local:0000000000000000",
            signature=sig.signature,
        )
        mandate.signatures = [tampered_sig]
        return await verify_signature(mandate, tampered_sig)

    assert asyncio.run(run()) is False


def test_unknown_algorithm_returns_none(fresh_local_key):
    """ml-dsa-87 has a reserved enum slot but no signer/verifier yet.
    verify_signature must return None (not True) so the route can require
    at least one signature it actually verified.
    """

    async def run():
        mandate = _make_mandate()
        pqc_sig = MandateSignature(
            algorithm=SignatureAlgorithm.ml_dsa_87,
            key_id="kms:pqc-placeholder",
            signature="AAAA",
        )
        mandate.signatures = [pqc_sig]
        return await verify_signature(mandate, pqc_sig)

    assert asyncio.run(run()) is None


def test_verify_route_rejects_ml_dsa_only(fresh_local_key):
    """A mandate carrying ONLY future-algorithm signatures must verify=False.
    Before this fix, ml-dsa-87 returned True optimistically — an attacker
    could submit a forged mandate with a single bogus PQC signature and the
    verifier would pass it.
    """

    async def run():
        mandate = _make_mandate(
            signatures=[
                MandateSignature(
                    algorithm=SignatureAlgorithm.ml_dsa_87,
                    key_id="kms:pqc-placeholder",
                    signature="AAAA",
                )
            ]
        )
        return await verify_mandate(
            VerifyMandateRequest(mandate=_to_response(mandate)), required_scope=None
        )

    result = asyncio.run(run())
    assert result.valid is False
    assert result.checks["signatures_valid"] is False


def test_verify_route_accepts_hybrid(fresh_local_key):
    """Hybrid mandate (classical + future-algo slot) must verify=True
    when the classical signature is valid. The unverifiable PQC slot is
    tolerated; it does NOT count as a passing signature on its own.
    """

    async def run():
        mandate = _make_mandate()
        classical = await sign_mandate(mandate)
        pqc_slot = MandateSignature(
            algorithm=SignatureAlgorithm.ml_dsa_87,
            key_id="kms:pqc-placeholder",
            signature="AAAA",
        )
        mandate.signatures = [classical, pqc_slot]
        return await verify_mandate(
            VerifyMandateRequest(mandate=_to_response(mandate)), required_scope=None
        )

    result = asyncio.run(run())
    assert result.valid is True
    assert result.checks["signatures_valid"] is True
