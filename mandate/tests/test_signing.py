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
import base64
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
from mandate.app.signing import (
    _b64url,
    _build_signable_payload,
    _mldsa_key_id,
    sign_mandate,
    verify_signature,
)


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


@pytest.fixture
def fresh_mldsa_key(monkeypatch):
    """Configure a fresh trusted ML-DSA-87 public key; yield the live signer.

    Skips if liboqs isn't available in the environment (e.g. the native lib
    wasn't built) so the rest of the suite still runs.
    """
    oqs = pytest.importorskip("oqs")

    signer = oqs.Signature("ML-DSA-87")
    pub = signer.generate_keypair()
    monkeypatch.setattr(
        settings, "forensic_mldsa_public_key", base64.b64encode(pub).decode(), raising=False
    )
    try:
        yield signer, pub
    finally:
        signer.free()


def _mldsa_sign(mandate: MandateDocument, signer, pub: bytes) -> MandateSignature:
    """Produce a valid ml-dsa-87 MandateSignature over the canonical payload."""
    raw = signer.sign(_build_signable_payload(mandate))
    return MandateSignature(
        algorithm=SignatureAlgorithm.ml_dsa_87,
        key_id=_mldsa_key_id(pub),
        signature=_b64url(raw),
    )


def test_mldsa_sign_then_verify_round_trip(fresh_mldsa_key):
    signer, pub = fresh_mldsa_key

    async def run():
        mandate = _make_mandate()
        sig = _mldsa_sign(mandate, signer, pub)
        mandate.signatures = [sig]
        return await verify_signature(mandate, sig)

    assert asyncio.run(run()) is True


def test_mldsa_tampered_signature_fails(fresh_mldsa_key):
    signer, pub = fresh_mldsa_key

    async def run():
        mandate = _make_mandate()
        sig = _mldsa_sign(mandate, signer, pub)
        raw = bytearray(base64.urlsafe_b64decode(sig.signature + "=="))
        raw[100] ^= 0x01  # flip a bit in the middle of the signature
        sig.signature = _b64url(bytes(raw))
        mandate.signatures = [sig]
        return await verify_signature(mandate, sig)

    assert asyncio.run(run()) is False


def test_mldsa_tampered_payload_fails(fresh_mldsa_key):
    signer, pub = fresh_mldsa_key

    async def run():
        mandate = _make_mandate()
        sig = _mldsa_sign(mandate, signer, pub)
        mandate.signatures = [sig]
        mandate.scope = ["write:everything"]  # mutate after signing
        return await verify_signature(mandate, sig)

    assert asyncio.run(run()) is False


def test_mldsa_untrusted_key_rejected(fresh_mldsa_key):
    """A valid ml-dsa signature from a key this deployment doesn't trust
    (its fingerprint isn't the configured one) must verify=False, not None."""
    signer, pub = fresh_mldsa_key
    oqs = pytest.importorskip("oqs")

    async def run():
        mandate = _make_mandate()
        # Sign with a DIFFERENT keypair; key_id derives from the foreign pubkey.
        with oqs.Signature("ML-DSA-87") as attacker:
            foreign_pub = attacker.generate_keypair()
            raw = attacker.sign(_build_signable_payload(mandate))
        sig = MandateSignature(
            algorithm=SignatureAlgorithm.ml_dsa_87,
            key_id=_mldsa_key_id(foreign_pub),
            signature=_b64url(raw),
        )
        mandate.signatures = [sig]
        return await verify_signature(mandate, sig)

    assert asyncio.run(run()) is False


def test_verify_route_accepts_mldsa_only(fresh_mldsa_key):
    """With a trusted PQC key configured, a mandate carrying ONLY a valid
    ml-dsa-87 signature must verify=True (the slot is now real)."""
    signer, pub = fresh_mldsa_key

    async def run():
        mandate = _make_mandate()
        sig = _mldsa_sign(mandate, signer, pub)
        mandate.signatures = [sig]
        return await verify_mandate(
            VerifyMandateRequest(mandate=_to_response(mandate)), required_scope=None
        )

    result = asyncio.run(run())
    assert result.valid is True
    assert result.checks["signatures_valid"] is True


def test_verify_route_accepts_hybrid_ecdsa_plus_mldsa(fresh_local_key, fresh_mldsa_key):
    """Hybrid mandate with BOTH a valid classical and a valid PQC signature
    verifies, and each signature verifies on its own."""
    signer, pub = fresh_mldsa_key

    async def run():
        mandate = _make_mandate()
        classical = await sign_mandate(mandate)
        pqc = _mldsa_sign(mandate, signer, pub)
        mandate.signatures = [classical, pqc]
        assert await verify_signature(mandate, classical) is True
        assert await verify_signature(mandate, pqc) is True
        return await verify_mandate(
            VerifyMandateRequest(mandate=_to_response(mandate)), required_scope=None
        )

    result = asyncio.run(run())
    assert result.valid is True
    assert result.checks["signatures_valid"] is True


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
