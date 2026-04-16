"""Audit outbox — enqueue at write time, flush in batches.

Split into two halves:

* ``enqueue_for_sinks`` — called synchronously from the audit writer right
  after a successful ``audit_log`` insert. For each active, matching sink
  in the org, write one pending ``audit_log_outbox`` row. Filters are
  applied here so disabled / mismatched sinks never generate an outbox row.

* ``flush_outbox`` — the worker side. Called by a CronJob, a CLI command,
  or a scheduled task. Claims a batch of due rows with ``FOR UPDATE SKIP
  LOCKED``, groups them by sink, hands each batch to the sink's transport,
  and updates status. Never raises — worker errors surface as ``failed``
  outbox rows or log warnings.

The worker is a pure function; no module-level state, no background thread.
This makes it trivial to run as a K8s CronJob, a one-shot CLI, or a
scheduled task, and easy to test.
"""

from __future__ import annotations

import logging
import uuid  # noqa: TC003 — used in dataclass field types at runtime
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session  # noqa: TC002 — runtime Session arg

from common.audit.transports import TRANSPORTS, DeliveryResult
from common.models.audit_log import AuditLog
from common.models.audit_outbox import AuditLogOutbox, OutboxStatus
from common.models.audit_sink import AuditLogSink

logger = logging.getLogger("ai_identity.audit.outbox")


# ── Config ───────────────────────────────────────────────────────────

# Per-row retry schedule. Each entry is the delay before the Nth attempt.
# A row that's failed N times uses ``_RETRY_DELAYS[N-1]`` (capped at the
# last entry). After exhausting the schedule, status flips to dead_letter.
_RETRY_DELAYS: list[timedelta] = [
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=6),
]
MAX_ATTEMPTS = len(_RETRY_DELAYS)

# Circuit breaker: after this many consecutive failures, open the sink's
# breaker and stop trying until an operator re-enables it or enough time
# passes. Kept conservative — one sink going bad shouldn't block an org's
# other sinks, but we don't want to hammer a broken endpoint forever either.
CIRCUIT_BREAKER_THRESHOLD = 10


# ── Enqueue (write-time) ─────────────────────────────────────────────


def _event_matches_filter(
    decision: str,
    request_metadata: dict[str, Any] | None,
    filter_config: dict[str, Any],
) -> bool:
    """Evaluate a sink's filter against a single event.

    Empty / missing filter = match everything. Keys not understood by this
    version are ignored (forward compat for future filter additions).
    """
    if not filter_config:
        return True

    decisions = filter_config.get("decisions")
    if decisions and decision not in decisions:
        return False

    action_types = filter_config.get("action_types")
    if action_types:
        metadata = request_metadata or {}
        if metadata.get("action_type") not in action_types:
            return False

    return True


def enqueue_for_sinks(
    db: Session,
    *,
    audit_entry: AuditLog,
) -> int:
    """For each active sink in the org, add a pending outbox row if the filter matches.

    Safe to call in the same transaction as the audit insert. If no sinks
    are configured for the org (the common case today), returns 0 without
    hitting the network or logging noise.

    Returns the number of outbox rows inserted.
    """
    org_id = audit_entry.org_id
    if org_id is None:
        return 0

    sinks = (
        db.query(AuditLogSink)
        .filter(
            AuditLogSink.org_id == org_id,
            AuditLogSink.enabled.is_(True),
            AuditLogSink.deleted_at.is_(None),
        )
        .all()
    )
    if not sinks:
        return 0

    inserted = 0
    for sink in sinks:
        if not _event_matches_filter(
            decision=audit_entry.decision,
            request_metadata=audit_entry.request_metadata,
            filter_config=sink.filter_config or {},
        ):
            continue

        db.add(
            AuditLogOutbox(
                audit_log_id=audit_entry.id,
                sink_id=sink.id,
                org_id=org_id,
                status=OutboxStatus.pending.value,
            )
        )
        inserted += 1

    if inserted:
        # Flush so the caller's outer commit picks up the rows.
        db.flush()
    return inserted


# ── Flush (worker-time) ──────────────────────────────────────────────


@dataclass
class FlushResult:
    """Summary of a single flush_outbox call — useful for ops dashboards."""

    rows_claimed: int
    delivered: int
    failed: int
    dead_lettered: int
    sinks_touched: set[uuid.UUID]

    @property
    def total_processed(self) -> int:
        return self.delivered + self.failed + self.dead_lettered


