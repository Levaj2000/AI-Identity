"""RetentionPolicy model — forensic retention policies (v0.5.0 Enterprise Forensics).

A retention policy decides how long forensic records live, when they are
redacted, and which fraction survives sampling. It is separate from the
runtime access policy (:class:`~common.models.policy.Policy`): the access
policy is the *mandate* (limits before an agent acts); the retention policy
governs the *evidence* (what survives after).

Design authority: Notion "Forensic Retention Policies — Policy Model (v0.5.0)".

Key semantics (enforced at the API layer, documented here):

* **First-match precedence** — ``rules`` are evaluated top to bottom; the
  first rule whose selector matches a record wins. Policy-create validation
  rejects a policy without a terminal catch-all, rejects fully
  shadowed/unreachable rules, and warns when a broader selector precedes a
  narrower overlapping one. An explain endpoint returns the matched
  ``rule_id`` for a supplied record.
* **Immutable versions** — a policy row is never mutated. Every change
  publishes a new row with ``version + 1`` and flips the previous active
  row to ``superseded``. Policy changes are themselves chained evidence
  (emitted as ``policy_published`` retention events).
* **Shortening safeguards** — retention shortening requires dual approval,
  takes effect after a 7-day delay (``effective_at``), never below the
  platform minimum floor, and no row is pruned before its checkpoint is
  mirrored.
* **Plan ceilings** — Free P30D (fixed, no custom policy), Pro P90D,
  Business P13M, Enterprise P10Y or indefinite. ``flow_tag: regulated``
  has a minimum of P6M. Holds are ceiling-exempt; excess durability may be
  billed per retained GB. Downgrades never prune immediately — they use a
  grace window and tombstone reason ``plan_ceiling``.
* **Durations** are ISO-8601 restricted to days, weeks, and years
  (``P1M`` is ambiguous and rejected). ``redact_after`` must be strictly
  less than ``retain_for``.
* **Sampling** pins ``sampling.alg: "sha256-mod-v1"`` inside the immutable
  policy version::

      h = SHA-256("aiid-sample-v1" || policy_id || rule_id || record_id)
      keep = (int.from_bytes(h[:8], "big") % of) < keep

  Sampled-out records are pruned at the first reaper run after their
  checkpoint is witnessed, with tombstone reason ``sampling``; sampled-in
  records follow ``retain_for``.
* ``created_by`` is an opaque principal ID, never an email.
"""

from __future__ import annotations

import datetime  # noqa: TC003 — used by SQLAlchemy at mapper-config time
import uuid

import sqlalchemy as sa
from sqlalchemy import (
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

# Tombstone reasons (also documented on RetentionEvent). Kept here as the
# canonical list so the reaper and the API validate against one source.
TOMBSTONE_REASONS = frozenset(
    {
        "retention_elapsed",
        "sampling",
        "erasure_request",
        "tenant_offboarding",
        "plan_ceiling",
    }
)

# Policy lifecycle states.
POLICY_STATUSES = frozenset({"draft", "active", "superseded"})

# The only sampling algorithm pinned for v0.5.0. Stored inside the immutable
# policy version so a future algorithm change is a new policy version, not a
# silent behavior change for existing versions.
SAMPLING_ALG_V1 = "sha256-mod-v1"


class RetentionPolicy(Base):
    """One immutable version of an org's forensic retention policy."""

    __tablename__ = "retention_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Stable identifier across versions, e.g. "retpol_7f3a…". Versions of the
    # same policy share it; (org_id, policy_id, version) is unique.
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False)

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # draft | active | superseded. Exactly one active version per org
    # (partial unique index below).
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")

    # Ordered rule array — first match wins. Each rule:
    #   {rule_id, selector{record_class, flow_tag[], decision[], agent_id[],
    #    session_id, risk_tier[], event_type},
    #    retain_for, redact_after|null, sampling{alg, of, keep}|null,
    #    hold_exempt}
    # The terminal catch-all rule is required (validated at create time).
    rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # The default rule applied when no rule matches (the required catch-all
    # is typically also the last entry of ``rules``; this column keeps the
    # fallback explicit for the reaper's hot path).
    default_rule: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Opaque principal ID — never an email.
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # When this version takes effect. Retention shortening defaults to a
    # 7-day delayed effect; set explicitly by the API layer.
    effective_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Previous version this one supersedes (self-FK, soft — history survives).
    supersedes: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retention_policies.id", ondelete="SET NULL"),
        nullable=True,
    )

    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Dual-approval trail for retention shortening:
    # [{by: <opaque principal id>, at: <iso8601>}]. Empty for non-shortening
    # changes or single-approval tiers.
    approvals: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("org_id", "policy_id", "version", name="uq_retention_policy_version"),
        # Exactly one active policy version per org. sqlite_where keeps the
        # in-memory test DB honest with prod Postgres behavior.
        Index(
            "uq_retention_policies_org_active",
            "org_id",
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
            sqlite_where=sa.text("status = 'active'"),
        ),
        Index("ix_retention_policies_org_status", "org_id", "status"),
    )
