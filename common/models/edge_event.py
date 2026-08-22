"""EdgeAuditEvent model — an ingested OCSF record from an edge deployment.

Rows are append-only. Every record that parses is stored, whatever its
verification outcome. Integrity failures (bad signature, fingerprint or
chain-identity mismatch) quarantine the record — it cannot be trusted
and never advances chain or stream state. Continuity observations on a
crypto-valid record (a stream gap, a chain discontinuity after a crashed
edge epoch) are stored as ``anomalies`` on a verified row instead: a gap
is itself evidence, and the platform's job is to surface it, not drop
it — nor to let one lost epoch cascade-quarantine everything after it.
"""

import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class EdgeEventStatus:
    """Verification outcome for an ingested record."""

    verified = "verified"
    quarantined = "quarantined"


class EdgeAuditEvent(Base):
    """One ingested OCSF record, with its arrival-time verification outcome."""

    __tablename__ = "edge_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    edge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_deployments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chain_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # metadata.uid — the record's own id; what a successor's prev_event points at
    metadata_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Idempotency identity: metadata.uid when present, else "<stream_id>#<stream_seq>"
    # (decision records don't carry metadata.uid yet — spec §4/emitter item 5).
    # NULLs are distinct in the unique constraint, so identity-less records
    # are stored but not replay-protected.
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Recomputed SHA-256 fingerprint of the covered bytes (hex); null for
    # unsigned records, which are always quarantined.
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Seam stream stamps (unmapped."cpex.stream")
    stream_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stream_seq: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    emission_seq: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # 1-based position among VERIFIED rows of this edge's chain; null for
    # quarantined rows — they never advance the chain.
    chain_position: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    # Integrity failures — why a quarantined record cannot be trusted
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Continuity observations on a VERIFIED record (stream gap, chain
    # re-anchor) — the record is trustworthy; the stream around it has a
    # story to tell. Never set on quarantined rows.
    anomalies: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The record itself, verbatim as received
    event: Mapped[dict] = mapped_column(JSONB, nullable=False)

    received_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("edge_id", "dedupe_key", name="uq_edge_events_dedupe"),
        # Chain-head lookup: newest verified row for (edge, chain)
        Index("ix_edge_events_edge_chain_id", "edge_id", "chain_uid", "id"),
        # Org audit-health surface: "this org's edge records, newest first"
        Index("ix_edge_events_org_received", "org_id", "received_at"),
    )
