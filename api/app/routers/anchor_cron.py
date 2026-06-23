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
from sqlalchemy import func, select
from sqlalchemy.orm import Session  # noqa: TC002 — runtime db.query

from common.config.settings import settings
from common.forensic.anchor_service import create_checkpoint
from common.forensic.signer import ForensicSignerConfigError, get_forensic_signer
from common.models import get_db
from common.models.audit_checkpoint import AuditCheckpoint
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

    Returns a structured summary: orgs with a backlog (those actually
    processed), checkpoints created, and the total events anchored this tick.
    """
    if not settings.internal_service_key or x_internal_key != settings.internal_service_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Resolve the signer once up front — surfaces a misconfigured key as 503
    # (matching the attestation endpoint) instead of failing per-org mid-run.
    try:
        signer = get_forensic_signer()
    except ForensicSignerConfigError as exc:
        raise HTTPException(status_code=503, detail=f"signer not configured: {exc}") from None

    # Select only orgs that actually have un-anchored rows, in one set-based
    # query, instead of `SELECT DISTINCT org_id` over all of audit_log followed
    # by a per-org probe. For each org we compare its highest audit_log.id
    # against its checkpoint high-water mark (max(last_audit_id)) and keep only
    # those where audit_log is ahead — so idle orgs are never visited and never
    # spend create_checkpoint's max()-lookup + un-anchored fetch. The query also
    # hands back each org's high-water mark, threaded straight into
    # create_checkpoint as ``after_id`` so the drain skips that lookup too.
    hwm = (
        select(
            AuditCheckpoint.org_id.label("org_id"),
            func.max(AuditCheckpoint.last_audit_id).label("last_audit_id"),
        )
        .group_by(AuditCheckpoint.org_id)
        .subquery()
    )
    candidates = db.execute(
        select(
            AuditLog.org_id,
            func.coalesce(hwm.c.last_audit_id, 0),
        )
        .outerjoin(hwm, hwm.c.org_id == AuditLog.org_id)
        .group_by(AuditLog.org_id, hwm.c.last_audit_id)
        .having(func.max(AuditLog.id) > func.coalesce(hwm.c.last_audit_id, 0))
    ).all()

    checkpoints_created = 0
    events_anchored = 0
    for org_id, last_anchored_id in candidates:
        # Seed the drain with the high-water mark from the candidate query, then
        # thread each new checkpoint's last_audit_id forward. So the max()-lookup
        # is never run separately — not once per batch (the N+1 Sentry flagged)
        # and not even once per org; the candidate query already resolved it.
        after_id = last_anchored_id
        for _ in range(max_per_org):
            cp = create_checkpoint(db, org_id, signer=signer, after_id=after_id)
            if cp is None:
                break
            after_id = cp.last_audit_id
            checkpoints_created += 1
            events_anchored += cp.tree_size

    logger.info(
        "evidence anchor checkpoint run",
        extra={
            "orgs_with_backlog": len(candidates),
            "checkpoints_created": checkpoints_created,
            "events_anchored": events_anchored,
        },
    )

    return {
        "status": "ok",
        "orgs_with_backlog": len(candidates),
        "checkpoints_created": checkpoints_created,
        "events_anchored": events_anchored,
    }
