"""Forensic attestation v1 — signed payload format for Milestone #33.

This module defines the wire format for the cryptographically signed
statements AI Identity issues at session close. See
:doc:`docs/forensics/attestation-format.md` for the full specification
including design rationale, verification algorithm, and trust-model
boundaries.

The split of concerns in this file:

* :class:`AttestationPayloadV1` — the *signed content*. What a verifier
  will look at to answer "what is AI Identity claiming?".
* :class:`DSSESignature` / :class:`DSSEEnvelope` — the *transport
  wrapper*. DSSE adds a payload-type tag and base64-encoded signature
  material so existing sigstore/in-toto tooling can consume our
  attestations without bespoke code.
* :func:`canonical_bytes` — JCS (RFC 8785) serialization. Produces the
  exact byte sequence that gets signed.
* :func:`pae` — Pre-Authentication Encoding. The DSSE spec mandates
  signing over PAE(payload_type, payload_bytes), not the raw payload,
  to get free domain separation between unrelated protocols.
* :func:`sign_payload` / :func:`verify_envelope` — the round-trip
  helpers. ``sign_payload`` takes a caller-supplied signer callable so
  the same code path works for both local-ECDSA (tests) and GCP KMS
  ``AsymmetricSign`` (production). No cryptographic material lives in
  this module — it only orchestrates bytes.

The signer callable contract:

    def signer(message_bytes: bytes) -> bytes: ...

        Returns an ASN.1 DER-encoded ECDSA-P256-SHA256 signature over
        SHA-256(message_bytes). This matches what
        ``kms.asymmetric_sign`` returns when the key algorithm is
        ``EC_SIGN_P256_SHA256``.

Intentionally NOT in this file:

* KMS client wiring (deferred to #263).
* Session lifecycle / "when to sign" decision (deferred to #263).
* Retrieval API endpoint (deferred to #264).
* Chain verification (that lives in ``common/audit/writer.py``
  ``verify_chain``; this module's verify is signature-only).
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import uuid  # noqa: TC003 — used by Pydantic at model-build time, not only in types
from typing import Literal

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal[1] = 1
PAYLOAD_TYPE = "application/vnd.ai-identity.attestation+json"
DSSE_PREAMBLE = b"DSSEv1"


class AttestationPayloadV1(BaseModel):
    """The signed content of a v1 forensic attestation.

    Every field is required. Optional fields are an anti-pattern in
    signed formats — a verifier that has to reason about "maybe this
    field is there" has a larger attack surface than one that rejects
    anything missing.

    Forward compatibility is handled by ``schema_version``: v2 adds
    new required fields and bumps the version; v1 verifiers reject v2
    loudly rather than silently ignoring the unknown fields.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = Field(
        default=1,
        description="Format version. Verifiers MUST reject unknown versions.",
    )
    session_id: uuid.UUID = Field(
        description="Opaque producer identifier for the session being attested.",
    )
    org_id: uuid.UUID = Field(
        description=(
            "Org whose HMAC key was used to build the audit chain. "
            "Needed to resolve the right verify_key during chain check."
        ),
    )
    evidence_chain_hash: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description=(
            "entry_hash of the last audit_log row in the committed range. "
            "SHA-256 hex (lowercase, no prefix)."
        ),
    )
    first_audit_id: int = Field(
        ge=1,
        description="First audit_log.id in the committed range (inclusive).",
    )
    last_audit_id: int = Field(
        ge=1,
        description=(
            "Last audit_log.id in the committed range (inclusive). "
            "Its entry_hash == evidence_chain_hash."
        ),
    )
    event_count: int = Field(
        ge=1,
        description="Number of audit rows in the committed range.",
    )
    session_start: datetime.datetime = Field(
        description="UTC start of the session window. Serialized RFC 3339 with Z suffix.",
    )
    session_end: datetime.datetime = Field(
        description="UTC end of the session window. Serialized RFC 3339 with Z suffix.",
    )
    signed_at: datetime.datetime = Field(
        description="UTC wall-clock time the signer produced the signature.",
    )
    signer_key_id: str = Field(
        min_length=1,
        max_length=512,
        description=(
            "Fully-qualified KMS key-version resource name: "
            "projects/.../cryptoKeyVersions/N. Pins the specific version "
            "for historical verifiability across rotations."
        ),
    )

    def to_canonical_dict(self) -> dict:
        """Return a plain dict in the shape that gets JCS-serialized.

        Pydantic's default ``model_dump()`` returns UUIDs as
        ``uuid.UUID`` and datetimes as ``datetime.datetime`` — JCS
        requires JSON-native types, so we normalize to strings here.
        Timestamps are emitted with a ``Z`` suffix (not ``+00:00``) for
        readability and to match the convention used in the design doc
        example.
        """
        return {
            "schema_version": self.schema_version,
            "session_id": str(self.session_id),
            "org_id": str(self.org_id),
            "evidence_chain_hash": self.evidence_chain_hash,
            "first_audit_id": self.first_audit_id,
            "last_audit_id": self.last_audit_id,
            "event_count": self.event_count,
            "session_start": _rfc3339_z(self.session_start),
            "session_end": _rfc3339_z(self.session_end),
            "signed_at": _rfc3339_z(self.signed_at),
            "signer_key_id": self.signer_key_id,
        }


