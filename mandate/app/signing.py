"""Mandate signing and canonical payload construction.

Signing flow:
  1. Build a signable dict from the mandate (all fields except signatures/updated_at/_id).
  2. Canonicalize via RFC 8785 (JSON Canonicalization Scheme).
  3. Sign the canonical bytes — GCP KMS (ECDSA P-256) in production,
     local PEM key in development.
  4. Return a MandateSignature with base64url-encoded signature.

Crypto agility: the signable payload includes schema_version so future
algorithm upgrades can be detected by the verifier. The ML-DSA-87 (PQC)
verify path is wired below via liboqs (Open Quantum Safe) — VERIFY ONLY,
no PQC issuance yet. A deployment opts in by configuring a single trusted
ML-DSA public key (settings.forensic_mldsa_public_key); when unset, the
slot stays inert and verify_signature returns None for ml-dsa-87.
"""

import asyncio
import base64
import hashlib
import logging

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    Prehashed,
    decode_dss_signature,
    encode_dss_signature,
)

from common.config.settings import settings
from mandate.app.schemas import MandateDocument, MandateSignature, SignatureAlgorithm

logger = logging.getLogger("ai_identity.mandate.signing")

# liboqs mechanism name for the reserved PQC slot. ML-DSA-87 == FIPS 204
# Level-5 (Dilithium5). Public key is 2592 bytes; signature is 4627 bytes.
_MLDSA_ALG = "ML-DSA-87"
_MLDSA_PUBKEY_LEN = 2592

# Cache of KMS key_id -> EC public key. Populated on first verify call per key.
# A single mandate service trusts a single signing key (settings.forensic_signing_key_id),
# but other key_ids may appear on legitimate mandates after key rotation, so we
# key the cache by resource path rather than a single global.
_kms_pubkey_cache: dict[str, ec.EllipticCurvePublicKey] = {}
_kms_pubkey_lock = asyncio.Lock()


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


def _b64url_decode(s: str) -> bytes:
    """Decode unpadded base64url (the format _b64url emits)."""
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _trusted_mldsa_pubkey() -> bytes | None:
    """Return the deployment's single trusted ML-DSA-87 public key, or None.

    Source is settings.forensic_mldsa_public_key (base64 of the raw 2592-byte
    public key). Returns None when unset or malformed — callers treat that as
    "this deployment cannot verify PQC signatures" rather than a hard failure,
    keeping the reserved slot inert until an operator opts in.
    """
    raw = settings.forensic_mldsa_public_key
    if not raw:
        return None
    try:
        # Accept standard or url-safe base64, padded or not.
        pub = base64.b64decode(raw + "=" * (-len(raw) % 4), altchars=b"-_")
    except Exception:
        logger.warning("forensic_mldsa_public_key is not valid base64; ignoring")
        return None
    if len(pub) != _MLDSA_PUBKEY_LEN:
        logger.warning(
            "forensic_mldsa_public_key is %d bytes, expected %d; ignoring",
            len(pub),
            _MLDSA_PUBKEY_LEN,
        )
        return None
    return pub


def _mldsa_key_id(pub_bytes: bytes) -> str:
    """Derive the trust key_id for an ML-DSA public key.

    Mirrors the local-ECDSA scheme: a stable fingerprint of the public key.
    A future PQC signer derives the same id from the same public key.
    """
    return f"mldsa-local:{hashlib.sha256(pub_bytes).hexdigest()[:16]}"


def _verify_mldsa(payload: bytes, signature: bytes, pub_bytes: bytes) -> bool:
    """Cryptographically verify an ML-DSA-87 signature over payload.

    liboqs is imported lazily so the module loads in environments where the
    native library isn't installed (only the PQC verify path needs it).
    Unlike the ECDSA path, ML-DSA signs the message directly — no prehash.
    """
    import oqs

    with oqs.Signature(_MLDSA_ALG) as verifier:
        return bool(verifier.verify(payload, signature, pub_bytes))


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
    der_sig = private_key.sign(digest, ec.ECDSA(Prehashed(hashes.SHA256())))
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


