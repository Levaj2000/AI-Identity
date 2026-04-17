"""Forensic attestation signing helpers.

Keeps the signing layer (KMS RPC vs local PEM) separate from the
payload/envelope format (``common.schemas.forensic_attestation``) so
tests can drive the schema without a KMS dependency and production can
swap signer backends without touching format code.
"""

from common.forensic.signer import (
    ForensicSignerConfigError,
    SignerHandle,
    get_forensic_signer,
)

__all__ = [
    "ForensicSignerConfigError",
    "SignerHandle",
    "get_forensic_signer",
]