class DSSESignature(BaseModel):
    """One signature entry inside a DSSE envelope."""

    model_config = ConfigDict(extra="forbid")

    keyid: str = Field(description="Key identifier (KMS key-version resource path).")
    sig: str = Field(description="Base64-encoded DER ECDSA signature.")


class DSSEEnvelope(BaseModel):
    """DSSE envelope — the on-the-wire form of a signed attestation.

    Matches the spec at
    https://github.com/secure-systems-lab/dsse/blob/master/envelope.md
    """

    model_config = ConfigDict(extra="forbid")

    payloadType: str = Field(  # noqa: N815 — DSSE spec field name
        description="MIME type of the payload; fixed for attestations.",
    )
    payload: str = Field(description="Base64-encoded canonical JSON payload.")
    signatures: list[DSSESignature] = Field(
        min_length=1,
        description="At least one signature. v1 always produces exactly one.",
    )


# ---------------------------------------------------------------------------
# Canonicalization + PAE
# ---------------------------------------------------------------------------


def canonical_bytes(payload: AttestationPayloadV1) -> bytes:
    """Serialize the payload to its canonical signed form (RFC 8785 JCS).

    This is the *exact* byte sequence that, once base64-encoded, goes
    into ``DSSEEnvelope.payload``. Callers should never manually
    ``json.dumps`` a payload for signing — routing through this
    function is the only way to get stable bytes.
    """
    return rfc8785.dumps(payload.to_canonical_dict())


def pae(payload_type: str, payload_bytes: bytes) -> bytes:
    """DSSE Pre-Authentication Encoding.

    PAE("DSSEv1", type, body) = b"DSSEv1 " + len(type) + b" " + type
                              + b" " + len(body) + b" " + body

    Lengths are ASCII-decimal byte counts. All string components are
    UTF-8. The length prefixes give us domain separation between
    unrelated signed protocols at zero cryptographic cost — a signature
    over one (type, body) cannot be replayed as valid over a different
    (type', body') no matter how the concatenations line up.
    """
    type_bytes = payload_type.encode("utf-8")
    return (
        DSSE_PREAMBLE
        + b" "
        + str(len(type_bytes)).encode("ascii")
        + b" "
        + type_bytes
        + b" "
        + str(len(payload_bytes)).encode("ascii")
        + b" "
        + payload_bytes
    )


# ---------------------------------------------------------------------------
# Sign + verify
# ---------------------------------------------------------------------------


def sign_payload(
    payload: AttestationPayloadV1,
    signer: _Signer,
) -> DSSEEnvelope:
    """Produce a DSSE envelope for ``payload`` using ``signer``.

    ``signer`` is a callable ``(bytes) -> bytes`` that returns a
    DER-encoded ECDSA-P256-SHA256 signature over SHA-256 of the input.
    This matches the contract of ``google.cloud.kms_v1.KeyManagementServiceClient.asymmetric_sign``
    for an ``EC_SIGN_P256_SHA256`` key.

    We pass a callable (rather than a key object) so the same code path
    works for both:

    * local-key tests — ``signer`` wraps an in-memory ECDSA private key
    * production — ``signer`` wraps a KMS ``AsymmetricSign`` RPC

    No network or file-system side effects happen inside this module.
    """
    payload_bytes = canonical_bytes(payload)
    signing_input = pae(PAYLOAD_TYPE, payload_bytes)
    signature_der = signer(signing_input)

    return DSSEEnvelope(
        payloadType=PAYLOAD_TYPE,
        payload=base64.b64encode(payload_bytes).decode("ascii"),
        signatures=[
            DSSESignature(
                keyid=payload.signer_key_id,
                sig=base64.b64encode(signature_der).decode("ascii"),
            ),
        ],
    )


