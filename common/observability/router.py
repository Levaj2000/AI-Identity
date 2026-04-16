"""GET /metrics — Prometheus exposition endpoint.

Protected by ``INTERNAL_SERVICE_KEY`` via ``X-Internal-Key`` header, same
pattern as the cleanup_cron and email_cron routers. Prometheus scrape
config:

    scrape_configs:
      - job_name: ai-identity-api
        scrape_interval: 30s
        metrics_path: /metrics
        static_configs:
          - targets: ['api.ai-identity.co']
        authorization:
          credentials: $INTERNAL_SERVICE_KEY
          type: ""   # we use X-Internal-Key, not Authorization
        # Or, simpler:
        http_headers:
          X-Internal-Key:
            values: ['$INTERNAL_SERVICE_KEY']

The endpoint is hidden from OpenAPI docs (``include_in_schema=False``).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session  # noqa: TC002 — runtime Depends target

from common.config.settings import settings
from common.models import get_db
from common.observability.metrics import REGISTRY, refresh_db_gauges

logger = logging.getLogger("ai_identity.api.metrics")

router = APIRouter(tags=["internal"])


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics(
    x_internal_key: str | None = Header(None, alias="x-internal-key"),
    db: Session = Depends(get_db),
) -> Response:
    """Render all registered Prometheus metrics.

    Refreshes DB-backed gauges (agent/org counts, outbox backlog, sink
    health) on every scrape — a short-lived DB hit in exchange for
    operators not having to run a separate metrics-exporter sidecar.
    """
    if not settings.internal_service_key or x_internal_key != settings.internal_service_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    refresh_db_gauges(db)
    body = generate_latest(REGISTRY)
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)
