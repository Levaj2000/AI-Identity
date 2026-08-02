"""GET /metrics — Prometheus exposition endpoint.

Unauthenticated. The endpoint is cluster-internal only — not exposed
via the Ingress, and the default-deny NetworkPolicy restricts which
pods can reach it (api/gateway ports are only open to the GCE load
balancer, internal pods, and GMP collector pods). This is the standard
k8s pattern: /metrics is safe to serve without auth because it returns
only aggregate counters (no PII, no credentials, no per-request data).

Scraped by Google Managed Prometheus via PodMonitoring resources
(k8s/pod-monitoring.yaml). Scrape interval: 30s.

DB-backed gauges are refreshed at most once per epoch-aligned
``settings.metrics_db_gauge_ttl_seconds`` window (default 15 min), NOT
on every scrape. Neon suspends its compute after ~5 idle minutes; a DB
query resets that timer, so refreshing on a 30s scrape interval would
keep the compute awake 24/7 (~$83/mo of idle uptime — the exact bug the
/health vs /health/deep split fixed for probes). Counters and
histograms are in-process and always current; only the gauge refresh
is throttled.

The endpoint is hidden from OpenAPI docs (``include_in_schema=False``).
"""

from __future__ import annotations

import logging
import threading
import time

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session  # noqa: TC002 — runtime Depends target

from common.config.settings import settings
from common.models import get_db
from common.observability.metrics import REGISTRY, refresh_db_gauges

logger = logging.getLogger("ai_identity.api.metrics")

router = APIRouter(tags=["internal"])

# Refresh throttle state. Refreshes are bucketed by *wall-clock* window
# (epoch time // TTL), not per-process age: with 2 gunicorn workers × 2
# pods × 2 services there are 8 independent processes, and monotonic
# per-process windows drift apart until their staggered refreshes keep
# Neon awake continuously anyway. Epoch-aligned 900s windows open
# exactly at :00/:15/:30/:45 — the same instants the */15
# evidence-anchor cron already wakes the compute — so every process
# refreshes inside the already-awake window and the whole fleet goes
# quiet together. The window is recorded when a refresh *attempt*
# starts — success or failure — so a down/cold DB is probed once per
# window, not hammered every 30s scrape.
_gauge_refresh_lock = threading.Lock()
_last_gauge_refresh_window: int | None = None


def reset_db_gauge_cache() -> None:
    """Force the next scrape to refresh DB-backed gauges (test hook)."""
    global _last_gauge_refresh_window
    _last_gauge_refresh_window = None


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics(
    db: Session = Depends(get_db),
) -> Response:
    """Render all registered Prometheus metrics.

    DB-backed gauges (agent/org counts, outbox backlog, sink health)
    refresh at most once per wall-clock TTL window; between refreshes,
    scrapes serve the last-known gauge values without touching the
    database. The injected session is lazy — SQLAlchemy opens no
    connection unless ``refresh_db_gauges`` actually runs, which also
    keeps the steady-state scrape free of connection-acquisition
    latency.
    """
    global _last_gauge_refresh_window
    window = int(time.time() // settings.metrics_db_gauge_ttl_seconds)
    # Non-blocking lock: under a scrape burst, one caller refreshes and
    # the rest serve the cached values immediately.
    if window != _last_gauge_refresh_window and _gauge_refresh_lock.acquire(blocking=False):
        try:
            _last_gauge_refresh_window = window
            refresh_db_gauges(db)
        finally:
            _gauge_refresh_lock.release()
    body = generate_latest(REGISTRY)
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)
