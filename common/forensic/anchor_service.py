"""Evidence Anchor service — emit signed checkpoints, build inclusion proofs.

The DB-facing layer over the pure crypto in ``common.forensic.merkle`` and
``common.forensic.anchor_checkpoint`` (#408). Three responsibilities:

* :func:`create_checkpoint` — fold the next contiguous batch of an org's
  un-checkpointed ``audit_log`` rows into a Merkle tree, sign the root with
  the platform forensic signer, and persist an :class:`AuditCheckpoint`.
  Idempotent: returns ``None`` when there is nothing new to anchor.
* :func:`find_covering_checkpoint` / :func:`build_inclusion_proof` — resolve
  the checkpoint that commits a given audit row and produce its O(log N)
  proof.
* :func:`assemble_evidence` — gather the checkpoints + per-event proofs for a
  set of events, the shape the Case File bundle ships.

Signing reuses the same single platform key + JWKS as the per-session
attestation (``get_forensic_signer``); the ``org_id`` is carried inside the
signed checkpoint payload. Per-org asymmetric key isolation stays unbuilt by
decision (ADR-003, #407): forgery resistance already lives in the per-org HMAC
layer, the asymmetric key only provides public verifiability, and the
per-checkpoint ``signer_key_id`` keeps a future per-org-key path additive — so
verifiers and key rotation have one story, not two. See
``docs/ADR-003-evidence-anchor-key-directory.md`` for the trigger to revisit.
"""

from __future__ import annotations

import datetime
import uuid  # noqa: TC003 — annotation only, but cheap to keep at runtime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session  # noqa: TC002 — runtime-facing db handle annotation

from common.forensic import merkle
from common.forensic.anchor_checkpoint import build_checkpoint, sign_checkpoint
from common.forensic.signer import SignerHandle, get_forensic_signer
from common.models.audit_checkpoint import AuditCheckpoint
from common.models.audit_log import AuditLog

# Cap the batch a single checkpoint covers. Keeps the stored ``leaves`` array
# and the proof size bounded (proof is O(log N) — ~10 hashes at this cap), and
# bounds the work per worker tick. Larger backlogs are drained across ticks.
MAX_BATCH = 1000


def _last_anchored_id(db: Session, org_id: uuid.UUID) -> int:
    """Highest ``audit_log.id`` already covered by a checkpoint for this org."""
    return (
        db.execute(
            select(func.max(AuditCheckpoint.last_audit_id)).where(AuditCheckpoint.org_id == org_id)
        ).scalar()
        or 0
    )


