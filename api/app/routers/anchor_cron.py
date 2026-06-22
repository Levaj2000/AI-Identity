"""Evidence Anchor checkpoint cron — internal endpoint.

Called by the ``evidence-anchor-checkpoint`` K8s CronJob (#408). For each org
with un-anchored ``audit_log`` rows, folds the next contiguous batch into a
signed Merkle checkpoint (see :mod:`common.forensic.anchor_service`). A single
ECDSA-P256 signature then covers the batch, and any one event's inclusion can
be proven offline against the published JWKS public key.

Idempotent: an org with nothing new to anchor is a no-op, and the unique
(org_id, first_audit_id) guard makes concurrent ticks safe. Drains up to
``max_per_org`` batches per org per tick so a backlog catches up across ticks
without an unbounded run.

Secured by the internal service key, same pattern as
``compliance_exports_cron.py``. Not exposed in public API docs.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session  # noqa: TC002 — runtime db.query

from common.config.settings import settings
from common.forensic.anchor_service import create_checkpoint
from common.forensic.signer import ForensicSignerConfigError, get_forensic_signer
from common.models import get_db
from common.models.audit_log import AuditLog

logger = logging.getLogger("ai_identity.api.anchor_cron")

router = APIRouter(prefix="/api/internal", tags=["internal"])


@router.post("/evidence-anchor/checkpoint", include_in_schema=False)
def emit_checkpoints(
    db: Annotated[Session, Depends(get_db)],
    x_internal_key: Annotated[str | None, Header(alias="x-internal-key")] = None,
    max_per_org: Annotated[
        int,
        Query(ge=1, le=1000, description="Max checkpoint batches to drain per org this tick."),
    ] = 10,
) -> dict:
    """Emit signed Merkle checkpoints for every org with un-anchored rows.

    Returns a structured summary: orgs scanned, checkpoints created, and the
    total events anchored this tick.
    """
    if not settings.internal_service_key or x_internal_key != settings.internal_service_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Resolve the signer once up front — surfaces a misconfigured key as 503
    # (matching the attestation endpoint) instead of failing per-org mid-run.
    try:
        signer = get_forensic_signer()
    except ForensicSignerConfigError as exc:
        raise HTTPException(status_code=503, detail=f"signer not configured: {exc}") from None

    org_ids = db.execute(select(AuditLog.org_id).distinct()).scalars().all()

    checkpoints_created = 0
    events_anchored = 0
    for org_id in org_ids:
        for _ in range(max_per_org):
            cp = create_checkpoint(db, org_id, signer=signer)
            if cp is None:
                break
            checkpoints_created += 1
            events_anchored += cp.tree_size

    logger.info(
        "evidence anchor checkpoint run",
        extra={
            "orgs_scanned": len(org_ids),
            "checkpoints_created": checkpoints_created,
            "events_anchored": events_anchored,
        },
    )

    return {
        "status": "ok",
        "orgs_scanned": len(org_ids),
        "checkpoints_created": checkpoints_created,
        "events_anchored": events_anchored,
    }
