"""Signed Merkle checkpoint for the Evidence Anchor.

A *checkpoint* commits, with a single ECDSA-P256 signature, to a Merkle
root over a batch of audit ``entry_hash`` values. It is the bridge that
turns the symmetric HMAC audit chain into something a third party can
verify with no shared secret.

It deliberately reuses the forensic signing stack that already exists in
the tree rather than introducing parallel crypto:

* signing key + KMS-backed rotation  → ``common.forensic.signer``
* public-key publication (JWKS)       → ``common.forensic.jwks``
* DSSE envelope + PAE domain sep      → ``common.schemas.forensic_attestation``

The checkpoint uses its OWN DSSE ``payloadType`` so a checkpoint signature
can never be replayed as a v1 forensic attestation (or vice versa) — the
PAE length-prefix + the type string give that separation for free.

Verification (``verify_checkpoint`` / ``verify_entry_inclusion``) depends
only on the *public* key and SHA-256. It imports nothing from the audit
writer and never touches ``AUDIT_HMAC_KEY`` — that independence is the
whole point of the Anchor and is asserted directly in the spike tests.
"""

from __future__ import annotations

import base64
import datetime
import uuid  # noqa: TC003 — used by Pydantic at model-build time, not only in types
from collections.abc import Callable

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import BaseModel, ConfigDict, Field

from common.forensic import merkle
from common.schemas.forensic_attestation import (
    AttestationVerificationError,
    DSSEEnvelope,
    DSSESignature,
    pae,
)

# Distinct from the attestation PAYLOAD_TYPE — domain separation.
CHECKPOINT_PAYLOAD_TYPE = "application/vnd.ai-identity.anchor-checkpoint+json"

_Signer = Callable[[bytes], bytes]


def _rfc3339_z(dt: datetime.datetime) -> str:
    """UTC RFC 3339 with a ``Z`` suffix (matches the attestation convention)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.UTC).replace(tzinfo=None)
    return dt.replace(microsecond=dt.microsecond).isoformat() + "Z"


class MerkleCheckpointV1(BaseModel):
    """The signed content of a v1 Evidence Anchor checkpoint.

    Like the attestation payload, every field is required and unknown
    fields are forbidden — a signed format with optional fields is a
    larger attack surface for a verifier to reason about.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(
        default=1, description="Format version; verifiers reject unknown versions."
    )
    org_id: uuid.UUID = Field(description="Org whose audit chain this batch was drawn from.")
    tree_size: int = Field(
        ge=1, description="Number of leaves (audit entries) committed by the root."
    )
    merkle_root: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 hex of the RFC 6962 Merkle root over the batch's entry_hashes.",
    )
    first_audit_id: int = Field(
        ge=1, description="First audit_log.id in the committed batch (inclusive)."
    )
    last_audit_id: int = Field(
        ge=1, description="Last audit_log.id in the committed batch (inclusive)."
    )
    signed_at: datetime.datetime = Field(
        description="UTC wall-clock time the signer produced the signature."
    )
    signer_key_id: str = Field(
        min_length=1,
        max_length=512,
        description="Signer key id (KMS key-version resource path, or local:<sha256>). Pins the key across rotations.",
    )

    def to_canonical_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "org_id": str(self.org_id),
            "tree_size": self.tree_size,
            "merkle_root": self.merkle_root,
            "first_audit_id": self.first_audit_id,
            "last_audit_id": self.last_audit_id,
            "signed_at": _rfc3339_z(self.signed_at),
            "signer_key_id": self.signer_key_id,
        }


def canonical_bytes(checkpoint: MerkleCheckpointV1) -> bytes:
    """RFC 8785 (JCS) canonical bytes — the exact sequence that gets signed."""
    return rfc8785.dumps(checkpoint.to_canonical_dict())


def build_checkpoint(
    *,
    org_id: uuid.UUID,
    entry_hashes: list[str],
    first_audit_id: int,
    last_audit_id: int,
    signer_key_id: str,
    signed_at: datetime.datetime,
) -> tuple[MerkleCheckpointV1, merkle.MerkleTree]:
    """Build a Merkle tree over ``entry_hashes`` and the matching checkpoint.

    ``entry_hashes`` are lowercase SHA-256 hex strings (the audit chain's
    ``entry_hash`` column). The tree leaves are their raw decoded bytes,
    so an outside verifier reconstructs a leaf as ``bytes.fromhex(entry_hash)``.
    """
    if not entry_hashes:
        raise ValueError("cannot build a checkpoint over an empty batch")
    tree = merkle.MerkleTree([bytes.fromhex(h) for h in entry_hashes])
    checkpoint = MerkleCheckpointV1(
        org_id=org_id,
        tree_size=tree.size,
        merkle_root=tree.root.hex(),
        first_audit_id=first_audit_id,
        last_audit_id=last_audit_id,
        signed_at=signed_at,
        signer_key_id=signer_key_id,
    )
    return checkpoint, tree


