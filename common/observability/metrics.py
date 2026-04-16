"""Prometheus metric collectors for AI Identity.

Every collector lives at module scope so it's a singleton per-process. The
API and Gateway services each have their own process and their own
registry — Prometheus scrapes them separately and the customer's Grafana
aggregates across targets.

Cardinality discipline
----------------------
Prometheus labels multiply. We deliberately keep labels bounded:

* ``decision``     — 3 values (allow / deny / error)
* ``reason``       — ~10 values (DenyReason enum)
* ``outcome``      — 3 values (delivered / failed / dead_letter)
* ``status``       — enum values (agent / sink status)

We do NOT label by ``org_id``, ``agent_id``, or any per-request value.
Those belong in the SIEM (Phase 2A forwarding), not in the metrics series.

Compute-on-scrape gauges
------------------------
``db_backed_gauges`` is populated lazily by the ``/metrics`` handler from
live DB queries (agent counts, outbox backlog, sink health). We don't hold
these values in-memory because they change based on other writers (other
API pods, migrations, manual cleanup). A 30-second Prometheus scrape
interval means one query per 30 seconds per service — negligible load.
"""

from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
)
from prometheus_client.metrics_core import Metric

# Dedicated registry (instead of the default global one) so tests can spin
# up fresh collectors per-case without needing prometheus_client's
# somewhat-quirky unregistration dance.
REGISTRY = CollectorRegistry()


# ── Audit counters / histogram ─────────────────────────────────────────

audit_events_total = Counter(
    "ai_identity_audit_events_total",
    "Total audit_log rows written, labeled by decision.",
    ["decision"],
    registry=REGISTRY,
)

audit_denies_total = Counter(
    "ai_identity_audit_denies_total",
    "Breakdown of denied events by deny reason.",
    ["reason"],
    registry=REGISTRY,
)

audit_latency_ms = Histogram(
    "ai_identity_audit_latency_ms",
    "Observed latency of audited requests (milliseconds).",
    # Buckets tuned for policy-engine + gateway enforcement workloads.
    # Anything > 1s is a real red flag worth bucketing separately.
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
    registry=REGISTRY,
)


# ── Audit forwarding (Phase 2A) ────────────────────────────────────────

outbox_deliveries_total = Counter(
    "ai_identity_outbox_deliveries_total",
    "Audit-log forwarding outcomes from flush_outbox, labeled by outcome.",
    ["outcome"],  # "delivered" | "failed" | "dead_letter"
    registry=REGISTRY,
)


# ── Process-level gauges (populated on scrape) ─────────────────────────

agents_total = Gauge(
    "ai_identity_agents_total",
    "Count of agents in the system, labeled by status.",
    ["status"],
    registry=REGISTRY,
)

organizations_total = Gauge(
    "ai_identity_organizations_total",
    "Total organizations in the system (excluding the sentinel system org).",
    registry=REGISTRY,
)

outbox_backlog = Gauge(
    "ai_identity_outbox_backlog",
    "Pending / failed / dead-lettered outbox rows awaiting worker action.",
    ["status"],
    registry=REGISTRY,
)

sinks_total = Gauge(
    "ai_identity_sinks_total",
    "Audit-forwarding sinks by enabled state.",
    ["enabled"],
    registry=REGISTRY,
)

sinks_circuit_open = Gauge(
    "ai_identity_sinks_circuit_open",
    "Count of sinks whose circuit breaker is currently open.",
    registry=REGISTRY,
)


# ── Helper: in-process counter bumps (writer + outbox call these) ──────


