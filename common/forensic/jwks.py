"""JWKS (JSON Web Key Set) builder for forensic attestation public keys.

Publishes the public half of the signing key(s) so offline verifiers
can resolve ``AttestationPayloadV1.signer_key_id`` → public key without
operational trust in AI Identity. See the "Key rotation & historical
verifiability" section of ``docs/forensics/attestation-format.md`` for
why every historical key version must remain resolvable.

Two backends mirror :mod:`common.forensic.signer`:

* **GCP KMS** — list all versions of the configured key (strip the
  ``/cryptoKeyVersions/N`` suffix to get the parent key path), call
  ``GetPublicKey`` on each non-destroyed version, convert the returned
  PEM to a JWK entry.
* **Local PEM** — publish the one key's public half. Dev / test only.

The shape of each JWK entry follows RFC 7517 for the standard fields
(``kty``, ``crv``, ``x``, ``y``, ``kid``, ``alg``, ``use``) plus a few
custom ``ai_identity:*`` fields that carry rotation metadata a verifier
needs: state (enabled/disabled), creation time, optional
not-before/not-after bounds.

This module does not talk to the network on import. ``build_jwks()``
calls KMS lazily when invoked. The router is responsible for handling
``ForensicSignerConfigError`` (no backend configured) by returning an
empty keys list — that's a legitimate "pre-rollout" state, not a 500.
"""

from __future__ import annotations

import base64
import hashlib
import re
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.config.settings import Settings  # noqa: TC002 — runtime default arg annotation
from common.config.settings import settings as default_settings

# KMS resource path: projects/X/locations/Y/keyRings/Z/cryptoKeys/K/cryptoKeyVersions/N
_KEY_VERSION_RE = re.compile(
    r"^(?P<parent>projects/[^/]+/locations/[^/]+/keyRings/[^/]+/cryptoKeys/[^/]+)"
    r"/cryptoKeyVersions/\d+$"
)

_LOCAL_KEY_ID_PREFIX = "local:"


def build_jwks(settings_obj: Settings | None = None) -> dict[str, Any]:
    """Return the full JWKS document, ready to be JSON-serialized.

    Shape: ``{"keys": [<jwk>, ...]}``. On an unconfigured signer (neither
    KMS nor local PEM set) returns ``{"keys": []}`` — the endpoint is
    always resolvable, even before the first key is provisioned, so
    verifiers don't have to handle "URL unreachable" as a separate case
    from "no keys yet".
    """
    s = settings_obj or default_settings

    if s.forensic_signing_key_id and s.forensic_signing_key_pem:
        # Defensive: matches the signer module's both-set check.
        # A real deployment with both env vars set is misconfigured;
        # better to publish no keys than the wrong ones.
        return {"keys": []}

    if s.forensic_signing_key_id:
        return {"keys": _kms_jwks(s.forensic_signing_key_id)}

    if s.forensic_signing_key_pem:
        return {"keys": [_local_jwk(s.forensic_signing_key_pem)]}

    return {"keys": []}


# ---------------------------------------------------------------------------
# KMS backend
# ---------------------------------------------------------------------------


def _kms_jwks(key_version_id: str) -> list[dict[str, Any]]:
    """List every non-destroyed version of the parent key as JWK entries.

    Historical verifiability requirement: old versions that signed
    attestations in the past must still appear here so a verifier can
    resolve their ``kid``. Destroyed versions cannot sign (and we
    cannot fetch their public key anyway) so they're omitted — a
    verifier that encounters a destroyed-key attestation will correctly
    see "kid not published" and fail closed.
    """
    match = _KEY_VERSION_RE.match(key_version_id)
    if not match:
        # Malformed config — treat as "no keys" rather than raising,
        # so the endpoint stays up. The signer will complain loudly
        # next time someone tries to POST an attestation.
        return []

    parent = match.group("parent")

    try:
        from google.cloud import kms_v1
    except ImportError:  # pragma: no cover — covered by api/requirements.txt
        return []

    client = kms_v1.KeyManagementServiceClient()

    entries: list[dict[str, Any]] = []
    for version in client.list_crypto_key_versions(request={"parent": parent}):
        state_name = _kms_state_name(version.state)
        if state_name == "destroyed":
            continue

        try:
            public_key = client.get_public_key(request={"name": version.name})
        except Exception:  # pragma: no cover — transient KMS errors
            # Skip this version rather than fail the whole JWKS —
            # other versions may still be reachable.
            continue

        jwk = _pem_to_jwk(public_key.pem.encode("utf-8"), kid=version.name)
        jwk["ai_identity:state"] = state_name
        if version.create_time is not None:
            jwk["ai_identity:created_at"] = _proto_ts_to_iso(version.create_time)
        entries.append(jwk)

    return entries


