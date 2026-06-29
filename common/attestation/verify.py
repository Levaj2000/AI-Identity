"""Verify a hardware attestation presented at agent registration (#423).

First (and currently only) supported type: an mTLS client certificate. The
verifier extracts the attested workload identity (SPIFFE SAN URI if present,
else the subject DN) and the public-key fingerprint that binds the credential,
checks the validity window, and — when a trusted CA is configured — checks the
certificate chains to it via the certificate's own signature.

VERIFY ONLY. We never issue certificates here. liboqs-style honesty: when no
trust anchor is configured we still *record* the attestation (identity +
fingerprint) but mark ``verified=False`` with a reason, rather than claim a
trust we didn't establish.
"""

from __future__ import annotations

import datetime
import hashlib

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtensionOID, NameOID

from common.attestation.schemas import AttestationResult, AttestationType, HardwareAttestation


def _spki_sha256(cert: x509.Certificate) -> str:
    """SHA-256 of the certificate's SubjectPublicKeyInfo (DER) — the binding id."""
    spki = cert.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(spki).hexdigest()


def _spiffe_or_subject(cert: x509.Certificate) -> str | None:
    """Prefer a SPIFFE SAN URI (workload identity); fall back to the subject DN."""
    try:
        san = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        for uri in san.value.get_values_for_type(x509.UniformResourceIdentifier):
            if uri.startswith("spiffe://"):
                return uri
    except x509.ExtensionNotFound:
        pass
    try:
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if cn:
            return cert.subject.rfc4514_string()
    except Exception:
        pass
    return cert.subject.rfc4514_string() or None


def verify_mtls_attestation(
    evidence_pem: str,
    *,
    trusted_ca_pem: str | None = None,
    now: datetime.datetime | None = None,
) -> AttestationResult:
    """Verify an mTLS client certificate as a hardware attestation."""
    now = now or datetime.datetime.now(datetime.UTC)
    result = AttestationResult(
        attestation_type=AttestationType.mtls_cert,
        verified=False,
        reason="not evaluated",
    )

    try:
        cert = x509.load_pem_x509_certificate(evidence_pem.encode())
    except Exception as e:
        result.reason = f"could not parse certificate: {e}"
        return result

    # Extract identity binding regardless of trust outcome (so it's recorded).
    result.subject = _spiffe_or_subject(cert)
    result.issuer = cert.issuer.rfc4514_string() or None
    result.public_key_sha256 = _spki_sha256(cert)
    result.serial_number = format(cert.serial_number, "x")
    nb = cert.not_valid_before_utc
    na = cert.not_valid_after_utc
    result.not_before = nb.isoformat()
    result.not_after = na.isoformat()

    # Validity window.
    if not (nb <= now < na):
        result.reason = f"certificate outside validity window ({nb.isoformat()} … {na.isoformat()})"
        return result

    # Chain trust. With no configured CA we record but do not claim trust.
    if not trusted_ca_pem:
        result.reason = "recorded; not verified (no trusted CA configured for mTLS attestation)"
        return result

    try:
        ca_cert = x509.load_pem_x509_certificate(trusted_ca_pem.encode())
    except Exception as e:
        result.reason = f"configured trusted CA is unparseable: {e}"
        return result

    try:
        # Single-level issuance check: signature + name chaining + validity.
        cert.verify_directly_issued_by(ca_cert)
    except (ValueError, TypeError) as e:
        result.reason = f"certificate not issued by the trusted CA: {e}"
        return result
    except Exception as e:  # InvalidSignature and friends
        result.reason = f"certificate signature did not verify against the trusted CA: {e}"
        return result

    result.verified = True
    result.reason = "verified: within validity window and issued by the configured trusted CA"
    return result


def verify_attestation(
    attestation: HardwareAttestation,
    *,
    trusted_ca_pem: str | None = None,
    now: datetime.datetime | None = None,
) -> AttestationResult:
    """Dispatch by attestation type. Only mtls_cert is implemented."""
    if attestation.attestation_type == AttestationType.mtls_cert:
        return verify_mtls_attestation(attestation.evidence, trusted_ca_pem=trusted_ca_pem, now=now)
    # Reserved types: record the request honestly, but unimplemented.
    return AttestationResult(
        attestation_type=attestation.attestation_type,
        verified=False,
        reason=f"attestation type '{attestation.attestation_type}' not yet implemented (mtls_cert only)",
    )
