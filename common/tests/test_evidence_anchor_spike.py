"""Evidence Anchor spike (#406) — de-risk the public-verifiability bet.

The question this spike answers: can a third party verify that one audit
entry is committed, using ONLY a published public key and SHA-256 — with
zero access to ``AUDIT_HMAC_KEY`` and zero ability to forge?

These tests prove yes by composing the new Merkle primitive with the
existing forensic DSSE/ECDSA-P256 signing stack. The headline test
(``test_third_party_verifies_with_only_public_key``) is the spike's exit
criterion.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import uuid

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.forensic import anchor_checkpoint as ac
from common.forensic import merkle
from common.schemas.forensic_attestation import (
    AttestationVerificationError,
    local_ecdsa_signer,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _fake_entry_hashes(n: int) -> list[str]:
    """n deterministic, distinct SHA-256 hex strings standing in for entry_hash."""
    return [hashlib.sha256(f"entry-{i}".encode()).hexdigest() for i in range(n)]


def _keypair() -> tuple[ec.EllipticCurvePrivateKey, bytes]:
    priv = ec.generate_private_key(ec.SECP256R1())
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv, pub_pem


# ---------------------------------------------------------------------------
# Merkle primitive — correctness across shapes (incl. non-power-of-two)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 8, 13, 17, 100])
def test_merkle_inclusion_roundtrip(n: int) -> None:
    leaves = [bytes.fromhex(h) for h in _fake_entry_hashes(n)]
    tree = merkle.MerkleTree(leaves)
    root = tree.root
    for i in range(n):
        proof = tree.inclusion_proof(i)
        assert merkle.verify_inclusion(leaves[i], i, n, proof, root) is True
        # O(log N) proof size (single-leaf tree has an empty proof).
        assert len(proof) <= max(1, n - 1).bit_length()


def test_merkle_rejects_tampered_leaf() -> None:
    leaves = [bytes.fromhex(h) for h in _fake_entry_hashes(8)]
    tree = merkle.MerkleTree(leaves)
    proof = tree.inclusion_proof(3)
    forged = hashlib.sha256(b"not-in-the-tree").digest()
    assert merkle.verify_inclusion(forged, 3, 8, proof, tree.root) is False


def test_merkle_rejects_wrong_index() -> None:
    leaves = [bytes.fromhex(h) for h in _fake_entry_hashes(8)]
    tree = merkle.MerkleTree(leaves)
    proof = tree.inclusion_proof(3)
    # Right leaf, wrong claimed position.
    assert merkle.verify_inclusion(leaves[3], 4, 8, proof, tree.root) is False


def test_merkle_rejects_out_of_range() -> None:
    leaves = [bytes.fromhex(h) for h in _fake_entry_hashes(4)]
    tree = merkle.MerkleTree(leaves)
    assert merkle.verify_inclusion(leaves[0], 4, 4, [], tree.root) is False


# ---------------------------------------------------------------------------
# Signed checkpoint — the headline de-risk test
# ---------------------------------------------------------------------------


def test_third_party_verifies_with_only_public_key() -> None:
    """A verifier holding ONLY the public key proves inclusion of one entry.

    No HMAC key, no database, no private key — exactly the position a
    court / auditor / counterparty is in with the published JWKS.
    """
    # --- producer side (holds the private key) ---
    priv, pub_pem = _keypair()
    entry_hashes = _fake_entry_hashes(50)
    org_id = uuid.uuid4()
    checkpoint, tree = ac.build_checkpoint(
        org_id=org_id,
        entry_hashes=entry_hashes,
        first_audit_id=1001,
        last_audit_id=1050,
        signer_key_id="local:test-key",
        signed_at=datetime.datetime(2026, 6, 22, 12, 0, 0),
    )
    envelope = ac.sign_checkpoint(checkpoint, local_ecdsa_signer(priv))

    # --- bundle handed to the third party: the entry, its index, an
    #     O(log N) proof, the signed checkpoint envelope, the public key ---
    target_index = 37
    target_entry = entry_hashes[target_index]
    proof = tree.inclusion_proof(target_index)

    # --- verifier side (public key only) ---
    verified = ac.verify_entry_inclusion(
        entry_hash=target_entry,
        index=target_index,
        envelope=envelope,
        proof=proof,
        public_key_pem=pub_pem,
    )
    assert verified.tree_size == 50
    assert verified.first_audit_id == 1001
    assert verified.last_audit_id == 1050
    assert verified.org_id == org_id


def test_checkpoint_signature_rejects_tampered_root() -> None:
    """Flipping the signed root invalidates the signature."""
    priv, pub_pem = _keypair()
    checkpoint, _ = ac.build_checkpoint(
        org_id=uuid.uuid4(),
        entry_hashes=_fake_entry_hashes(10),
        first_audit_id=1,
        last_audit_id=10,
        signer_key_id="local:test-key",
        signed_at=datetime.datetime(2026, 6, 22, 12, 0, 0),
    )
    envelope = ac.sign_checkpoint(checkpoint, local_ecdsa_signer(priv))

    # Re-encode the payload with a different root, keeping the old signature.
    tampered = checkpoint.model_copy(update={"merkle_root": "0" * 64})
    envelope.payload = base64.b64encode(ac.canonical_bytes(tampered)).decode("ascii")

    with pytest.raises(AttestationVerificationError, match="signature verification failed"):
        ac.verify_checkpoint(envelope, pub_pem)


def test_inclusion_rejects_entry_not_in_batch() -> None:
    """A validly-signed checkpoint still rejects an entry that isn't a leaf."""
    priv, pub_pem = _keypair()
    entry_hashes = _fake_entry_hashes(20)
    checkpoint, tree = ac.build_checkpoint(
        org_id=uuid.uuid4(),
        entry_hashes=entry_hashes,
        first_audit_id=1,
        last_audit_id=20,
        signer_key_id="local:test-key",
        signed_at=datetime.datetime(2026, 6, 22, 12, 0, 0),
    )
    envelope = ac.sign_checkpoint(checkpoint, local_ecdsa_signer(priv))
    outsider = hashlib.sha256(b"never-recorded").hexdigest()

    with pytest.raises(AttestationVerificationError, match="not included"):
        ac.verify_entry_inclusion(
            entry_hash=outsider,
            index=5,
            envelope=envelope,
            proof=tree.inclusion_proof(5),
            public_key_pem=pub_pem,
        )