def _kms_state_name(state: Any) -> str:
    """Normalize KMS enum state to a lowercase string.

    The kms_v1 client exposes state as an IntEnum with names like
    ``ENABLED``, ``DISABLED``, ``DESTROYED``, ``DESTROY_SCHEDULED``.
    We publish the lowercase form so verifiers don't have to know the
    KMS enum numbering.
    """
    name = getattr(state, "name", str(state))
    return name.lower()


def _proto_ts_to_iso(ts: Any) -> str:
    """Convert a protobuf Timestamp (or anything with ``isoformat()``) to ISO-8601.

    KMS returns ``google.protobuf.Timestamp`` which has a ``.ToDatetime()``
    method; we prefer duck-typing so tests can pass a plain ``datetime``.
    """
    if hasattr(ts, "isoformat"):
        return ts.isoformat().replace("+00:00", "Z")
    if hasattr(ts, "ToDatetime"):
        return ts.ToDatetime().isoformat() + "Z"
    return str(ts)


# ---------------------------------------------------------------------------
# Local-PEM backend
# ---------------------------------------------------------------------------


def _local_jwk(pem: str) -> dict[str, Any]:
    """Build a single JWK for a locally configured PEM signer.

    The ``kid`` uses the same ``local:<sha256>`` scheme as the signer,
    so envelopes signed in dev and this JWKS agree on key identity.
    """
    private_key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        return {}
    public_key = private_key.public_key()
    public_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    kid = _LOCAL_KEY_ID_PREFIX + hashlib.sha256(public_der).hexdigest()

    jwk = _ec_public_key_to_jwk(public_key, kid=kid)
    jwk["ai_identity:state"] = "enabled"
    return jwk


# ---------------------------------------------------------------------------
# PEM / EC-point → JWK conversion
# ---------------------------------------------------------------------------


def _pem_to_jwk(pem_bytes: bytes, *, kid: str) -> dict[str, Any]:
    """Parse a PEM ``SubjectPublicKeyInfo`` and return a JWK dict."""
    public_key = serialization.load_pem_public_key(pem_bytes)
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError(
            f"JWKS publishes ECDSA keys only; got {type(public_key).__name__} for kid={kid!r}"
        )
    return _ec_public_key_to_jwk(public_key, kid=kid)


def _ec_public_key_to_jwk(public_key: ec.EllipticCurvePublicKey, *, kid: str) -> dict[str, Any]:
    if not isinstance(public_key.curve, ec.SECP256R1):
        raise ValueError(
            f"JWKS publishes P-256 keys only; got {public_key.curve.name} for kid={kid!r}"
        )
    numbers = public_key.public_numbers()
    # Both coordinates are 32 bytes on P-256 — pad with leading zeros
    # if a small integer happens to be under the natural byte length.
    x_bytes = numbers.x.to_bytes(32, "big")
    y_bytes = numbers.y.to_bytes(32, "big")
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64url(x_bytes),
        "y": _b64url(y_bytes),
        "kid": kid,
        "alg": "ES256",
        "use": "sig",
    }


def _b64url(data: bytes) -> str:
    """Standard JWK base64url encoding — no padding, ``+/`` → ``-_``."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
