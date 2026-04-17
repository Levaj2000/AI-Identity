"""Forensic signer resolution — KMS in prod, local PEM in dev/test.

The ``common.schemas.forensic_attestation`` module is deliberately
signer-agnostic: it takes a ``Callable[[bytes], bytes]`` and doesn't
care where the signature comes from. This module is the other side of
that contract — it reads settings and returns a ready-to-call signer
callable plus the key identifier that goes into the envelope.

Two backends:

* **GCP KMS** (production) — ``forensic_signing_key_id`` is set to a
  full KMS key-version resource path. Every call makes an
  ``AsymmetricSign`` RPC. Key material never leaves KMS.
* **Local PEM** (dev + tests) — ``forensic_signing_key_pem`` is set to
  a PEM-encoded P-256 private key. Signing happens in-process. The
  ``signer_key_id`` for these envelopes uses a ``local:<sha256>``
  scheme so envelopes signed in dev cannot be confused for KMS-signed
  envelopes later.

Exactly one backend must be configured. Setting both is a startup
error (``ForensicSignerConfigError``) — we don't want a silent
fallback that could hide a misconfiguration in production.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.config.settings import Settings  # noqa: TC002 — runtime default arg annotation
from common.config.settings import settings as default_settings

if TYPE_CHECKING:
    from collections.abc import Callable

    _Signer = Callable[[bytes], bytes]

_KMS_KEY_ID_PREFIX = "projects/"
_LOCAL_KEY_ID_PREFIX = "local:"


class ForensicSignerConfigError(RuntimeError):
    """Raised at startup if the signer is misconfigured.

    The attestation endpoint catches this and returns 503 so the
    service can still run without signer config (e.g. the API serves
    other traffic while KMS creds are being rotated).
    """


@dataclass(frozen=True)
class SignerHandle:
    """A configured signer ready to be passed to ``sign_payload``.

    Keeping the callable and the key id together prevents the common
    bug of signing with one key and claiming another in the envelope.
    """

    sign: _Signer
    """Callable that takes the signing input bytes and returns a
    DER-encoded ECDSA-P256-SHA256 signature. Matches the contract of
    ``common.schemas.forensic_attestation.sign_payload``'s ``signer``
    parameter.
    """

    key_id: str
    """The identifier that goes into ``AttestationPayloadV1.signer_key_id``
    and the DSSE envelope's ``keyid``. For KMS, the full key-version
    resource path. For local, ``local:<sha256 of public key DER>``.
    """

    backend: str
    """``"kms"`` or ``"local"``. Used by the metrics layer to label
    sign latency by backend — KMS is a network call, local is CPU.
    """


def get_forensic_signer(
    settings_obj: Settings | None = None,
) -> SignerHandle:
    """Resolve a signer from application settings.

    Idempotent and cheap for the local-PEM case. For the KMS case we
    instantiate a ``KeyManagementServiceClient`` per call — the API
    router caches the handle at startup (see
    ``api/app/routers/attestations.py``) so we don't pay that cost per
    request.
    """
    s = settings_obj or default_settings

    has_kms = bool(s.forensic_signing_key_id)
    has_local = bool(s.forensic_signing_key_pem)

    if has_kms and has_local:
        raise ForensicSignerConfigError(
            "both FORENSIC_SIGNING_KEY_ID (KMS) and FORENSIC_SIGNING_KEY_PEM "
            "(local) are set; pick exactly one backend. Unset the one you're "
            "not using to avoid signing with the wrong key."
        )
    if not has_kms and not has_local:
        raise ForensicSignerConfigError(
            "no forensic signing key configured. Set FORENSIC_SIGNING_KEY_ID "
            "to a GCP KMS key-version resource path for production, or "
            "FORENSIC_SIGNING_KEY_PEM to a PEM-encoded P-256 private key "
            "for development."
        )

    if has_kms:
        return _build_kms_signer(s.forensic_signing_key_id)
    return _build_local_signer(s.forensic_signing_key_pem)


# ---------------------------------------------------------------------------
# KMS backend
# ---------------------------------------------------------------------------


def _build_kms_signer(key_id: str) -> SignerHandle:
    if not key_id.startswith(_KMS_KEY_ID_PREFIX) or "/cryptoKeyVersions/" not in key_id:
        raise ForensicSignerConfigError(
            f"FORENSIC_SIGNING_KEY_ID does not look like a KMS key-version "
            f"resource path (expected 'projects/.../cryptoKeyVersions/N'): {key_id!r}"
        )

    try:
        from google.cloud import kms_v1
    except ImportError as exc:  # pragma: no cover — covered by requirements.txt
        raise ForensicSignerConfigError(
            "google-cloud-kms is not installed; cannot use KMS signing backend. "
            "Install the package or switch to FORENSIC_SIGNING_KEY_PEM."
        ) from exc

    client = kms_v1.KeyManagementServiceClient()

    def _sign(message: bytes) -> bytes:
        # KMS with EC_SIGN_P256_SHA256 expects the already-hashed digest
        # OR the raw message — both work, but the digest path keeps the
        # request payload small and avoids sending 100 KB+ of signing
        # input over the wire for large audit ranges.
        digest = hashlib.sha256(message).digest()
        response = client.asymmetric_sign(
            request={
                "name": key_id,
                "digest": {"sha256": digest},
            },
        )
        return response.signature

    return SignerHandle(sign=_sign, key_id=key_id, backend="kms")


# ---------------------------------------------------------------------------
# Local-PEM backend
# ---------------------------------------------------------------------------


def _build_local_signer(pem: str) -> SignerHandle:
    try:
        private_key = serialization.load_pem_private_key(
            pem.encode("utf-8"),
            password=None,
        )
    except (ValueError, TypeError) as exc:
        raise ForensicSignerConfigError(
            f"FORENSIC_SIGNING_KEY_PEM could not be parsed as a PEM private key: {exc}"
        ) from exc

    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ForensicSignerConfigError(
            "FORENSIC_SIGNING_KEY_PEM must be an elliptic-curve private key "
            f"(got {type(private_key).__name__}); the attestation format requires ECDSA P-256."
        )
    if not isinstance(private_key.curve, ec.SECP256R1):
        raise ForensicSignerConfigError(
            "FORENSIC_SIGNING_KEY_PEM must be a P-256 (SECP256R1) key; "
            f"got {private_key.curve.name}."
        )

    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_id = _LOCAL_KEY_ID_PREFIX + hashlib.sha256(public_der).hexdigest()

    def _sign(message: bytes) -> bytes:
        return private_key.sign(message, ec.ECDSA(hashes.SHA256()))

    return SignerHandle(sign=_sign, key_id=key_id, backend="local")
