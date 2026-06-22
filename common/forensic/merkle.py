"""Merkle tree + offline inclusion proofs for the Evidence Anchor.

The audit log is an HMAC-SHA256 hash chain (see ``common/audit/writer.py``):
``entry_hash = HMAC-SHA256(canonical_payload || prev_hash, key=AUDIT_HMAC_KEY)``.
Proving that a single event is committed requires re-walking the chain
from a trusted tip *and* holding the org's HMAC key — that is O(N) and
**secret-dependent**. It makes truly independent verification impossible:
the only party who can verify is one you have also handed forging power.

This module adds the missing primitive: a Merkle tree over a batch of
audit ``entry_hash`` values. Paired with a signed root (see
``anchor_checkpoint.py``), a third party can prove ONE entry is included
in O(log N) using nothing but SHA-256 and the *public* signing key — zero
access to ``AUDIT_HMAC_KEY``, zero ability to forge.

Hashing follows RFC 6962 (Certificate Transparency) domain separation:

    leaf_hash(d)    = SHA-256(0x00 || d)
    node_hash(l, r) = SHA-256(0x01 || l || r)

The 0x00 / 0x01 prefixes stop a second-preimage attack that presents an
internal node as a leaf (or vice versa). This is a deliberately boring,
spec-faithful implementation — clarity over cleverness for a primitive
that has to be re-implementable by an outside verifier.
"""

from __future__ import annotations

import hashlib
import hmac

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"


def leaf_hash(data: bytes) -> bytes:
    """RFC 6962 leaf hash: SHA-256(0x00 || data)."""
    return hashlib.sha256(LEAF_PREFIX + data).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    """RFC 6962 interior node hash: SHA-256(0x01 || left || right)."""
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def _largest_power_of_two_less_than(n: int) -> int:
    """Largest power of two strictly less than ``n`` (requires n >= 2).

    RFC 6962 splits a subtree of size n at this boundary so that the
    left subtree is a complete binary tree.
    """
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def _root(hashes: list[bytes]) -> bytes:
    """Merkle Tree Hash (MTH) over a list of already-leaf-hashed values."""
    n = len(hashes)
    if n == 0:
        raise ValueError("merkle root requires at least one leaf")
    if n == 1:
        return hashes[0]
    k = _largest_power_of_two_less_than(n)
    return _node_hash(_root(hashes[:k]), _root(hashes[k:]))


def _proof(hashes: list[bytes], index: int) -> list[bytes]:
    """RFC 6962 audit path for ``index`` over already-leaf-hashed values."""
    n = len(hashes)
    if not 0 <= index < n:
        raise IndexError(f"index {index} out of range for tree of size {n}")
    if n == 1:
        return []
    k = _largest_power_of_two_less_than(n)
    if index < k:
        return _proof(hashes[:k], index) + [_root(hashes[k:])]
    return _proof(hashes[k:], index - k) + [_root(hashes[:k])]


class MerkleTree:
    """A Merkle tree over a batch of leaf *data* values.

    Leaf data is the raw bytes of an audit ``entry_hash`` (32 bytes,
    decoded from its hex form). The tree leaf-hashes each value on
    construction, so ``root`` and ``inclusion_proof`` operate on the
    domain-separated leaves.
    """

    def __init__(self, leaves: list[bytes]) -> None:
        if not leaves:
            raise ValueError("MerkleTree requires at least one leaf")
        self._leaves = [leaf_hash(d) for d in leaves]

    @property
    def size(self) -> int:
        return len(self._leaves)

    @property
    def root(self) -> bytes:
        return _root(self._leaves)

    def inclusion_proof(self, index: int) -> list[bytes]:
        """Audit path proving the leaf at ``index`` is committed to the root."""
        return _proof(self._leaves, index)


def verify_inclusion(
    leaf_data: bytes,
    index: int,
    tree_size: int,
    proof: list[bytes],
    root: bytes,
) -> bool:
    """Offline RFC 6962 inclusion-proof check. O(log N), no secret, no DB.

    Returns True iff ``leaf_data`` is the leaf at position ``index`` in a
    tree of ``tree_size`` leaves whose Merkle root is ``root``. This is the
    function an outside verifier runs — it depends only on SHA-256.

    Implements the verification algorithm from RFC 6962 §2.1.1 verbatim.
    """
    if tree_size <= 0 or not 0 <= index < tree_size:
        return False

    fn = index
    sn = tree_size - 1
    r = leaf_hash(leaf_data)

    for p in proof:
        if sn == 0:
            # Path longer than the tree height — malformed proof.
            return False
        if (fn & 1) or fn == sn:
            r = _node_hash(p, r)
            if not (fn & 1):
                # We were forced to be a right child because fn == sn;
                # shift down until we sit on a left edge again.
                while True:
                    fn >>= 1
                    sn >>= 1
                    if (fn & 1) or fn == 0:
                        break
        else:
            r = _node_hash(r, p)
        fn >>= 1
        sn >>= 1

    return sn == 0 and hmac.compare_digest(r, root)
