"""Evidence Anchor service tests (#408).

Proves the DB-backed path end-to-end: real audit_log rows → signed checkpoint
→ inclusion proof that a third party verifies offline with only the public
key. Mirrors the spike's guarantee, now over persisted rows.
"""

from __future__ import annotations

import hashlib

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.forensic import anchor_service
from common.forensic.anchor_checkpoint import verify_entry_inclusion
from common.forensic.signer import SignerHandle
from common.models.audit_log import AuditLog
from common.models.organization import Organization
from common.schemas.forensic_attestation import (
    AttestationVerificationError,
    DSSEEnvelope,
)


def _local_signer() -> tuple[SignerHandle, bytes]:
    priv = ec.generate_private_key(ec.SECP256R1())
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    def _sign(message: bytes) -> bytes:
        return priv.sign(message, ec.ECDSA(hashes.SHA256()))

    return SignerHandle(sign=_sign, key_id="local:anchor-test", backend="local"), pub_pem


@pytest.fixture
def org(db_session, test_user):
    o = Organization(name="Anchor Test Org", owner_id=test_user.id)
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    return o


def _add_rows(db, org_id, agent_id, n: int, *, prefix: str = "e") -> list[int]:
    """Insert n audit_log rows; return their ids in order."""
    ids = []
    for i in range(n):
        row = AuditLog(
            agent_id=agent_id,
            org_id=org_id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
            entry_hash=hashlib.sha256(f"{prefix}-{org_id}-{i}".encode()).hexdigest(),
            prev_hash="GENESIS" if i == 0 else "x" * 64,
        )
        db.add(row)
        db.flush()
        ids.append(row.id)
    db.commit()
    return ids


def test_create_checkpoint_covers_rows_then_noops(db_session, org, test_agent):
    ids = _add_rows(db_session, org.id, test_agent.id, 50)
    signer, _ = _local_signer()

    cp = anchor_service.create_checkpoint(db_session, org.id, signer=signer)
    assert cp is not None
    assert cp.tree_size == 50
    assert cp.first_audit_id == ids[0]
    assert cp.last_audit_id == ids[-1]
    assert cp.audit_log_ids == ids
    assert cp.signer_key_id == "local:anchor-test"

    # Nothing new to anchor → no-op.
    assert anchor_service.create_checkpoint(db_session, org.id, signer=signer) is None

    # New rows → a second, contiguous, non-overlapping checkpoint.
    more = _add_rows(db_session, org.id, test_agent.id, 10, prefix="f")
    cp2 = anchor_service.create_checkpoint(db_session, org.id, signer=signer)
    assert cp2 is not None
    assert cp2.tree_size == 10
    assert cp2.first_audit_id == more[0]
    assert cp2.first_audit_id == cp.last_audit_id + 1


def test_after_id_threads_drain_without_requerying_max(db_session, org, test_agent):
    """Threading ``after_id`` drains a backlog into contiguous, gapless batches.

    Mirrors the anchor_cron per-tick loop, which now passes the previous
    checkpoint's ``last_audit_id`` forward instead of re-deriving the high-water
    mark with a ``SELECT max(...)`` each batch (the N+1 on the endpoint).
    """
    ids = _add_rows(db_session, org.id, test_agent.id, 25)
    signer, _ = _local_signer()

    after_id = None
    covered: list[int] = []
    for _ in range(10):  # max_per_org guard, same as the cron
        cp = anchor_service.create_checkpoint(
            db_session, org.id, signer=signer, max_batch=10, after_id=after_id
        )
        if cp is None:
            break
        covered.extend(cp.audit_log_ids)
        after_id = cp.last_audit_id

    # Every row anchored exactly once, in order, with no gaps or overlaps.
    assert covered == ids


def test_inclusion_proof_verifies_offline_with_public_key(db_session, org, test_agent):
    ids = _add_rows(db_session, org.id, test_agent.id, 40)
    signer, pub_pem = _local_signer()
    anchor_service.create_checkpoint(db_session, org.id, signer=signer)

    target = ids[17]
    evidence = anchor_service.assemble_evidence(db_session, org.id, [target])
    assert evidence["pending"] == []
    assert len(evidence["checkpoints"]) == 1
    assert len(evidence["proofs"]) == 1

    proof = evidence["proofs"][0]
    envelope = DSSEEnvelope(**evidence["checkpoints"][0]["envelope"])

    # Third party: public key only, no DB, no HMAC secret.
    checkpoint = verify_entry_inclusion(
        entry_hash=proof["entry_hash"],
        index=proof["index"],
        envelope=envelope,
        proof=[bytes.fromhex(h) for h in proof["proof"]],
        public_key_pem=pub_pem,
    )
    assert checkpoint.org_id == org.id
    assert checkpoint.tree_size == 40


def test_tampered_entry_fails_verification(db_session, org, test_agent):
    ids = _add_rows(db_session, org.id, test_agent.id, 16)
    signer, pub_pem = _local_signer()
    anchor_service.create_checkpoint(db_session, org.id, signer=signer)

    proof = anchor_service.assemble_evidence(db_session, org.id, [ids[3]])["proofs"][0]
    cp = anchor_service.find_covering_checkpoint(db_session, org.id, ids[3])
    envelope = DSSEEnvelope(**cp.envelope)
    forged = hashlib.sha256(b"after-the-fact edit").hexdigest()

    with pytest.raises(AttestationVerificationError, match="not included"):
        verify_entry_inclusion(
            entry_hash=forged,
            index=proof["index"],
            envelope=envelope,
            proof=[bytes.fromhex(h) for h in proof["proof"]],
            public_key_pem=pub_pem,
        )


def test_assemble_evidence_reports_uncovered_events(db_session, org, test_agent):
    ids = _add_rows(db_session, org.id, test_agent.id, 5)
    signer, _ = _local_signer()
    anchor_service.create_checkpoint(db_session, org.id, signer=signer)
    # Two more rows arrive after the checkpoint — not yet anchored.
    later = _add_rows(db_session, org.id, test_agent.id, 2, prefix="late")

    evidence = anchor_service.assemble_evidence(db_session, org.id, ids + later)
    assert set(evidence["pending"]) == set(later)
    assert len(evidence["proofs"]) == len(ids)


def test_checkpoints_are_org_scoped(db_session, org, test_agent, test_user):
    other = Organization(name="Other Org", owner_id=test_user.id)
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    _add_rows(db_session, org.id, test_agent.id, 8)
    _add_rows(db_session, other.id, test_agent.id, 3, prefix="other")
    signer, _ = _local_signer()

    cp = anchor_service.create_checkpoint(db_session, org.id, signer=signer)
    assert cp.tree_size == 8  # only this org's rows
    cp_other = anchor_service.create_checkpoint(db_session, other.id, signer=signer)
    assert cp_other.tree_size == 3
