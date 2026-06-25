"""Generate a cross-implementation test vector for the in-browser inclusion verifier.

Uses the REAL forensic code path (build_checkpoint / sign_checkpoint / Merkle proof
/ JWK export) so the JS verifier is validated against Python, not against itself.
Run from repo root:  python dashboard/scripts/gen_anchor_fixture.py
Emits JSON to stdout — paste into dashboard/src/lib/__tests__/fixtures/anchor-vector.json
"""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from common.forensic.anchor_checkpoint import build_checkpoint, sign_checkpoint
from common.forensic.jwks import _ec_public_key_to_jwk

# Deterministic-ish inputs (signature itself is randomized, but that's fine —
# the vector captures one signature that must verify).
ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
N = 7  # odd count exercises the RFC 6962 right-edge promotion path
entry_hashes = [hashlib.sha256(f"event-{i}".encode()).hexdigest() for i in range(N)]

priv = ec.generate_private_key(ec.SECP256R1())
KID = "local:fixture-key"


def _sign(message: bytes) -> bytes:
    return priv.sign(message, ec.ECDSA(hashes.SHA256()))


signed_at = datetime.datetime(2026, 6, 25, 12, 0, 0, tzinfo=datetime.UTC)
checkpoint, tree = build_checkpoint(
    org_id=ORG_ID,
    entry_hashes=entry_hashes,
    first_audit_id=1000,
    last_audit_id=1000 + N - 1,
    signer_key_id=KID,
    signed_at=signed_at,
)
envelope = sign_checkpoint(checkpoint, _sign)

# Prove inclusion of a middle leaf (index 3) — exercises both left/right combines.
TARGET_INDEX = 3
proof_nodes = tree.inclusion_proof(TARGET_INDEX)

jwk = _ec_public_key_to_jwk(priv.public_key(), kid=KID)

vector = {
    "checkpoints": [{"merkle_root": checkpoint.merkle_root, "envelope": envelope.model_dump()}],
    "inclusionProofs": {
        "proofs": [
            {
                "audit_id": 1000 + TARGET_INDEX,
                "entry_hash": entry_hashes[TARGET_INDEX],
                "index": TARGET_INDEX,
                "tree_size": N,
                "merkle_root": checkpoint.merkle_root,
                "proof": [node.hex() for node in proof_nodes],
            }
        ],
        "pending": [],
    },
    "jwks": {"keys": [jwk]},
}
print(json.dumps(vector, indent=2))
