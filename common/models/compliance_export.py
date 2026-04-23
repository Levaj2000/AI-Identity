"""ComplianceExport — persisted job record for a compliance export build.

Written by the compliance export router on POST, updated by the
builder as the job advances through the FSM
(``queued → building → ready|failed``). The authoritative artifact of
a successful build is the ZIP on disk/GCS referenced by
``archive_url``; the ``manifest_envelope`` column mirrors the signed
DSSE envelope that commits to every file in the archive.

See ``docs/ADR-002-compliance-exports.md`` for the full schema
rationale — this model is the implementation of the "Data model"
section.
"""

from __future__ import annotations

import datetime  # noqa: TC003 — used by SQLAlchemy at mapper-config time
import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class ComplianceExport(Base):
    """One compliance export job — queued, building, or terminal."""

    __tablename__ = "compliance_exports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Ownership & tenancy ------------------------------------------------
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Scope ---------------------------------------------------------------
    profile: Mapped[str] = mapped_column(String(40), nullable=False)
    audit_period_start: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    audit_period_end: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Null → whole org. On Postgres this is a native UUID[]; the SQLite
    # test fallback uses JSON so the migration is portable.
    agent_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)).with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    # Deterministic hash of the sorted agent_ids list — empty-string
    # sentinel for "null / whole org" so the unique index can treat that
    # as a distinct bucket. Postgres can't unique-index an ARRAY in a
    # way that treats [a,b] and [b,a] as equal, so the hash is computed
    # at write time (see common.compliance.agent_ids_hash).
    agent_ids_hash: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")

    # FSM -----------------------------------------------------------------
    # enum: queued | building | ready | failed — enforced at app layer.
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    progress_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Archive pointers ---------------------------------------------------
    archive_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    archive_url_expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archive_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    archive_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # The DSSE envelope mirrors attestation.envelope so downstream tools
    # can reuse the same shape for manifest verification.
    manifest_envelope: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Internal path where the archive lives on disk/object storage.
    # Distinct from archive_url (which is the client-facing URL, may
    # expire). The builder populates this on success; the download
    # endpoint resolves it. Null when status != ready.
    archive_storage_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Terminal error (status == failed) ----------------------------------
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps ---------------------------------------------------------
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # Idempotency guard — return 409 on duplicate IN-FLIGHT job.
        # PARTIAL unique index: only enforces on status ∈ (queued,
        # building). Terminal rows (ready/failed) can accumulate per
        # scope without conflict, so cancel / orphan-reap / repeated
        # retries after a failed build all work.
        #
        # The original UniqueConstraint (#275) included `status` in
        # the column set without a WHERE clause; that meant only one
        # `failed` row could exist per scope, which broke every
        # transition-to-failed once the first one landed. This
        # partial index is the correction.
        Index(
            "uq_compliance_export_inflight",
            "org_id",
            "profile",
            "audit_period_start",
            "audit_period_end",
            "agent_ids_hash",
            unique=True,
            postgresql_where=text("status IN ('queued', 'building')"),
            # SQLite also supports partial indexes; needed for the
            # in-memory test DB that reaches the model directly via
            # metadata.create_all (no Alembic migration path).
            sqlite_where=text("status IN ('queued', 'building')"),
        ),
        # List endpoint: newest first, per-org.
        Index(
            "ix_compliance_exports_org_created_at",
            "org_id",
            "created_at",
        ),
        # Worker polling: queued jobs per org.
        Index(
            "ix_compliance_exports_org_status",
            "org_id",
            "status",
        ),
    )
