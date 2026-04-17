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


# ── Audit integrity failures ───────────────────────────────────────────
#
# Counts the rare but security-critical case where `create_audit_entry`
# raises — meaning the enforcement decision was made but we could not
# record it. This happened during the 2026-04-16 incident: audit writes
# failed for 3 days without alerting because the gateway's try/except
# only logged to stdout and Sentry's default LoggingIntegration
# deduplicated them into one event. This counter is the cheap, always-on
# backstop for monitoring: a non-zero rate over any window is a page-the-
# on-call signal because it means the forensic audit chain has gaps.

audit_write_failures_total = Counter(
    "ai_identity_audit_write_failures_total",
    "audit_log write failures by service and failure kind. "
    "A non-zero rate means the forensic audit chain has gaps — page.",
    ["service", "kind"],  # service: api | gateway; kind: schema | integrity | unknown
    registry=REGISTRY,
)


# ── Audit forwarding (Phase 2A) ────────────────────────────────────────

outbox_deliveries_total = Counter(
    "ai_identity_outbox_deliveries_total",
    "Audit-log forwarding outcomes from flush_outbox, labeled by outcome.",
    ["outcome"],  # "delivered" | "failed" | "dead_letter"
    registry=REGISTRY,
)


# ── Forensic attestation signing (#263) ────────────────────────────────
#
# Sign latency matters because a slow KMS call blocks the attestation
# POST. Labeled by backend so we can separate "KMS network call" (slow,
# bursty) from "local PEM" (fast, for dev + tests). Outcome lets alerts
# distinguish "KMS throwing" from "clean slow signs" — only the former
# should page.

attestation_sign_latency_ms = Histogram(
    "ai_identity_attestation_sign_latency_ms",
    "Observed latency of forensic attestation signing (milliseconds).",
    ["backend"],  # "kms" | "local"
    # KMS typical is 50–300ms, local is single-digit. Buckets cover both
    # without so many bins that cardinality balloons.
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500),
    registry=REGISTRY,
)

attestation_signs_total = Counter(
    "ai_identity_attestation_signs_total",
    "Forensic attestation sign attempts, labeled by backend and outcome.",
    ["backend", "outcome"],  # outcome: "ok" | "error" | "config_error"
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


def classify_audit_write_failure(exc: BaseException) -> str:
    """Classify an audit-write exception into a stable failure-kind label.

    Kept narrow on purpose — the cardinality of Prometheus labels has to
    stay bounded. Three buckets is enough to drive alerts and triage:

      - ``schema``    — DB schema mismatch (missing column, FK violation,
                        NOT-NULL violation). The code and DB disagree;
                        this is the 2026-04-16 incident shape.
      - ``integrity`` — HMAC chain, hash computation, or canonical-payload
                        problems. A real forensic-integrity concern —
                        either key rotation gone wrong or tampering.
      - ``unknown``   — anything else (connection, timeout, programming
                        error). Still paged; still worth investigating.
    """
    msg = str(exc).lower()
    name = type(exc).__name__.lower()
    schema_markers = (
        "undefinedcolumn",
        "undefinedtable",
        "notnullviolation",
        "foreignkeyviolation",
    )
    if any(m in name for m in schema_markers) or "does not exist" in msg or "violates" in msg:
        return "schema"
    if "hmac" in msg or "entry_hash" in msg or "prev_hash" in msg or "chain" in msg:
        return "integrity"
    return "unknown"


def record_audit_write_failure(service: str, *, kind: str = "unknown") -> None:
    """Increment the audit-write-failure counter.

    Called from the narrow ``except`` blocks that wrap
    ``create_audit_entry``. Safe to call under any concurrency model —
    prometheus_client Counters are process-safe. Never raises; an
    observability hiccup must never change the enforcement outcome.
    """
    try:
        audit_write_failures_total.labels(service=service, kind=kind).inc()
    except Exception:  # pragma: no cover — defensive
        import logging

        logging.getLogger("ai_identity.metrics").warning(
            "audit_write_failures counter increment failed", exc_info=True
        )


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
    "attestation_sign_latency_ms",
    "attestation_signs_total",
    "audit_latency_ms",
    "audit_write_failures_total",
    "classify_audit_write_failure",
    "organizations_total",
    "outbox_backlog",
    "outbox_deliveries_total",
    "record_audit_write",
    "record_audit_write_failure",
    "record_outbox_delivery",
    "refresh_db_gauges",
    "sinks_circuit_open",
    "sinks_total",
]