def record_audit_write(
    *,
    decision: str,
    deny_reason: str | None = None,
    latency_ms: int | None = None,
) -> None:
    """Increment the audit counters for a single event.

    Safe to call from any async/sync context — prometheus_client is
    thread-safe and drops no samples under contention. Any exception here
    is swallowed: observability must never change the audited decision.
    """
    try:
        audit_events_total.labels(decision=decision).inc()
        if decision in ("deny", "denied") and deny_reason:
            audit_denies_total.labels(reason=deny_reason).inc()
        if latency_ms is not None and latency_ms >= 0:
            audit_latency_ms.observe(latency_ms)
    except Exception:  # pragma: no cover — defensive
        import logging

        logging.getLogger("ai_identity.metrics").warning("metrics emission failed", exc_info=True)


def record_outbox_delivery(outcome: str, *, count: int = 1) -> None:
    """Record one or more outbox delivery outcomes.

    ``outcome`` must be one of: ``delivered``, ``failed``, ``dead_letter``.
    """
    if count <= 0:
        return
    try:
        outbox_deliveries_total.labels(outcome=outcome).inc(count)
    except Exception:  # pragma: no cover — defensive
        import logging

        logging.getLogger("ai_identity.metrics").warning("metrics emission failed", exc_info=True)


# ── DB-backed gauge refresh (called by /metrics handler on scrape) ─────


def refresh_db_gauges(db) -> None:  # type: ignore[no-untyped-def]
    """Populate the DB-backed gauges from live queries.

    Called once per scrape from the ``/metrics`` HTTP handler. Never
    raises — a DB hiccup during scrape shouldn't page anyone; Prometheus
    will notice missing samples on its own and alert per staleness rules.
    """
    try:
        from sqlalchemy import func, select

        from common.models import (
            Agent,
            AuditLogOutbox,
            AuditLogSink,
            Organization,
            OutboxStatus,
        )
        from common.models.organization import SYSTEM_ORG_ID

        # Agent counts by status
        agents_total.clear()
        rows = db.execute(select(Agent.status, func.count(Agent.id)).group_by(Agent.status)).all()
        for status, count in rows:
            agents_total.labels(status=status or "unknown").set(count)

        # Organization count (exclude sentinel system org)
        org_count = db.execute(
            select(func.count(Organization.id)).where(Organization.id != SYSTEM_ORG_ID)
        ).scalar()
        organizations_total.set(org_count or 0)

        # Outbox backlog by status — interested in not-yet-terminal states
        outbox_backlog.clear()
        rows = db.execute(
            select(AuditLogOutbox.status, func.count(AuditLogOutbox.id))
            .where(
                AuditLogOutbox.status.in_(
                    (
                        OutboxStatus.pending.value,
                        OutboxStatus.failed.value,
                        OutboxStatus.dead_letter.value,
                    )
                )
            )
            .group_by(AuditLogOutbox.status)
        ).all()
        for status, count in rows:
            outbox_backlog.labels(status=status).set(count)

        # Sinks by enabled state (soft-deleted excluded)
        sinks_total.clear()
        rows = db.execute(
            select(AuditLogSink.enabled, func.count(AuditLogSink.id))
            .where(AuditLogSink.deleted_at.is_(None))
            .group_by(AuditLogSink.enabled)
        ).all()
        for enabled, count in rows:
            sinks_total.labels(enabled=str(bool(enabled)).lower()).set(count)

        # Open circuit breakers
        open_count = db.execute(
            select(func.count(AuditLogSink.id)).where(
                AuditLogSink.deleted_at.is_(None),
                AuditLogSink.circuit_opened_at.isnot(None),
            )
        ).scalar()
        sinks_circuit_open.set(open_count or 0)
    except Exception:  # pragma: no cover — defensive
        import logging

        logging.getLogger("ai_identity.metrics").warning(
            "DB-backed gauge refresh failed", exc_info=True
        )


__all__ = [
    "REGISTRY",
    "Metric",
    "agents_total",
    "audit_denies_total",
    "audit_events_total",
    "audit_latency_ms",
    "organizations_total",
    "outbox_backlog",
    "outbox_deliveries_total",
    "record_audit_write",
    "record_outbox_delivery",
    "refresh_db_gauges",
    "sinks_circuit_open",
    "sinks_total",
]