def verify_envelope(
    envelope: DSSEEnvelope,
    public_key_pem: bytes,
) -> AttestationPayloadV1:
    """Verify an envelope's signature against ``public_key_pem``.

    On success, returns the parsed :class:`AttestationPayloadV1`.
    On failure, raises :class:`AttestationVerificationError` with a
    human-readable reason.

    This verifies ONLY the cryptographic signature + the schema
    version. It does **not** walk the HMAC audit chain — that check
    belongs in the forensic CLI (#266) / audit module, because it
    needs access to the audit rows and the org's verify key. Keep the
    layers separate.
    """
    if envelope.payloadType != PAYLOAD_TYPE:
        raise AttestationVerificationError(
            f"unexpected payloadType: {envelope.payloadType!r} (expected {PAYLOAD_TYPE!r})"
        )
    if len(envelope.signatures) != 1:
        raise AttestationVerificationError(
            f"expected exactly 1 signature, got {len(envelope.signatures)}"
        )

    try:
        payload_bytes = base64.b64decode(envelope.payload, validate=True)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        raise AttestationVerificationError(f"payload is not valid base64: {exc}") from exc

    try:
        signature_der = base64.b64decode(envelope.signatures[0].sig, validate=True)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        raise AttestationVerificationError(f"signature is not valid base64: {exc}") from exc

    public_key = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise AttestationVerificationError(
            "public key is not an elliptic-curve key (attestation format requires ECDSA P-256)"
        )

    signing_input = pae(PAYLOAD_TYPE, payload_bytes)
    try:
        public_key.verify(signature_der, signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise AttestationVerificationError("signature does not verify") from exc

    # Re-parse the payload through the pydantic model so callers get a
    # validated, typed object back (and we catch v2 payloads that a v1
    # verifier should reject).
    try:
        parsed = AttestationPayloadV1.model_validate_json(payload_bytes)
    except Exception as exc:
        raise AttestationVerificationError(
            f"payload does not match AttestationPayloadV1 schema: {exc}"
        ) from exc

    # Defense in depth — schema_version is already constrained by the
    # Literal[1] field, but an explicit check makes the intent
    # unambiguous if the Literal is ever relaxed.
    if parsed.schema_version != SCHEMA_VERSION:
        raise AttestationVerificationError(f"unsupported schema_version: {parsed.schema_version}")

    return parsed


class AttestationVerificationError(Exception):
    """Raised by :func:`verify_envelope` on any verification failure.

    Caught as a single exception type so callers can distinguish
    "signature is bad" from "KMS is unreachable" without parsing
    error messages.
    """


# ---------------------------------------------------------------------------
# Local-key signer (testing + tooling)
# ---------------------------------------------------------------------------


def local_ecdsa_signer(private_key: ec.EllipticCurvePrivateKey) -> _Signer:
    """Wrap an in-memory ECDSA-P256 private key as a ``_Signer``.

    Used by the test suite and by any ad-hoc tooling (e.g. a future
    developer-mode CLI that signs with a local key rather than KMS).
    Production signing always goes through a KMS-backed signer — this
    helper is *not* a substitute.
    """
    if not isinstance(private_key.curve, ec.SECP256R1):
        raise ValueError(
            "local_ecdsa_signer requires a P-256 (SECP256R1) private key; "
            f"got {private_key.curve.name}"
        )

    def _sign(message: bytes) -> bytes:
        return private_key.sign(message, ec.ECDSA(hashes.SHA256()))

    return _sign


def hash_signing_input(payload_bytes: bytes) -> bytes:
    """SHA-256 of PAE(PAYLOAD_TYPE, payload_bytes).

    Convenience for tests + any path that wants to pre-hash before
    handing off to a signer that takes an already-hashed digest (some
    KMS client modes accept either). Not used by :func:`sign_payload`
    itself — we pass the full signing input so each signer can decide
    whether to hash internally (ECDSA with SHA-256 always hashes).
    """
    return hashlib.sha256(pae(PAYLOAD_TYPE, payload_bytes)).digest()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

from collections.abc import Callable  # noqa: E402 — type alias reference

_Signer = Callable[[bytes], bytes]


def _rfc3339_z(dt: datetime.datetime) -> str:
    """Format ``dt`` as RFC 3339 with a ``Z`` suffix.

    Requires the datetime to be timezone-aware and UTC (or convertible
    to UTC without ambiguity). Naive datetimes are a signing footgun —
    we reject them loudly.
    """
    if dt.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware (attach datetime.UTC)")
    utc = dt.astimezone(datetime.UTC)
    # Drop microseconds for a shorter, more typical RFC 3339 wire form.
    # Nothing in the verification depends on sub-second precision.
    utc = utc.replace(microsecond=0)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