async def _get_kms_public_key(key_id: str) -> ec.EllipticCurvePublicKey:
    """Fetch the EC public key for a KMS key-version resource path, cached.

    KMS returns the public key as PEM; we parse once and cache. The cache is
    process-local — a restart re-fetches, which is fine (KMS pubkeys rarely change).
    """
    if key_id in _kms_pubkey_cache:
        return _kms_pubkey_cache[key_id]

    async with _kms_pubkey_lock:
        if key_id in _kms_pubkey_cache:
            return _kms_pubkey_cache[key_id]

        from google.cloud import kms

        client = kms.KeyManagementServiceAsyncClient()
        response = await client.get_public_key(request={"name": key_id})
        public_key = serialization.load_pem_public_key(response.pem.encode())
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            raise RuntimeError(
                f"KMS key {key_id} did not return an EC public key (got {type(public_key).__name__})"
            )
        _kms_pubkey_cache[key_id] = public_key
        return public_key


def _is_trusted_key_id(key_id: str) -> bool:
    """Allowlist: only verify signatures from keys this deployment trusts.

    Without this, an attacker could sign a forged mandate with their own KMS key,
    embed the resource path, and our verifier would fetch the pubkey and
    "successfully" verify it. The signature would be valid but the issuer untrusted.

    For now we trust exactly one key: the one this service is configured to sign with.
    Future: extend to a cross-org trust list when we federate.
    """
    if key_id.startswith("mldsa-local:"):
        # PQC trust: fingerprint must match the configured ML-DSA public key.
        pub = _trusted_mldsa_pubkey()
        if pub is None:
            return False
        return key_id == _mldsa_key_id(pub)

    if key_id.startswith("local:"):
        # Local-mode trust: fingerprint must match the configured PEM
        pem = settings.forensic_signing_key_pem
        if not pem:
            return False
        try:
            private_key = serialization.load_pem_private_key(pem.encode(), password=None)
        except Exception:
            return False
        if not isinstance(private_key, ec.EllipticCurvePrivateKey):
            return False
        pub_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.CompressedPoint,
        )
        expected = f"local:{hashlib.sha256(pub_bytes).hexdigest()[:16]}"
        return key_id == expected

    # KMS-mode trust: must match the configured signing key resource path
    return bool(settings.forensic_signing_key_id) and key_id == settings.forensic_signing_key_id


async def verify_signature(mandate: MandateDocument, sig: MandateSignature) -> bool | None:
    """Verify one signature entry against the mandate's canonical payload.

    Returns:
        True  — signature is valid and trusted
        False — signature is invalid OR key is not trusted by this verifier
        None  — algorithm is not verifiable by this deployment (the ml-dsa-87
                verifier is wired, but no trusted PQC key is configured here).
                The route uses this to require at least one verifiable signature
                without failing hybrid mandates that carry a future-algo slot
                alongside a classical one.
    """
    if sig.algorithm == SignatureAlgorithm.ml_dsa_87:
        pub = _trusted_mldsa_pubkey()
        if pub is None:
            # No PQC trust key configured: the slot is reserved but inert here.
            # Returning None (not False) keeps hybrid mandates verifiable via
            # their classical signature on deployments without a PQC key.
            logger.debug("ml-dsa-87 signature present but no trusted PQC key configured")
            return None

        if not _is_trusted_key_id(sig.key_id):
            logger.warning("ml-dsa-87 signature uses untrusted key_id: %s", sig.key_id)
            return False

        payload = _build_signable_payload(mandate)
        try:
            sig_bytes = _b64url_decode(sig.signature)
            return _verify_mldsa(payload, sig_bytes, pub)
        except Exception as e:
            logger.warning("ml-dsa-87 verification error: %s", e)
            return False

    if not _is_trusted_key_id(sig.key_id):
        logger.warning("Signature uses untrusted key_id: %s", sig.key_id)
        return False

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
            private_key = serialization.load_pem_private_key(pem.encode(), password=None)
            public_key = private_key.public_key()
        else:
            public_key = await _get_kms_public_key(sig.key_id)

        public_key.verify(der_sig, digest, ec.ECDSA(Prehashed(hashes.SHA256())))
        return True
    except InvalidSignature:
        logger.warning("Signature failed cryptographic verification for %s", sig.key_id)
        return False
    except Exception as e:
        logger.warning("Signature verification error: %s", e)
        return False
