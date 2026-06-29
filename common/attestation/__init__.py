"""Hardware attestation at agent registration (#423).

Optionally bind an agent's identity to a hardware root of trust (mTLS client
cert first; TPM/enclave reserved), verify it, and record it as an evidence-chain
event. See schemas.py and verify.py.
"""

from common.attestation.schemas import (
    AttestationResult,
    AttestationType,
    HardwareAttestation,
)
from common.attestation.verify import verify_attestation, verify_mtls_attestation

__all__ = [
    "AttestationResult",
    "AttestationType",
    "HardwareAttestation",
    "verify_attestation",
    "verify_mtls_attestation",
]