def sign_checkpoint(checkpoint: MerkleCheckpointV1, signer: _Signer) -> DSSEEnvelope:
    """Produce a DSSE envelope over ``checkpoint`` using ``signer``.

    ``signer`` is the same ``(bytes) -> DER-ECDSA-P256-SHA256`` callable
    used by the attestation path (``SignerHandle.sign``), so a KMS-backed
    signer and a local-key test signer share this code unchanged.
    """
    payload_bytes = canonical_bytes(checkpoint)
    signing_input = pae(CHECKPOINT_PAYLOAD_TYPE, payload_bytes)
    signature_der = signer(signing_input)
    return DSSEEnvelope(
        payloadType=CHECKPOINT_PAYLOAD_TYPE,
        payload=base64.b64encode(payload_bytes).decode("ascii"),
        signatures=[
            DSSESignature(
                keyid=checkpoint.signer_key_id,
                sig=base64.b64encode(signature_der).decode("ascii"),
            ),
        ],
    )


def verify_checkpoint(envelope: DSSEEnvelope, public_key_pem: bytes) -> MerkleCheckpointV1:
    """Verify a checkpoint envelope's signature against a *public* key.

    Returns the parsed checkpoint on success; raises
    :class:`AttestationVerificationError` on any failure. Depends only on
    the public key + SHA-256 — never on ``AUDIT_HMAC_KEY``.
    """
    if envelope.payloadType != CHECKPOINT_PAYLOAD_TYPE:
        raise AttestationVerificationError(
            f"unexpected payloadType: {envelope.payloadType!r} (expected {CHECKPOINT_PAYLOAD_TYPE!r})"
        )
    if len(envelope.signatures) != 1:
        raise AttestationVerificationError(
            f"expected exactly 1 signature, got {len(envelope.signatures)}"
        )

    try:
        payload_bytes = base64.b64decode(envelope.payload, validate=True)
        signature_der = base64.b64decode(envelope.signatures[0].sig, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise AttestationVerificationError(f"malformed base64 in envelope: {exc}") from exc

    public_key = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise AttestationVerificationError(
            "public key is not an elliptic-curve key (need ECDSA P-256)"
        )

    signing_input = pae(CHECKPOINT_PAYLOAD_TYPE, payload_bytes)
    try:
        public_key.verify(signature_der, signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise AttestationVerificationError("signature verification failed") from exc

    checkpoint = MerkleCheckpointV1.model_validate_json(payload_bytes)
    if checkpoint.schema_version != 1:
        raise AttestationVerificationError(
            f"unsupported checkpoint schema_version: {checkpoint.schema_version}"
        )
    return checkpoint


def verify_entry_inclusion(
    *,
    entry_hash: str,
    index: int,
    envelope: DSSEEnvelope,
    proof: list[bytes],
    public_key_pem: bytes,
) -> MerkleCheckpointV1:
    """End-to-end offline check that one audit entry is committed.

    Verifies (1) the checkpoint signature against the public key, then
    (2) that ``entry_hash`` is the leaf at ``index`` under the signed
    Merkle root. Raises :class:`AttestationVerificationError` if either
    fails; returns the verified checkpoint on success.

    This is exactly what a court, auditor, or counterparty runs with only
    the published JWKS public key and the evidence bundle in hand — no
    database access, no ``AUDIT_HMAC_KEY``.
    """
    checkpoint = verify_checkpoint(envelope, public_key_pem)
    ok = merkle.verify_inclusion(
        leaf_data=bytes.fromhex(entry_hash),
        index=index,
        tree_size=checkpoint.tree_size,
        proof=proof,
        root=bytes.fromhex(checkpoint.merkle_root),
    )
    if not ok:
        raise AttestationVerificationError(
            f"entry_hash not included at index {index} under the signed Merkle root"
        )
    return checkpoint