def test_checkpoint_payload_type_is_domain_separated() -> None:
    """A checkpoint envelope is not interchangeable with a v1 attestation.

    The distinct payloadType + PAE length-prefix mean an attestation
    verifier rejects a checkpoint envelope outright, so a signature over
    one can never be replayed as the other.
    """
    from common.schemas import forensic_attestation as fa

    assert ac.CHECKPOINT_PAYLOAD_TYPE != fa.PAYLOAD_TYPE

    priv, pub_pem = _keypair()
    checkpoint, _ = ac.build_checkpoint(
        org_id=uuid.uuid4(),
        entry_hashes=_fake_entry_hashes(4),
        first_audit_id=1,
        last_audit_id=4,
        signer_key_id="local:test-key",
        signed_at=datetime.datetime(2026, 6, 22, 12, 0, 0),
    )
    envelope = ac.sign_checkpoint(checkpoint, local_ecdsa_signer(priv))

    with pytest.raises(fa.AttestationVerificationError, match="unexpected payloadType"):
        fa.verify_envelope(envelope, pub_pem)


def test_verify_path_never_imports_audit_hmac_key() -> None:
    """Structural guard: the verifier modules must not depend on the chain
    writer / HMAC secret. Independence is the entire premise of the Anchor.

    We parse the actual ``import`` statements (not prose) so the docstrings
    that *describe* the HMAC chain don't trip the check.
    """
    import ast

    import common.forensic.anchor_checkpoint as mod_ac
    import common.forensic.merkle as mod_m

    for mod in (mod_m, mod_ac):
        with open(mod.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert "common.audit.writer" not in imported
        assert not any("audit" in name and "writer" in name for name in imported)