def _serialize_event(entry: AuditLog) -> dict[str, Any]:
    """Shape an AuditLog row as the per-event JSON that goes in the envelope."""
    return {
        "id": entry.id,
        "agent_id": str(entry.agent_id),
        "agent_name": entry.agent_name,
        "org_id": str(entry.org_id) if entry.org_id else None,
        "user_id": str(entry.user_id) if entry.user_id else None,
        "correlation_id": entry.correlation_id,
        "endpoint": entry.endpoint,
        "method": entry.method,
        "decision": entry.decision,
        "cost_estimate_usd": (
            float(entry.cost_estimate_usd) if entry.cost_estimate_usd is not None else None
        ),
        "latency_ms": entry.latency_ms,
        "request_metadata": entry.request_metadata,
        "entry_hash": entry.entry_hash,
        "prev_hash": entry.prev_hash,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def _schedule_next_attempt(attempts: int) -> datetime:
    """When should the next retry fire for a row that's failed ``attempts`` times?"""
    idx = min(attempts - 1, len(_RETRY_DELAYS) - 1)
    return datetime.now(UTC) + _RETRY_DELAYS[idx]


def flush_outbox(
    db: Session,
    *,
    limit: int = 100,
    now: datetime | None = None,
) -> FlushResult:
    """Claim up to ``limit`` due rows, deliver per sink, update statuses.

    Uses ``FOR UPDATE SKIP LOCKED`` on PostgreSQL so horizontal worker
    scaling is safe — multiple workers will pick up disjoint rows.
    Falls back to a plain SELECT on SQLite (tests), which is fine because
    tests don't have concurrent workers.

    Callers own the transaction boundary — commit on return, rollback on
    exception. The function itself commits once near the end to release
    the row locks promptly, then issues a fresh transaction if needed
    for status writes; read-modify-write on the same row is always inside
    one transaction.
    """
    dialect = db.bind.dialect.name if db.bind else "unknown"
    now = now or datetime.now(UTC)

    # 1. Claim rows that are due. Include sink join so we can skip rows
    #    whose sink got disabled / deleted / circuit-opened after enqueue.
    stmt = (
        select(AuditLogOutbox)
        .where(
            AuditLogOutbox.status.in_((OutboxStatus.pending.value, OutboxStatus.failed.value)),
            AuditLogOutbox.next_attempt_at <= now,
        )
        .order_by(AuditLogOutbox.id.asc())
        .limit(limit)
    )
    if dialect == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)

    claimed_rows: list[AuditLogOutbox] = list(db.execute(stmt).scalars().all())
    if not claimed_rows:
        return FlushResult(
            rows_claimed=0,
            delivered=0,
            failed=0,
            dead_lettered=0,
            sinks_touched=set(),
        )

    # 2. Group by sink.
    by_sink: dict[uuid.UUID, list[AuditLogOutbox]] = {}
    for row in claimed_rows:
        by_sink.setdefault(row.sink_id, []).append(row)

    delivered = 0
    failed = 0
    dead_lettered = 0
    sinks_touched: set[uuid.UUID] = set()

    # 3. Per sink: skip unhealthy sinks, fetch events, deliver, update status.
    for sink_id, rows in by_sink.items():
        sink = db.query(AuditLogSink).filter(AuditLogSink.id == sink_id).first()
        if sink is None or not sink.enabled or sink.deleted_at is not None:
            # Sink vanished or got disabled between enqueue and flush —
            # leave rows in pending; operator can force-delete or re-enable.
            logger.info(
                "skipping outbox rows for inactive/deleted sink %s (%d rows)",
                sink_id,
                len(rows),
            )
            continue

        if sink.consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            # Circuit-breaker open — don't hammer a known-broken endpoint.
            # Operator must explicitly re-enable or rotate secret.
            logger.warning(
                "circuit breaker open for sink %s (%d consecutive failures); skipping",
                sink_id,
                sink.consecutive_failures,
            )
            continue

        transport = TRANSPORTS.get(sink.kind)
        if transport is None:
            logger.error("no transport registered for sink kind %r", sink.kind)
            continue

        # Fetch the referenced audit_log rows in one query.
        audit_ids = [row.audit_log_id for row in rows]
        audit_rows = db.query(AuditLog).filter(AuditLog.id.in_(audit_ids)).all()
        audit_by_id = {a.id: a for a in audit_rows}

        events: list[dict[str, Any]] = []
        for row in rows:
            entry = audit_by_id.get(row.audit_log_id)
            if entry is None:
                # audit row got deleted — data integrity issue, flag and skip.
                row.status = OutboxStatus.dead_letter.value
                row.last_error = "referenced audit_log row no longer exists"
                row.last_attempt_at = now
                dead_lettered += 1
                continue
            events.append(_serialize_event(entry))

        if not events:
            # All rows were orphaned; nothing to send.
            sinks_touched.add(sink_id)
            continue

        result: DeliveryResult = transport.deliver(
            events=events,
            url=sink.url,
            secret=sink.secret,
        )
        sinks_touched.add(sink_id)

        if result.success:
            for row in rows:
                if row.status == OutboxStatus.dead_letter.value:
                    continue  # orphaned row, already marked above
                row.status = OutboxStatus.delivered.value
                row.delivered_at = now
                row.last_attempt_at = now
                row.attempts += 1
                delivered += 1
            sink.consecutive_failures = 0
            sink.circuit_opened_at = None
        else:
            for row in rows:
                if row.status == OutboxStatus.dead_letter.value:
                    continue  # orphaned row, already marked above
                row.attempts += 1
                row.last_attempt_at = now
                row.last_error = result.error
                if row.attempts >= MAX_ATTEMPTS:
                    row.status = OutboxStatus.dead_letter.value
                    dead_lettered += 1
                else:
                    row.status = OutboxStatus.failed.value
                    row.next_attempt_at = _schedule_next_attempt(row.attempts)
                    failed += 1
            sink.consecutive_failures += 1
            if (
                sink.consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD
                and sink.circuit_opened_at is None
            ):
                sink.circuit_opened_at = now
                logger.error(
                    "circuit breaker opened for sink %s after %d consecutive failures",
                    sink_id,
                    sink.consecutive_failures,
                )

    db.commit()

    return FlushResult(
        rows_claimed=len(claimed_rows),
        delivered=delivered,
        failed=failed,
        dead_lettered=dead_lettered,
        sinks_touched=sinks_touched,
    )
