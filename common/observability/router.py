"""GET /metrics — Prometheus exposition endpoint.

Unauthenticated. The endpoint is cluster-internal only — not exposed
via the Ingress, and the default-deny NetworkPolicy restricts which
pods can reach it (api/gateway ports are only open to the GCE load
balancer, internal pods, and GMP collector pods). This is the standard
k8s pattern: /metrics is safe to serve without auth because it returns
only aggregate counters (no PII, no credentials, no per-request data).

Scraped by Google Managed Prometheus via PodMonitoring resources
(k8s/pod-monitoring.yaml). Scrape interval: 30s.

The endpoint is hidden from OpenAPI docs (``include_in_schema=False``).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session  # noqa: TC002 — runtime Depends target

from common.models import get_db
from common.observability.metrics import REGISTRY, refresh_db_gauges

logger = logging.getLogger("ai_identity.api.metrics")

router = APIRouter(tags=["internal"])


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics(
    db: Session = Depends(get_db),
) -> Response:
    """Render all registered Prometheus metrics.

    Refreshes DB-backed gauges (agent/org counts, outbox backlog, sink
    health) on every scrape — a short-lived DB hit in exchange for
    operators not having to run a separate metrics-exporter sidecar.
    """
    refresh_db_gauges(db)
    body = generate_latest(REGISTRY)
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)
