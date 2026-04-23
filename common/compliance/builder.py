"""Compliance export orchestrator.

Given a queued ``ComplianceExport`` row, runs it through the build
pipeline:

    queued → building → (profile builder writes artifacts)
                     → (bundle.seal signs manifest + closes ZIP)
                     → ready (or failed on any exception)

This is invoked via :func:`run_export_job` from:

- FastAPI ``BackgroundTasks`` right after POST /api/v1/exports (the
  foundation path — async-within-request is good enough until the
  real worker lands).
- Tests calling it directly — synchronous, no BackgroundTasks timing
  to deal with.

Dedicated worker (Cloud Run job / Pub/Sub) is a later concern and will
simply wrap this same function.
"""

from __future__ import annotations

import datetime
import logging
import uuid  # noqa: TC003 — used at runtime (str(job.id), etc.)
from pathlib import Path

from sqlalchemy.orm import Session  # noqa: TC002 — db.query(...) at runtime

from common.compliance.builders.eu_ai_act import build_eu_ai_act_bundle
from common.compliance.builders.placeholder import build_placeholder_bundle
from common.compliance.builders.soc2 import build_soc2_bundle
from common.compliance.bundle import ComplianceExportBundle
from common.compliance.job import (
    transition_to_building,
    transition_to_failed,
    transition_to_ready,
)
from common.config.settings import settings as default_settings
from common.forensic.signer import ForensicSignerConfigError, get_forensic_signer
from common.models import ComplianceExport

logger = logging.getLogger("ai_identity.compliance.builder")


def _archive_storage_path(export_id: uuid.UUID, archive_dir: Path) -> Path:
    """File path where the archive for ``export_id`` lives on disk."""
    return archive_dir / f"export-{export_id}.zip"


def _ensure_utc(dt: datetime.datetime) -> datetime.datetime:
    """Normalize a datetime read from the DB to a UTC-aware value.

    Production Postgres preserves tzinfo; the SQLite test engine
    strips it. Either way, the columns are stored as UTC by the
    application, so attaching UTC on read is correct and defensive.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.UTC)
    return dt.astimezone(datetime.UTC)


def run_export_job(
    db: Session,
    job_id: uuid.UUID,
    *,
    archive_dir: Path | None = None,
    now: datetime.datetime | None = None,
) -> None:
    """Build the export identified by ``job_id``.

    Loads the row, transitions it through the FSM, and writes the ZIP
    to ``archive_dir`` (defaulting to the configured compliance-export
    archive dir). Any exception is captured and turned into a
    ``failed`` state so the DB never ends up ambiguously mid-build.

    Returns ``None`` — callers read the updated row from the DB.
    """
    archive_dir = archive_dir or Path(default_settings.compliance_export_archive_dir)
    now = now or datetime.datetime.now(tz=datetime.UTC)

    job = db.query(ComplianceExport).filter(ComplianceExport.id == job_id).first()
    if job is None:
        logger.warning("run_export_job: job not found", extra={"job_id": str(job_id)})
        return

    try:
        transition_to_building(db, job)
        db.commit()

        # --- Signer -----------------------------------------------------
        # Resolve at build time so rotation just works — the API stays
        # up even while KMS creds are being updated.
        try:
            signer = get_forensic_signer()
        except ForensicSignerConfigError as exc:
            logger.exception("forensic signer misconfigured; failing export job")
            transition_to_failed(
                db,
                job,
                error_code="signer_misconfigured",
                error_message=str(exc),
                completed_at=datetime.datetime.now(tz=datetime.UTC),
            )
            db.commit()
            return

        # --- Bundle -----------------------------------------------------
        archive_path = _archive_storage_path(job.id, archive_dir)
        bundle = ComplianceExportBundle.create(archive_path, export_id=job.id)

        period_start = _ensure_utc(job.audit_period_start)
        period_end = _ensure_utc(job.audit_period_end)

        # Dispatch to the profile-specific builder. Profiles without a
        # dedicated builder yet fall back to the placeholder — which
        # still produces a fully-signed, verifiable bundle.
        if job.profile == "soc2_tsc_2017":
            build_soc2_bundle(
                bundle,
                db=db,
                org_id=job.org_id,
                export_id=job.id,
                audit_period_start=period_start,
                audit_period_end=period_end,
                built_at=now,
                agent_ids=job.agent_ids,
            )
        elif job.profile == "eu_ai_act_2024":
            build_eu_ai_act_bundle(
                bundle,
                db=db,
                org_id=job.org_id,
                export_id=job.id,
                audit_period_start=period_start,
                audit_period_end=period_end,
                built_at=now,
                agent_ids=job.agent_ids,
            )
        else:
            build_placeholder_bundle(
                bundle,
                profile=job.profile,
                org_id=job.org_id,
                export_id=job.id,
                audit_period_start=period_start,
                audit_period_end=period_end,
                built_at=now,
            )

        bundle.seal(
            profile=job.profile,
            audit_period_start=period_start,
            audit_period_end=period_end,
            built_at=now,
            org_id=job.org_id,
            signer=signer,
        )

        # --- Transition -----------------------------------------------
        # `archive_url` stays null in this foundation PR — the download
        # endpoint serves from `archive_storage_path` instead. Signed
        # GCS URLs land with the storage-backend refactor.
        transition_to_ready(
            db,
            job,
            archive_storage_path=str(bundle.archive_path),
            archive_url=None,
            archive_url_expires_at=None,
            archive_sha256=bundle.archive_sha256,
            archive_bytes=bundle.archive_bytes,
            manifest_envelope=bundle.manifest_envelope,
            completed_at=datetime.datetime.now(tz=datetime.UTC),
        )
        db.commit()

        logger.info(
            "compliance export built",
            extra={
                "job_id": str(job.id),
                "org_id": str(job.org_id),
                "profile": job.profile,
                "archive_bytes": job.archive_bytes,
            },
        )

    except Exception as exc:  # noqa: BLE001 — any build error → failed row
        db.rollback()
        # Re-fetch after rollback so we have a clean instance to update.
        job = db.query(ComplianceExport).filter(ComplianceExport.id == job_id).first()
        if job is None:
            logger.exception("run_export_job: job disappeared during failure path")
            return
        if job.status in {"ready", "failed"}:
            # Already terminal — don't clobber.
            return
        logger.exception("compliance export build failed")
        transition_to_failed(
            db,
            job,
            error_code="build_failed",
            error_message=f"{type(exc).__name__}: {exc}",
            completed_at=datetime.datetime.now(tz=datetime.UTC),
        )
        db.commit()
