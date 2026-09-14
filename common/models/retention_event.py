"""RetentionEvent model — the retention_event record class (v0.5.0).

Tombstones, redaction receipts, hold events, and policy publications all
use the ``retention_event`` record class. Rows of this class are exempt
from ordinary retention rules and are retained indefinitely — the event
log is the permanent memory of what the reaper did and why.

Design authority: Notion "Forensic Retention Policies — Policy Model (v0.5.0)".

Event types:

* ``tombstone`` — a record was pruned. The payload carries the pruned
  row's ``entry_hash``, ``entry_hash_org``, ``audit_id``,
  ``org_chain_seq``, and the exact ``merkle_root`` hex of the checkpoint
  covering it, plus ``reason`` (one of ``TOMBSTONE_REASONS``), the
  ``rule_id`` that selected it, the ``checkpoint_id`` whose witnessing
  authorized the prune, and ``pruned_at``. High-sampling batches may
  carry compact ``(sequence, hashes)`` tuples instead of one row per
  record. References to pruned rows are soft (no FK) — a hard FK would
  block the very pruning the tombstone records.
* ``redaction_receipt`` — stored redaction was applied. The payload
  carries ``scope`` (``stored`` for v0.5.0; ``export`` reserved for
  later reuse without a schema bump) and the fields needed to verify the
  redaction against a pre-redaction export. A redacted row is verified
  through its receipt, not by recomputing the original HMAC — the
  canonical payload included the full ``request_metadata``, so HMAC
  recomputation after redaction is impossible by construction.
* ``hold_placed`` / ``hold_released`` — mirror of the legal-hold
  lifecycle (references ``legal_holds.id`` in the payload).
* ``policy_published`` — a new retention policy version took effect
  (references ``retention_policies.id`` in the payload).

Inclusion under a witnessed checkpoint is sufficient for a tombstone —
no Rekor entry per tombstone. (Rekor is not a current witness.)

``created_by`` is an opaque principal ID, never an email.
"""

from __future__ import annotations

import datetime  # noqa: TC003 — used by SQLAlchemy at mapper-config time
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base
from common.models.retention_policy import TOMBSTONE_REASONS  # noqa: F401 — re-export

# Retention event types.
RETENTION_EVENT_TYPES = frozenset(
    {
        "tombstone",
        "redaction_receipt",
        "hold_placed",
        "hold_released",
        "policy_published",
    }
)


class RetentionEvent(Base):
    """One immutable retention-plane event: tombstone, receipt, hold, or publish."""

    __tablename__ = "retention_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # tombstone | redaction_receipt | hold_placed | hold_released | policy_published
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Type-specific payload — see module docstring for each shape.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Opaque principal ID — never an email. The reaper uses its own
    # service principal here.
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Attestation cross-check: "every event of this type in this org,
        # newest first" (frozen audit-ID lists verify every missing ID has
        # a tombstone).
        Index("ix_retention_events_org_type_created", "org_id", "event_type", "created_at"),
        Index("ix_retention_events_org_created", "org_id", "created_at"),
    )
