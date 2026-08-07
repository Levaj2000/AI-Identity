"""Signed draw receipts — evidence flowing back up the delegation chain.

The Biscuit carries authority downstream (a parent narrows a token and
hands it to a delegate); the receipt carries evidence back upstream (the
trusted enforcement point hands the presenter a signed record of what was
done — or refused — with that authority). The delegator ends up holding
offline-verifiable proof of its delegate's actions without anyone
instrumenting the delegate's runtime.

Trust anchor symmetry: receipts are signed with the SAME Ed25519 root key
that anchors the Biscuit tokens (settings.biscuit_root_key_pem), so a
party that can verify the token can verify the receipt — one published
key, both directions.

The receipt is not the ledger. The chained audit log stays authoritative;
the receipt's ``correlation_id`` ties it to the chain rows for that exact
request, so a receipt-in-hand can always be reconciled against the
tamper-evident record if disputed. ``revocation_id`` identifies WHICH
copy of the authority acted — a parent's receipt provably concerns its
delegate's attenuated token, not some other holder.

Payload is canonicalized with RFC 8785 (JCS) before signing, matching the
mandate signer's convention.
"""

from __future__ import annotations

import base64
import datetime as dt

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

RECEIPT_ALGORITHM = "ed25519-jcs"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def mint_receipt(private_key_pem: str, payload: dict) -> dict:
    """Sign a receipt payload with the Biscuit root key.

    ``issued_at`` is stamped here so the signature always covers it.
    Raises ValueError if the PEM is missing or not an Ed25519 key.
    """
    if not private_key_pem.strip():
        raise ValueError("no Biscuit root key configured — cannot mint receipts")
    key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Biscuit root key must be an Ed25519 private key")

    body = dict(payload)
    body["issued_at"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    signature = key.sign(rfc8785.dumps(body))
    public_hex = (
        key.public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        .hex()
    )
    return {
        "receipt": body,
        "algorithm": RECEIPT_ALGORITHM,
        "public_key": public_hex,
        "signature": _b64url(signature),
    }


def verify_receipt(bundle: dict, trusted_public_key_hex: str) -> bool:
    """Verify a receipt offline against the published root public key.

    False on any mismatch: wrong algorithm, a public_key field that isn't
    the trusted key (a forger can't just swap in their own), bad
    signature, or tampered payload bytes.
    """
    try:
        if bundle.get("algorithm") != RECEIPT_ALGORITHM:
            return False
        if bundle.get("public_key") != trusted_public_key_hex:
            return False
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(trusted_public_key_hex))
        public_key.verify(
            _b64url_decode(bundle["signature"]),
            rfc8785.dumps(bundle["receipt"]),
        )
        return True
    except (InvalidSignature, KeyError, TypeError, ValueError):
        return False
