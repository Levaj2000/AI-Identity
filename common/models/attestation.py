"""ForensicAttestation — persisted DSSE envelope for a session's audit range.

Written by :mod:`api.app.routers.attestations` at session close. Read by
the retrieval API (#264) and the CLI verify tool (#266). See
``docs/forensics/attestation-format.md`` for the signed payload format.

The envelope column is the authoritative artifact — all the other
columns either mirror fields from inside the envelope for indexing, or
capture resolution state at signing time (``audit_log_ids``,
``event_count``) so the attestation stays verifiable even if the
underlying ``audit_log`` rows are later pruned by retention. See the
"Retention coordination" section of the design doc for why that
redundancy is deliberate.
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


class ForensicAttestation(Base):
    """One signed attestation for a (org_id, session_id) pair."""

    __tablename__ = "forensic_attestations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Business keys -------------------------------------------------------
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Frozen scope — what range of audit rows this envelope covers ------
    # first_audit_id and last_audit_id mirror the envelope fields for
    # indexing (so "find the attestation that includes row N" is an
    # indexed range scan, not a JSON query).
    first_audit_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_audit_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Resolved row IDs at sign time — purge-resilient.
    # The signer walked [first_audit_id, last_audit_id] and recorded
    # exactly which rows were present. If retention later drops some of
    # these, a verifier can say "the chain existed at sign time but N
    # rows are missing now" instead of silently accepting a truncated
    # chain. On Postgres this is a native ARRAY; SQLite tests skip this
    # path by falling back to JSON.
    audit_log_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer).with_variant(JSON(), "sqlite"),
        nullable=False,
    )

    # Session window — mirrors the envelope for range queries ----------
    session_start: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    session_end: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Signature metadata -------------------------------------------------
    signer_key_id: Mapped[str] = mapped_column(String(512), nullable=False)
    signed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # The authoritative artifact — the full DSSE envelope as JSON.
    # Everything else in this row can be derived from it; the mirrored
    # columns exist only for query performance.
    envelope: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # One attestation per (org, session) — re-signing the same
        # session would produce conflicting evidence. #263 enforces
        # idempotency at the router layer (return existing on duplicate).
        UniqueConstraint("org_id", "session_id", name="uq_attestation_org_session"),
        # Fast "find attestation covering audit row N" for the range
        # scan called from the CLI verify tool (#266).
        Index(
            "ix_forensic_attestation_range",
            "org_id",
            "first_audit_id",
            "last_audit_id",
        ),
        Index(
            "ix_forensic_attestation_signed_at",
            "org_id",
            "signed_at",
        ),
    )
