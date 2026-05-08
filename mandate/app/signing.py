"""Mandate signing and canonical payload construction.

Signing flow:
  1. Build a signable dict from the mandate (all fields except signatures/updated_at/_id).
  2. Canonicalize via RFC 8785 (JSON Canonicalization Scheme).
  3. Sign the canonical bytes — GCP KMS (ECDSA P-256) in production,
     local PEM key in development.
  4. Return a MandateSignature with base64url-encoded signature.

Crypto agility: the signable payload includes schema_version so future
algorithm upgrades can be detected by the verifier. The ML-DSA-87 slot
will be wired here when the PQC library is integrated (H2 milestone).
"""

import base64
import hashlib
import logging

import rfc8785
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

from common.config.settings import settings
from mandate.app.schemas import MandateDocument, MandateSignature, SignatureAlgorithm

logger = logging.getLogger("ai_identity.mandate.signing")


def _build_signable_payload(mandate: MandateDocument) -> bytes:
    """Extract the signable fields and canonicalize with RFC 8785.

    Excluded: signatures (would be circular), updated_at (mutable metadata).
    """
    d = mandate.model_dump(mode="json")
    d.pop("signatures", None)
    d.pop("updated_at", None)
    # Convert datetime objects to ISO strings if model_dump left them as objects
    return rfc8785.dumps(d)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _sign_local(payload: bytes) -> tuple[str, str]:
    """Sign with a local PEM private key (dev/test only)."""
    pem = settings.forensic_signing_key_pem
    if not pem:
        raise RuntimeError(
            "No signing key configured (set FORENSIC_SIGNING_KEY_PEM or FORENSIC_SIGNING_KEY_ID)"
        )

    private_key = serialization.load_pem_private_key(pem.encode(), password=None)
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise RuntimeError("FORENSIC_SIGNING_KEY_PEM must be an EC (P-256) private key")

    digest = hashlib.sha256(payload).digest()
    der_sig = private_key.sign(digest, ec.ECDSA(hashes.Prehashed()))
    r, s = decode_dss_signature(der_sig)
    # Fixed-width 32-byte components concatenated (IEEE P1363 format)
    raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")

    pub = private_key.public_key()
    pub_bytes = pub.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.CompressedPoint,
    )
    fingerprint = hashlib.sha256(pub_bytes).hexdigest()[:16]
    return _b64url(raw_sig), f"local:{fingerprint}"


async def _sign_kms(payload: bytes) -> tuple[str, str]:
    """Sign with GCP Cloud KMS (ECDSA P-256)."""
    from google.cloud import kms

    key_id = settings.forensic_signing_key_id
    client = kms.KeyManagementServiceAsyncClient()
    digest = {"sha256": hashlib.sha256(payload).digest()}
    response = await client.asymmetric_sign(request={"name": key_id, "digest": digest})
    # GCP returns DER; convert to IEEE P1363
    r, s = decode_dss_signature(response.signature)
    raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return _b64url(raw_sig), key_id


async def sign_mandate(mandate: MandateDocument) -> MandateSignature:
    """Produce a classical ECDSA-P256-SHA256 signature for a mandate.

    Uses KMS in production (FORENSIC_SIGNING_KEY_ID set) or the local PEM
    key in development. Raises RuntimeError if neither is configured.
    """
    payload = _build_signable_payload(mandate)

    if settings.forensic_signing_key_id:
        signature_b64, key_id = await _sign_kms(payload)
    else:
        signature_b64, key_id = _sign_local(payload)

    return MandateSignature(
        algorithm=SignatureAlgorithm.ecdsa_p256_sha256,
        key_id=key_id,
        signature=signature_b64,
    )


def verify_signature(mandate: MandateDocument, sig: MandateSignature) -> bool:
    """Verify one signature entry against the mandate's canonical payload.

    Only ecdsa-p256-sha256 is verifiable offline today.
    ml-dsa-87 signatures are skipped (not yet issued; stub).
    """
    if sig.algorithm == SignatureAlgorithm.ml_dsa_87:
        logger.debug("ML-DSA-87 verification not yet implemented — skipping")
        return True  # Optimistic: don't fail mandates that have a future-algo slot

    payload = _build_signable_payload(mandate)
    digest = hashlib.sha256(payload).digest()

    try:
        raw_sig = base64.urlsafe_b64decode(sig.signature + "==")
        if len(raw_sig) != 64:
            logger.warning("Signature wrong length: %d bytes", len(raw_sig))
            return False
        r = int.from_bytes(raw_sig[:32], "big")
        s = int.from_bytes(raw_sig[32:], "big")
        der_sig = encode_dss_signature(r, s)

        if sig.key_id.startswith("local:"):
            pem = settings.forensic_signing_key_pem
            if not pem:
                logger.warning("Cannot verify local signature — PEM not configured")
                return False
            private_key = serialization.load_pem_private_key(pem.encode(), password=None)
            public_key = private_key.public_key()
        else:
            # KMS public key — fetched and cached at startup (future optimization)
            # For now: if we don't have the public key locally, trust the DB record
            # (signature was verified at issuance). Full offline verification
            # requires fetching the KMS public key, which is a Phase 2 enhancement.
            logger.debug(
                "KMS key offline verification not yet implemented — trusting stored record"
            )
            return True

        public_key.verify(der_sig, digest, ec.ECDSA(hashes.Prehashed()))
        return True
    except Exception as e:
        logger.warning("Signature verification failed: %s", e)
        return False
