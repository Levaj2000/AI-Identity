"""Manifest canonicalization + DSSE signing for compliance exports.

The manifest is the thing an auditor actually verifies against. It
commits to every file in the archive by SHA-256 so tampering with any
artifact after export invalidates the whole bundle.

This module is intentionally parallel to
``common.schemas.forensic_attestation.sign_payload`` — same DSSE
machinery, different ``payloadType``. Domain separation is enforced
via the distinct payloadType so a forensic attestation signature can't
be replayed as a manifest signature and vice versa.

See ADR-002 §Bundle structure for the manifest schema and §Verification
for the auditor-side verification walk.
"""

from __future__ import annotations

import base64
import datetime
from typing import TYPE_CHECKING

import rfc8785

from common.schemas.forensic_attestation import DSSEEnvelope, DSSESignature, pae

if TYPE_CHECKING:
    import uuid

    from common.forensic.signer import SignerHandle

# Domain-separated from the attestation payloadType. An auditor or
# verifier that expects this type will reject an attestation envelope
# and vice versa — same key, different domains.
EXPORT_MANIFEST_PAYLOAD_TYPE = "application/vnd.ai-identity.export-manifest+json"

# Bump when the manifest schema changes in a non-additive way.
MANIFEST_SCHEMA_VERSION = 1


class ManifestArtifact(dict):
    """Single-entry shape — intentionally a dict to keep JCS trivial.

    Fields: ``path`` (relative to archive root), ``sha256`` (hex),
    ``bytes`` (int), ``controls`` (list[str], may be empty).
    """


def build_manifest(
    *,
    export_id: uuid.UUID,
    org_id: uuid.UUID,
    profile: str,
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
    built_at: datetime.datetime,
    signer_key_id: str,
    artifacts: list[dict],
    artifact_schema_versions: dict[str, str] | None = None,
) -> dict:
    """Build the canonical manifest dict.

    Callers should not hand-construct this — routing through this
    builder guarantees the schema version, field order, and RFC 3339
    timestamp serialization match what the auditor CLI expects.

    ``artifact_schema_versions`` maps artifact path → version string
    (e.g. ``{"change_log.csv": "2.0"}``). Omitted when empty so
    pre-v2 manifests stay byte-identical for regression tests.
    """
    manifest: dict = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "export_id": str(export_id),
        "org_id": str(org_id),
        "profile": profile,
        "audit_period_start": _rfc3339_z(audit_period_start),
        "audit_period_end": _rfc3339_z(audit_period_end),
        "built_at": _rfc3339_z(built_at),
        "signer_key_id": signer_key_id,
        "artifacts": artifacts,
    }
    if artifact_schema_versions:
        manifest["artifact_schema_versions"] = dict(artifact_schema_versions)
    return manifest


def canonical_manifest_bytes(manifest: dict) -> bytes:
    """RFC 8785 JCS bytes of the manifest — the exact signed form."""
    return rfc8785.dumps(manifest)


def sign_manifest(manifest: dict, signer: SignerHandle) -> DSSEEnvelope:
    """Sign the manifest with the given key → DSSE envelope.

    Mirrors ``common.schemas.forensic_attestation.sign_payload`` but
    with ``EXPORT_MANIFEST_PAYLOAD_TYPE`` baked in for domain
    separation. The canonical bytes are deterministic so re-signing an
    identical manifest produces the same envelope modulo the ECDSA
    nonce.
    """
    payload_bytes = canonical_manifest_bytes(manifest)
    signing_input = pae(EXPORT_MANIFEST_PAYLOAD_TYPE, payload_bytes)
    signature_der = signer.sign(signing_input)
    return DSSEEnvelope(
        payloadType=EXPORT_MANIFEST_PAYLOAD_TYPE,
        payload=base64.b64encode(payload_bytes).decode("ascii"),
        signatures=[
            DSSESignature(
                keyid=signer.key_id,
                sig=base64.b64encode(signature_der).decode("ascii"),
            ),
        ],
    )


def _rfc3339_z(value: datetime.datetime) -> str:
    """Match attestation timestamps: UTC, trailing ``Z``, no offset."""
    if value.tzinfo is None:
        msg = "manifest timestamps must be timezone-aware UTC"
        raise ValueError(msg)
    utc = value.astimezone(datetime.UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
