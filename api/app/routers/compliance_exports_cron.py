"""Compliance-export retention cron — internal endpoint.

Called by the ``compliance-export-cleanup`` K8s CronJob per ADR-002's
30-day retention default. Finds ``ready`` export jobs whose
``completed_at`` is older than the retention window, deletes their
on-disk archive file, and nulls out the storage pointer so the
download endpoint returns 404 ("archive expired; request a new
export").

Source-of-truth evidence (audit_log, attestations, policy rows) is
untouched — only the archive bundle is GC'd. A client can always
re-request a build from the same period to regenerate a fresh
archive.

Secured by the internal service key, same pattern as
``cleanup_cron.py``. Not exposed in public API docs.
"""

from __future__ import annotations

import datetime
import logging
from datetime import timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session  # noqa: TC002 — runtime db.query

from common.compliance.job import READY
from common.config.settings import settings
from common.models import ComplianceExport, get_db

logger = logging.getLogger("ai_identity.api.compliance_exports_cron")

router = APIRouter(prefix="/api/internal", tags=["internal"])


@router.post("/compliance-exports/cleanup", include_in_schema=False)
def cleanup_expired_exports(
    db: Annotated[Session, Depends(get_db)],
    x_internal_key: Annotated[str | None, Header(alias="x-internal-key")] = None,
    retention_days: Annotated[
        int | None,
        Query(
            ge=1,
            le=3650,
            description=(
                "Override the configured retention window. Default is "
                "compliance_export_retention_days from settings."
            ),
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        Query(description="Preview targets without deleting any files."),
    ] = True,
) -> dict:
    """GC compliance-export archives past the retention window.

    Returns a structured summary: ``candidates``, ``archives_deleted``,
    ``rows_updated``, and (on dry runs) the list of target export ids
    so an operator can inspect before enabling the real run.
    """
    if not settings.internal_service_key or x_internal_key != settings.internal_service_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    window_days = retention_days or settings.compliance_export_retention_days
    cutoff = datetime.datetime.now(tz=datetime.UTC) - timedelta(days=window_days)

    # Candidates: ready jobs older than cutoff that still point at a
    # file on disk. Skip rows whose storage_path was already cleared
    # (idempotency — the cron can safely re-run).
    candidates = (
        db.query(ComplianceExport)
        .filter(
            ComplianceExport.status == READY,
            ComplianceExport.completed_at.isnot(None),
            ComplianceExport.completed_at <= cutoff,
            ComplianceExport.archive_storage_path.isnot(None),
        )
        .order_by(ComplianceExport.completed_at.asc())
        .all()
    )

    if dry_run:
        return {
            "status": "dry_run",
            "retention_days": window_days,
            "cutoff": cutoff.isoformat(),
            "candidates": len(candidates),
            "candidate_ids": [str(c.id) for c in candidates],
            "archives_deleted": 0,
            "rows_updated": 0,
        }

    archives_deleted = 0
    rows_updated = 0
    for export in candidates:
        path = Path(export.archive_storage_path)
        try:
            if path.exists():
                path.unlink()
                archives_deleted += 1
        except OSError:
            # Log and move on — an individual file we can't delete
            # shouldn't stop the rest of the batch. The cron will
            # retry tomorrow; if it persists, an operator sees it.
            logger.exception(
                "failed to delete archive; skipping row update",
                extra={"export_id": str(export.id), "path": str(path)},
            )
            continue

        # Null out the storage pointer so the download endpoint returns
        # a clean "archive expired; request a new export" 404. We leave
        # the row itself (with its DSSE manifest_envelope) intact so
        # audit history of what was signed and when survives retention.
        export.archive_storage_path = None
        export.archive_url = None
        export.archive_url_expires_at = None
        rows_updated += 1

    db.commit()

    logger.info(
        "compliance export retention cleanup",
        extra={
            "retention_days": window_days,
            "candidates": len(candidates),
            "archives_deleted": archives_deleted,
            "rows_updated": rows_updated,
        },
    )

    return {
        "status": "ok",
        "retention_days": window_days,
        "cutoff": cutoff.isoformat(),
        "candidates": len(candidates),
        "archives_deleted": archives_deleted,
        "rows_updated": rows_updated,
    }
