"""Schemas for hardware attestation at agent registration (#423).

At registration an agent may *optionally* present a hardware attestation that
binds its identity to a hardware root of trust. We verify it, bind the attested
public key to the agent, and record it as an evidence-chain event. The first
supported type is an **mTLS client certificate**; TPM quote / secure-enclave
attestation are reserved for later.

This mirrors the OCSF workload-attestation object proposed in the gap list
(Issue 5: ``attestation_type`` / ``attestation_evidence`` / ``verified`` +
workload-identity binding) — so AI Identity is the running-code reference for
the gap it's asking the WG to add. Per the Issue 5 precision trap, workload
attestation (*is the environment/credential trustworthy?*) is kept distinct
from record integrity (the audit hash chain) — they are separate signals.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AttestationType(StrEnum):
    """Kinds of hardware attestation. Only ``mtls_cert`` is implemented."""

    mtls_cert = "mtls_cert"  # X.509 client certificate (implemented)
    tpm_quote = "tpm_quote"  # reserved — not yet implemented
    enclave = "enclave"  # reserved — secure-enclave quote, not yet implemented


class HardwareAttestation(BaseModel):
    """An attestation presented at registration (input)."""

    attestation_type: AttestationType = Field(
        description="Kind of attestation evidence. Currently only 'mtls_cert'.",
    )
    evidence: str = Field(
        ...,
        max_length=64_000,
        description=(
            "The attestation evidence. For 'mtls_cert', a PEM-encoded X.509 client certificate."
        ),
    )


class AttestationResult(BaseModel):
    """Outcome of verifying a hardware attestation (output / record).

    ``verified`` is True only when the evidence cryptographically checks out
    *and* is trusted by this deployment (e.g. an mTLS cert that chains to the
    configured trusted CA and is within its validity window). When no trust
    anchor is configured the attestation is still recorded with the extracted
    identity, but ``verified`` is False and ``reason`` says why — no overclaim.
    """

    attestation_type: AttestationType
    verified: bool = Field(description="True only if cryptographically verified AND trusted.")
    reason: str = Field(description="Human-readable why verified / why not.")
    # --- workload-identity binding (what was attested) ---
    subject: str | None = Field(
        default=None,
        description="Attested workload identity (SPIFFE URI if present, else cert subject DN).",
    )
    issuer: str | None = Field(default=None, description="Certificate issuer DN.")
    public_key_sha256: str | None = Field(
        default=None,
        description="SHA-256 of the attested public key (SPKI DER) — the binding fingerprint.",
    )
    serial_number: str | None = Field(default=None, description="Certificate serial (hex).")
    not_before: str | None = Field(default=None, description="Validity start (RFC 3339).")
    not_after: str | None = Field(default=None, description="Validity end (RFC 3339).")

    def audit_scalars(self) -> dict[str, str | bool]:
        """Flat, allowlist-safe fields for the audit chain (no nested dicts).

        The full result is denormalized onto the agent; the audit entry carries
        only these scalars (see common/audit/sanitizer.py allowlist).
        """
        out: dict[str, str | bool] = {
            "attestation_type": str(self.attestation_type),
            "attestation_verified": self.verified,
        }
        if self.subject:
            out["attestation_subject"] = self.subject
        if self.public_key_sha256:
            out["attestation_pubkey_sha256"] = self.public_key_sha256
        return out
