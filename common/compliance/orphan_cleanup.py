"""Reap compliance-export jobs stuck in an in-flight state.

Why this exists: the builder runs inline via FastAPI ``BackgroundTasks``.
If the pod that accepted the POST gets killed (rolling deploy, OOM,
node drain) before the background task finishes, the job is left in
``queued`` or ``building`` state with no process working on it. The
row sits forever and blocks any future request with the same scope
via the idempotency unique index.

A real job queue (Cloud Run + Pub/Sub per ADR-002 §"Build pipeline")
would solve this with retries and visibility-timeout reassignment.
Until that lands, we run this reaper at API startup so every pod
boot clears any orphans the previous pod left behind.

Behavior:

- Finds rows in (queued, building) whose ``created_at`` is older
  than the stale threshold (default 10 minutes).
- Transitions each to ``failed`` with
  ``error_code="orphaned_on_restart"`` and a message describing why.
- Idempotent — safe to re-run. A job completed mid-reap by another
  worker won't be touched (status filter catches it).

Intentionally conservative threshold: 10 minutes is long enough that
a genuinely slow build (large audit window, KMS latency) isn't
reaped mid-flight, but short enough that a failed deploy cleanup
happens on the next pod boot rather than sitting around.
"""

from __future__ import annotations

import datetime
import logging

from sqlalchemy.orm import Session  # noqa: TC002 — runtime db.query

from common.compliance.job import BUILDING, FAILED, QUEUED
from common.models import ComplianceExport

logger = logging.getLogger("ai_identity.compliance.orphan_cleanup")

DEFAULT_STALE_THRESHOLD_MINUTES = 10


def reap_orphaned_exports(
    db: Session,
    *,
    stale_threshold_minutes: int = DEFAULT_STALE_THRESHOLD_MINUTES,
    now: datetime.datetime | None = None,
) -> int:
    """Mark stuck in-flight jobs as failed. Returns the count reaped.

    ``now`` overrideable for tests; production callers should use the
    default ``datetime.datetime.now(tz=UTC)``.
    """
    effective_now = now or datetime.datetime.now(tz=datetime.UTC)
    cutoff = effective_now - datetime.timedelta(minutes=stale_threshold_minutes)

    orphans = (
        db.query(ComplianceExport)
        .filter(
            ComplianceExport.status.in_((QUEUED, BUILDING)),
            ComplianceExport.created_at <= cutoff,
        )
        .all()
    )
    if not orphans:
        return 0

    for orphan in orphans:
        # Capture original status BEFORE mutating — the error message
        # needs to tell the operator which state the job was stuck in
        # (queued vs building), not the post-reap 'failed'.
        prior_status = orphan.status
        orphan.status = FAILED
        orphan.error_code = "orphaned_on_restart"
        orphan.error_message = (
            f"Job was in {prior_status!r} for longer than "
            f"{stale_threshold_minutes} minutes at API restart; the "
            "pod that accepted the request was almost certainly "
            "terminated mid-build. Re-request the export — a fresh "
            "job on the current pod will complete normally."
        )
        orphan.completed_at = effective_now

    db.commit()
    logger.info(
        "compliance export orphan cleanup reaped %d job(s)",
        len(orphans),
        extra={"orphan_ids": [str(o.id) for o in orphans]},
    )
    return len(orphans)
