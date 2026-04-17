"""Unit tests for common/schemas/forensic_attestation.py.

These tests exercise the signing layer in isolation using a local
ECDSA-P256 key — no KMS, no DB, no network. The production signing
pipeline (#263) uses a KMS-backed signer that satisfies the same
``_Signer`` protocol; swapping the backing key is the only difference.

Coverage goals:

* Round-trip: sign a payload, verify the envelope, get back an equal
  payload. The fundamental correctness test.
* Canonical bytes are stable across:
  - different insertion orders of the payload fields
  - UUID object vs. string input
  - multiple calls (determinism)
* Verification fails *loudly* on:
  - tampered payload
  - tampered signature
  - wrong public key
  - wrong payload_type
  - multi-signature envelopes (v1 expects exactly 1)
  - naive (tz-unaware) datetimes
* PAE produces the exact bytes required by the DSSE spec — this is
  the interop surface.
"""

from __future__ import annotations

import base64
import copy
import datetime
import json
import uuid

import pytest
import rfc8785
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.schemas.forensic_attestation import (
    PAYLOAD_TYPE,
    AttestationPayloadV1,
    AttestationVerificationError,
    DSSEEnvelope,
    DSSESignature,
    canonical_bytes,
    local_ecdsa_signer,
    pae,
    sign_payload,
    verify_envelope,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ec_keypair() -> tuple[ec.EllipticCurvePrivateKey, bytes]:
    """Generate a fresh P-256 keypair; return (private_key, public_pem)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, public_pem


@pytest.fixture
def sample_payload() -> AttestationPayloadV1:
    """A realistic attestation payload for round-trip tests."""
    return AttestationPayloadV1(
        schema_version=1,
        session_id=uuid.UUID("b8f2c1a0-4e6d-4e2a-9f1a-3c2b0d4e8f7a"),
        org_id=uuid.UUID("f1e2d3c4-b5a6-4798-8877-66554433abcd"),
        evidence_chain_hash=("3b7e0a6f4a9d8c2e5b1f0d3c6a8b9e2d1f4c7a0b3d6e9f2a5c8b1d4e7a0b3c6d"),
        first_audit_id=104821,
        last_audit_id=104827,
        event_count=7,
        session_start=datetime.datetime(2026, 4, 17, 13, 42, 0, tzinfo=datetime.UTC),
        session_end=datetime.datetime(2026, 4, 17, 13, 47, 30, tzinfo=datetime.UTC),
        signed_at=datetime.datetime(2026, 4, 17, 13, 47, 30, tzinfo=datetime.UTC),
        signer_key_id=(
            "projects/test-project/locations/us-east1/keyRings/ai-identity-forensic/"
            "cryptoKeys/session-attestation/cryptoKeyVersions/1"
        ),
    )


# ---------------------------------------------------------------------------
# Canonical serialization (JCS)
# ---------------------------------------------------------------------------


class TestCanonicalBytes:
    def test_deterministic(self, sample_payload: AttestationPayloadV1) -> None:
        """Two calls on the same payload produce the same bytes."""
        assert canonical_bytes(sample_payload) == canonical_bytes(sample_payload)

    def test_sorted_keys(self, sample_payload: AttestationPayloadV1) -> None:
        """JCS sorts object keys. Verify the bytes start with the
        alphabetically-first field."""
        raw = canonical_bytes(sample_payload)
        # "event_count" comes before "evidence_chain_hash" alphabetically
        # because 'n' < 'v' at position 5 (event_co*n*t vs evide*n*ce ...).
        # Actually lexically: "event_count" vs "evidence_chain_hash":
        # position 0-4 "event" == "evide" — at position 4 'n' (0x6E) vs
        # 'e' (0x65), so "evidence..." sorts BEFORE "event_count". Rather
        # than hand-ranking, just assert the output is a valid JSON object
        # whose key order matches sorted.
        parsed = json.loads(raw)
        actual_keys = list(parsed.keys())
        assert actual_keys == sorted(actual_keys), f"JCS must sort keys; got {actual_keys}"

    def test_no_insignificant_whitespace(self, sample_payload: AttestationPayloadV1) -> None:
        """JCS strips all insignificant whitespace — no spaces or newlines
        between tokens."""
        raw = canonical_bytes(sample_payload).decode("utf-8")
        assert "\n" not in raw
        # Only spaces that are allowed are inside string values, which
        # our payload doesn't contain — so zero space bytes total.
        assert " " not in raw

    def test_rfc3339_timestamp_with_z(self, sample_payload: AttestationPayloadV1) -> None:
        """Timestamps are serialized with ``Z`` suffix (not ``+00:00``)."""
        parsed = json.loads(canonical_bytes(sample_payload))
        assert parsed["session_start"].endswith("Z")
        assert parsed["session_end"].endswith("Z")
        assert parsed["signed_at"].endswith("Z")
        assert "+00:00" not in parsed["signed_at"]

    def test_uuid_serialized_as_lowercase_string(
        self, sample_payload: AttestationPayloadV1
    ) -> None:
        parsed = json.loads(canonical_bytes(sample_payload))
        assert parsed["session_id"] == "b8f2c1a0-4e6d-4e2a-9f1a-3c2b0d4e8f7a"
        assert parsed["org_id"] == "f1e2d3c4-b5a6-4798-8877-66554433abcd"

    def test_naive_datetime_rejected(self) -> None:
        """Naive (tz-unaware) datetimes are a signing footgun — reject."""
        with pytest.raises(ValueError, match="timezone-aware"):
            AttestationPayloadV1(
                schema_version=1,
                session_id=uuid.uuid4(),
                org_id=uuid.uuid4(),
                evidence_chain_hash="a" * 64,
                first_audit_id=1,
                last_audit_id=1,
                event_count=1,
                session_start=datetime.datetime(2026, 4, 17, 13, 42, 0),  # naive
                session_end=datetime.datetime(2026, 4, 17, 13, 47, 0, tzinfo=datetime.UTC),
                signed_at=datetime.datetime(2026, 4, 17, 13, 47, 0, tzinfo=datetime.UTC),
                signer_key_id="projects/.../cryptoKeyVersions/1",
            ).to_canonical_dict()


# ---------------------------------------------------------------------------
# PAE (DSSE Pre-Authentication Encoding)
# ---------------------------------------------------------------------------


class TestPAE:
    def test_known_vector_empty_body(self) -> None:
        """PAE('application/x', b'') == b'DSSEv1 13 application/x 0 '."""
        assert pae("application/x", b"") == b"DSSEv1 13 application/x 0 "

    def test_known_vector_simple(self) -> None:
        """PAE with short type + body."""
        result = pae("app/vnd.test", b"hi")
        assert result == b"DSSEv1 12 app/vnd.test 2 hi"

    def test_length_prefixes_are_byte_counts_not_char_counts(self) -> None:
        """UTF-8 multi-byte characters — length prefix must count bytes."""
        body = "é".encode()  # 2 bytes
        result = pae("application/json", body)
        assert result == b"DSSEv1 16 application/json 2 \xc3\xa9"

    def test_domain_separation(self) -> None:
        """Different (type, body) pairs that happen to concatenate the
        same way MUST produce different PAE outputs."""
        a = pae("type/a", b"body1-longer")
        b = pae("type/a-body", b"1-longer")
        assert a != b


# ---------------------------------------------------------------------------
# Round-trip: sign + verify
# ---------------------------------------------------------------------------


class TestSignVerifyRoundTrip:
    def test_happy_path(
        self,
        sample_payload: AttestationPayloadV1,
        ec_keypair: tuple[ec.EllipticCurvePrivateKey, bytes],
    ) -> None:
        """Sign → envelope → verify returns an equal payload."""
        private_key, public_pem = ec_keypair
        signer = local_ecdsa_signer(private_key)

        envelope = sign_payload(sample_payload, signer)
        assert envelope.payloadType == PAYLOAD_TYPE
        assert len(envelope.signatures) == 1
        assert envelope.signatures[0].keyid == sample_payload.signer_key_id

        verified = verify_envelope(envelope, public_pem)
        assert verified == sample_payload

    def test_envelope_serializes_to_json(
        self,
        sample_payload: AttestationPayloadV1,
        ec_keypair: tuple[ec.EllipticCurvePrivateKey, bytes],
    ) -> None:
        """The envelope is a plain JSON object — can be dumped/loaded."""
        private_key, public_pem = ec_keypair
        envelope = sign_payload(sample_payload, local_ecdsa_signer(private_key))

        serialized = envelope.model_dump_json()
        round_tripped = DSSEEnvelope.model_validate_json(serialized)
        assert verify_envelope(round_tripped, public_pem) == sample_payload

    def test_signature_is_der_encoded(
        self,
        sample_payload: AttestationPayloadV1,
        ec_keypair: tuple[ec.EllipticCurvePrivateKey, bytes],
    ) -> None:
        """The signature bytes inside the base64 wrapper are ASN.1 DER
        (starts with 0x30 SEQUENCE tag). This is what GCP KMS returns
        for EC_SIGN_P256_SHA256, so local and prod stay compatible."""
        private_key, _ = ec_keypair
        envelope = sign_payload(sample_payload, local_ecdsa_signer(private_key))
        sig_bytes = base64.b64decode(envelope.signatures[0].sig)
        assert sig_bytes[0] == 0x30, "ECDSA signature should be DER SEQUENCE"


# ---------------------------------------------------------------------------
# Negative cases — verification must fail loudly, not silently
# ---------------------------------------------------------------------------


class TestVerifyRejects:
    def test_tampered_payload(
        self,
        sample_payload: AttestationPayloadV1,
        ec_keypair: tuple[ec.EllipticCurvePrivateKey, bytes],
    ) -> None:
        """Flip one byte in the payload — signature must fail."""
        private_key, public_pem = ec_keypair
        envelope = sign_payload(sample_payload, local_ecdsa_signer(private_key))

        # Re-encode the payload with a tampered event_count.
        payload_dict = sample_payload.to_canonical_dict()
        payload_dict["event_count"] = 999
        envelope.payload = base64.b64encode(rfc8785.dumps(payload_dict)).decode("ascii")

        with pytest.raises(AttestationVerificationError, match="signature does not verify"):
            verify_envelope(envelope, public_pem)

    def test_tampered_signature(
        self,
        sample_payload: AttestationPayloadV1,
        ec_keypair: tuple[ec.EllipticCurvePrivateKey, bytes],
    ) -> None:
        private_key, public_pem = ec_keypair
        envelope = sign_payload(sample_payload, local_ecdsa_signer(private_key))

        # Flip the last byte of the signature.
        sig = bytearray(base64.b64decode(envelope.signatures[0].sig))
        sig[-1] ^= 0x01
        envelope.signatures[0] = DSSESignature(
            keyid=envelope.signatures[0].keyid,
            sig=base64.b64encode(bytes(sig)).decode("ascii"),
        )

        with pytest.raises(AttestationVerificationError):
            verify_envelope(envelope, public_pem)

    def test_wrong_public_key(
        self,
        sample_payload: AttestationPayloadV1,
        ec_keypair: tuple[ec.EllipticCurvePrivateKey, bytes],
    ) -> None:
        private_key, _ = ec_keypair
        envelope = sign_payload(sample_payload, local_ecdsa_signer(private_key))

        # Generate a DIFFERENT keypair and try to verify with its public key.
        other_key = ec.generate_private_key(ec.SECP256R1())
        other_pem = other_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        with pytest.raises(AttestationVerificationError, match="signature does not verify"):
            verify_envelope(envelope, other_pem)

    def test_wrong_payload_type(
        self,
        sample_payload: AttestationPayloadV1,
        ec_keypair: tuple[ec.EllipticCurvePrivateKey, bytes],
    ) -> None:
        """An envelope claiming a different payload type is rejected
        before any crypto work — this is the domain separation check
        DSSE's PAE gives us for free."""
        private_key, public_pem = ec_keypair
        envelope = sign_payload(sample_payload, local_ecdsa_signer(private_key))
        mutated = copy.deepcopy(envelope)
        mutated.payloadType = "application/vnd.evil+json"

        with pytest.raises(AttestationVerificationError, match="unexpected payloadType"):
            verify_envelope(mutated, public_pem)

    def test_rsa_public_key_rejected(self, sample_payload: AttestationPayloadV1) -> None:
        """Only EC public keys are accepted — reject RSA even before
        attempting verification."""
        from cryptography.hazmat.primitives.asymmetric import rsa

        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_pem = rsa_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        # Construct any envelope (contents don't matter for this check).
        envelope = DSSEEnvelope(
            payloadType=PAYLOAD_TYPE,
            payload=base64.b64encode(canonical_bytes(sample_payload)).decode("ascii"),
            signatures=[DSSESignature(keyid="k", sig=base64.b64encode(b"fake").decode("ascii"))],
        )
        with pytest.raises(AttestationVerificationError, match="not an elliptic-curve key"):
            verify_envelope(envelope, rsa_pem)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestPayloadSchema:
    def test_extra_fields_rejected(self) -> None:
        """``extra="forbid"`` means unknown fields blow up at parse time
        — important so v1 verifiers don't silently accept v2 payloads."""
        with pytest.raises(ValueError):
            AttestationPayloadV1.model_validate(
                {
                    "schema_version": 1,
                    "session_id": str(uuid.uuid4()),
                    "org_id": str(uuid.uuid4()),
                    "evidence_chain_hash": "a" * 64,
                    "first_audit_id": 1,
                    "last_audit_id": 1,
                    "event_count": 1,
                    "session_start": "2026-04-17T00:00:00Z",
                    "session_end": "2026-04-17T00:01:00Z",
                    "signed_at": "2026-04-17T00:01:00Z",
                    "signer_key_id": "projects/.../cryptoKeyVersions/1",
                    "future_field": "should cause reject",
                }
            )

    def test_evidence_chain_hash_must_be_hex(self) -> None:
        with pytest.raises(ValueError):
            AttestationPayloadV1(
                schema_version=1,
                session_id=uuid.uuid4(),
                org_id=uuid.uuid4(),
                evidence_chain_hash="NOT-HEX-" + "a" * 56,
                first_audit_id=1,
                last_audit_id=1,
                event_count=1,
                session_start=datetime.datetime(2026, 4, 17, 0, 0, 0, tzinfo=datetime.UTC),
                session_end=datetime.datetime(2026, 4, 17, 0, 1, 0, tzinfo=datetime.UTC),
                signed_at=datetime.datetime(2026, 4, 17, 0, 1, 0, tzinfo=datetime.UTC),
                signer_key_id="projects/.../cryptoKeyVersions/1",
            )

    def test_schema_version_literal(self) -> None:
        """schema_version must be exactly 1 — any other value (including
        2) is rejected. This is the gate that makes v1 verifiers fail
        loudly on v2 inputs instead of silently ignoring unknown fields."""
        with pytest.raises(ValueError):
            AttestationPayloadV1.model_validate(
                {
                    "schema_version": 2,
                    "session_id": str(uuid.uuid4()),
                    "org_id": str(uuid.uuid4()),
                    "evidence_chain_hash": "a" * 64,
                    "first_audit_id": 1,
                    "last_audit_id": 1,
                    "event_count": 1,
                    "session_start": "2026-04-17T00:00:00Z",
                    "session_end": "2026-04-17T00:01:00Z",
                    "signed_at": "2026-04-17T00:01:00Z",
                    "signer_key_id": "projects/.../cryptoKeyVersions/1",
                }
            )


# ---------------------------------------------------------------------------
# Signer contract
# ---------------------------------------------------------------------------


class TestLocalSigner:
    def test_rejects_non_p256_key(self) -> None:
        """The local signer refuses anything other than SECP256R1 — we
        don't want a test accidentally signing with P-384 and then
        production failing to verify."""
        p384 = ec.generate_private_key(ec.SECP384R1())
        with pytest.raises(ValueError, match="P-256"):
            local_ecdsa_signer(p384)
