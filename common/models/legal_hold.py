"""LegalHold model — litigation/regulatory holds that freeze pruning (v0.5.0).

A legal hold exempts matching records from pruning for as long as it is
active — holds are ceiling-exempt, so they may keep records past the plan's
retention ceiling. Excess durability from holds may be billed per retained
GB (pricing concern, not modeled here).

Design authority: Notion "Forensic Retention Policies — Policy Model (v0.5.0)".

* Hold selectors support ``record_ids``, ``agent_id``, and a time window —
  stored as JSONB so selector shapes can grow without a schema migration.
* Hold placement and release are both emitted as ``retention_event`` rows
  (``hold_placed`` / ``hold_released``) — the event log is the immutable
  audit trail; this table is the queryable current state for the reaper.
* Release requires a reason and an approver different from the placer
  (enforced at the API layer).
* ``created_by`` / ``placed_by`` / ``released_by`` are opaque principal IDs,
  never emails.
"""

from __future__ import annotations

import datetime  # noqa: TC003 — used by SQLAlchemy at mapper-config time
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base

# Hold lifecycle states.
HOLD_STATUSES = frozenset({"active", "released"})


class LegalHold(Base):
    """A legal/regulatory hold freezing pruning of matching records."""

    __tablename__ = "legal_holds"

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

    # Hold selector — supports record_ids, agent_id, and a time window:
    #   {record_ids: [<audit_log id>, ...], agent_id: <uuid str>,
    #    time_window: {from: <iso8601>, to: <iso8601>},
    #    record_class: "audit" | ..., note: <str>}
    # A record is frozen when it matches the selector. Empty selector fields
    # are wildcards.
    selector: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # active | released.
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    # Opaque principal IDs — never emails.
    placed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    placed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    released_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Must differ from placed_by (enforced at the API layer).
    released_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # Reaper hot path: "active holds for this org".
        Index("ix_legal_holds_org_status", "org_id", "status"),
    )