def create_checkpoint(
    db: Session,
    org_id: uuid.UUID,
    *,
    signer: SignerHandle | None = None,
    max_batch: int = MAX_BATCH,
    now: datetime.datetime | None = None,
    after_id: int | None = None,
) -> AuditCheckpoint | None:
    """Anchor the next contiguous batch of un-checkpointed rows for ``org_id``.

    Returns the persisted :class:`AuditCheckpoint`, or ``None`` if the org has
    no rows beyond its last checkpoint (nothing to do — the worker no-ops).

    ``signer`` defaults to the configured platform signer; tests pass a
    local-key handle. ``now`` is injectable for deterministic tests.

    ``after_id`` lets a caller draining several contiguous batches for one org
    thread the previous checkpoint's ``last_audit_id`` forward, so the high-water
    mark is not re-derived with a ``SELECT max(...)`` every iteration (the N+1
    the per-tick drain loop in ``anchor_cron`` otherwise triggers). When ``None``
    the mark is read from the DB as before. The returned checkpoint's
    ``last_audit_id`` is the value to pass as ``after_id`` on the next call —
    correct on both the normal and the concurrent-winner path.
    """
    last_id = after_id if after_id is not None else _last_anchored_id(db, org_id)

    rows = db.execute(
        select(AuditLog.id, AuditLog.entry_hash)
        .where(AuditLog.org_id == org_id, AuditLog.id > last_id)
        .order_by(AuditLog.id.asc())
        .limit(max_batch)
    ).all()
    if not rows:
        return None

    audit_log_ids = [r.id for r in rows]
    leaves = [r.entry_hash for r in rows]

    signer = signer or get_forensic_signer()
    signed_at = now or datetime.datetime.now(tz=datetime.UTC)

    checkpoint, _tree = build_checkpoint(
        org_id=org_id,
        entry_hashes=leaves,
        first_audit_id=audit_log_ids[0],
        last_audit_id=audit_log_ids[-1],
        signer_key_id=signer.key_id,
        signed_at=signed_at,
    )
    envelope = sign_checkpoint(checkpoint, signer.sign)

    row = AuditCheckpoint(
        org_id=org_id,
        tree_size=checkpoint.tree_size,
        first_audit_id=checkpoint.first_audit_id,
        last_audit_id=checkpoint.last_audit_id,
        merkle_root=checkpoint.merkle_root,
        audit_log_ids=audit_log_ids,
        leaves=leaves,
        signer_key_id=signer.key_id,
        signed_at=signed_at,
        envelope=envelope.model_dump(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Another worker anchored this same starting row concurrently. The
        # unique (org_id, first_audit_id) guard fired; the winner's row is
        # equivalent, so roll back and hand it back.
        db.rollback()
        winner = db.execute(
            select(AuditCheckpoint).where(
                AuditCheckpoint.org_id == org_id,
                AuditCheckpoint.first_audit_id == audit_log_ids[0],
            )
        ).scalar_one_or_none()
        return winner
    db.refresh(row)
    return row


def find_covering_checkpoint(
    db: Session, org_id: uuid.UUID, audit_id: int
) -> AuditCheckpoint | None:
    """The checkpoint whose batch commits ``audit_id``, or ``None`` if not yet anchored."""
    return db.execute(
        select(AuditCheckpoint).where(
            AuditCheckpoint.org_id == org_id,
            AuditCheckpoint.first_audit_id <= audit_id,
            AuditCheckpoint.last_audit_id >= audit_id,
        )
    ).scalar_one_or_none()


def build_inclusion_proof(checkpoint: AuditCheckpoint, audit_id: int) -> dict | None:
    """O(log N) inclusion proof that ``audit_id`` is committed by ``checkpoint``.

    Returns a JSON-serializable dict (hex proof) that an offline verifier
    combines with the signed checkpoint envelope and the public key. Returns
    ``None`` if ``audit_id`` is not in this checkpoint's batch.
    """
    try:
        index = checkpoint.audit_log_ids.index(audit_id)
    except ValueError:
        return None
    tree = merkle.MerkleTree([bytes.fromhex(h) for h in checkpoint.leaves])
    proof = tree.inclusion_proof(index)
    return {
        "audit_id": audit_id,
        "entry_hash": checkpoint.leaves[index],
        "index": index,
        "tree_size": checkpoint.tree_size,
        "merkle_root": checkpoint.merkle_root,
        "proof": [node.hex() for node in proof],
    }


def assemble_evidence(db: Session, org_id: uuid.UUID, audit_ids: list[int]) -> dict:
    """Gather the checkpoints + per-event inclusion proofs for ``audit_ids``.

    The shape the Case File bundle ships. ``checkpoints`` is keyed by
    ``merkle_root`` (each appears once even when many events share it);
    ``proofs`` carries one entry per anchored event, referencing its
    checkpoint by root. Events not yet covered by a checkpoint are listed in
    ``pending`` so the bundle is honest about coverage rather than silently
    dropping them.
    """
    checkpoints: dict[str, dict] = {}
    proofs: list[dict] = []
    pending: list[int] = []

    for audit_id in audit_ids:
        cp = find_covering_checkpoint(db, org_id, audit_id)
        if cp is None:
            pending.append(audit_id)
            continue
        proof = build_inclusion_proof(cp, audit_id)
        if proof is None:  # pragma: no cover — covering query guarantees membership
            pending.append(audit_id)
            continue
        checkpoints.setdefault(cp.merkle_root, cp.envelope)
        proofs.append(proof)

    return {
        "checkpoints": [
            {"merkle_root": root, "envelope": env} for root, env in checkpoints.items()
        ],
        "proofs": proofs,
        "pending": pending,
    }
