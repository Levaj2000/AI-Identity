"""AuditCheckpoint — a signed Merkle checkpoint over a batch of audit rows.

The Evidence Anchor (#408, built on the spike in ``common/forensic/merkle.py``
+ ``anchor_checkpoint.py``). Periodically a worker folds a contiguous batch of
an org's ``audit_log`` rows into a Merkle tree and signs the root once with the
platform forensic key (ECDSA P-256, same signer + JWKS as the per-session
attestation in :mod:`common.models.attestation`). A single signature then
covers the whole batch, and any one event's inclusion can be proven in
O(log N) against the signed root using only the *public* key — no
``AUDIT_HMAC_KEY``.

This mirrors :class:`~common.models.attestation.ForensicAttestation`:

* ``envelope`` (the signed DSSE checkpoint) is the authoritative artifact —
  the other columns mirror fields from inside it for indexing.
* ``audit_log_ids`` + ``leaves`` are the frozen, ordered batch captured at
  sign time, so a checkpoint stays verifiable (and proofs stay buildable)
  even if the underlying ``audit_log`` rows are later pruned by retention.

Batches are contiguous and non-overlapping per org: each checkpoint covers
``audit_log`` rows with ``id`` in ``[first_audit_id, last_audit_id]``, and the
next checkpoint picks up after ``last_audit_id``. So every checkpointed row
belongs to exactly one checkpoint, and "find the checkpoint covering row N" is
an indexed range scan.
"""

from __future__ import annotations

import datetime  # noqa: TC003 — used by SQLAlchemy at mapper-config time
import uuid

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class AuditCheckpoint(Base):
    """One signed Merkle checkpoint over a contiguous batch of an org's audit rows."""

    __tablename__ = "audit_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Business key --------------------------------------------------------
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Frozen scope — mirrors the envelope for indexed "covering" lookups.
    tree_size: Mapped[int] = mapped_column(Integer, nullable=False)
    first_audit_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_audit_id: Mapped[int] = mapped_column(Integer, nullable=False)
    merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)

    # The frozen, ordered batch captured at sign time. ``audit_log_ids`` maps
    # an event to its leaf index; ``leaves`` is the ordered list of entry_hash
    # values that were hashed into the tree. Both are purge-resilient — a
    # proof can be rebuilt from ``leaves`` alone even if the rows are pruned.
    # On Postgres these are native ARRAYs; SQLite tests fall back to JSON.
    audit_log_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer).with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    leaves: Mapped[list[str]] = mapped_column(
        ARRAY(String).with_variant(JSON(), "sqlite"),
        nullable=False,
    )

    # Signature metadata --------------------------------------------------
    signer_key_id: Mapped[str] = mapped_column(String(512), nullable=False)
    signed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # The authoritative artifact — the full signed DSSE checkpoint envelope.
    envelope: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # Contiguous, non-overlapping batches: one checkpoint per
        # (org, first row). Re-running the worker over an already-covered
        # range is a no-op rather than a conflicting second checkpoint.
        UniqueConstraint("org_id", "first_audit_id", name="uq_checkpoint_org_first"),
        # "find the checkpoint covering audit row N" — indexed range scan.
        Index(
            "ix_audit_checkpoint_range",
            "org_id",
            "first_audit_id",
            "last_audit_id",
        ),
        Index("ix_audit_checkpoint_created", "org_id", "created_at"),
    )
