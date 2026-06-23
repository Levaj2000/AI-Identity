"""AuditLog model — immutable record of every gateway decision."""

import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class AuditLog(Base):
    """An immutable log entry for every request the gateway processes."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Denormalized user_id for RLS tenant isolation (defense-in-depth).
    # Nullable because orphaned entries (agent deleted) may lack a user_id.
    # NOT included in the HMAC integrity chain — it's an access-control field.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Denormalized org_id for fast org-scoped queries (Cisco-scale multi-tenant).
    # Populated from agent.org_id at write time; backfilled for legacy rows via
    # migration o6l7m8n9o0p1. NOT included in the HMAC integrity chain — it's
    # an access-control field derivable from agent_id.
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # End-to-end correlation ID — one value travels client → API → gateway
    # → audit row. Enables operators (and SIEM pipelines) to reconstruct a
    # single user action across services with a point query.
    # See common/audit/correlation.py for generation / header handling.
    # NOT included in the HMAC chain — it's operational metadata, not a
    # statement about what the request did.
    correlation_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    # Request details
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)

    # Decision
    decision: Mapped[str] = mapped_column(String(10), nullable=False)  # allow, deny, error

    # Metrics
    cost_estimate_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Denormalized agent name — survives agent hard-deletion during purge
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Flexible request context
    request_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # HMAC integrity chain — links each entry to the previous one
    entry_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="HMAC-SHA256 of this entry's canonical data + prev_hash",
    )
    prev_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="entry_hash of the preceding row; GENESIS for the first entry",
    )

    # Per-org HMAC chain (Phase 1 of per-org chain migration).
    # Nullable while dual-write rolls out and legacy rows are backfilled.
    # See docs/audit-chain-per-org-migration.md.
    prev_hash_org: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="entry_hash_org of preceding row in this org; GENESIS for org's first row",
    )
    entry_hash_org: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="HMAC-SHA256 of canonical data + prev_hash_org",
    )
    org_chain_seq: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="1-based monotonic sequence within org_id; completeness guard",
    )

    # Timestamp — server_default kept as fallback; writer sets explicitly for hash
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships — soft FK (no CASCADE, audit logs survive agent deletion)
    agent: Mapped["Agent"] = relationship(  # noqa: F821
        back_populates="audit_logs",
        primaryjoin="Agent.id == foreign(AuditLog.agent_id)",
    )

    # Composite indexes for query performance
    __table_args__ = (
        Index("ix_audit_log_agent_created", "agent_id", "created_at"),
        Index("ix_audit_log_user_created", "user_id", "created_at"),
        # Primary enterprise query pattern: "all events in this org, newest first"
        Index("ix_audit_log_org_created", "org_id", "created_at"),
        # Evidence Anchor checkpoint cron (#408): the candidate query groups by
        # org_id and takes max(id) to find orgs with un-anchored rows. This
        # (org_id, id) B-tree lets Postgres satisfy that grouped-max with an
        # index scan instead of a full audit_log seq scan every tick.
        Index("ix_audit_log_org_id_id", "org_id", "id"),
        # Per-org chain completeness guard. NULLs are distinct in both PG
        # and SQLite by default, so legacy unbackfilled rows don't collide;
        # populated rows enforce one-row-per-sequence per org.
        UniqueConstraint("org_id", "org_chain_seq", name="uq_audit_log_org_chain_seq"),
    )
