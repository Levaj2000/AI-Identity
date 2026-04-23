"""Compliance export API.

Async job-based export per ADR-002. ``POST /api/v1/exports`` queues a
build, the background builder turns it into a signed, hash-committed
ZIP, and ``GET /api/v1/exports/{id}`` polls status until
``status == "ready"``. An authenticated ``GET
/api/v1/exports/{id}/download`` streams the archive bytes.

Design reference: ``docs/ADR-002-compliance-exports.md``.
Scoping doc: ``docs/compliance/export-profiles.md``.

This replaces the #273 stub — every endpoint now does real work
against ``compliance_exports``. The profile builders themselves are
still placeholders (foundation PR) so the archive contents are
intentionally minimal; that's #3/#4/#5 in the milestone breakdown.
"""

from __future__ import annotations

import datetime
import logging
import uuid  # noqa: TC003 — FastAPI resolves path param annotations at runtime
from datetime import timedelta
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session  # noqa: TC002 — FastAPI Depends target

from api.app.auth import get_current_user
from common.compliance.agent_ids_hash import agent_ids_hash
from common.compliance.builder import run_export_job
from common.compliance.job import BUILDING, QUEUED
from common.config.settings import settings as default_settings
from common.models import (
    Agent,
    ComplianceExport,
    OrgMembership,
    SessionLocal,
    User,
    get_db,
)
from common.schemas.compliance_export import (
    ExportCreateRequest,
    ExportListResponse,
    ExportResponse,
    ExportStatus,
)

logger = logging.getLogger("ai_identity.api.compliance_exports")

router = APIRouter(prefix="/api/v1/exports", tags=["compliance.exports"])


# ── AuthZ helpers ────────────────────────────────────────────────────


def _assert_org_admin(db: Session, user: User, org_id: uuid.UUID) -> None:
    """Raise 403 unless the caller is an owner/admin of ``org_id``.

    Mirrors the predicate used by the attestation sign endpoint. Export
    creation is a destructive administrative action — it produces a
    permanent, signed record of an org's activity — so we gate it the
    same way.
    """
    if user.role == "admin":
        return
    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == user.id,
            OrgMembership.role.in_(("owner", "admin")),
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="org membership required to create compliance exports",
        )


def _caller_org_id(db: Session, user: User) -> uuid.UUID:
    """Resolve the org the caller is acting as.

    Preserves the "caller cannot export across orgs" invariant from
    #263. Platform admins without a primary org get a 400 — they must
    use an admin-scoped call shape that isn't part of v1.
    """
    if user.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "caller has no primary org; platform admins must specify "
                "a target org (not supported in v1)"
            ),
        )
    return user.org_id


def _verify_agent_ids_belong_to_org(
    db: Session, agent_ids: list[uuid.UUID] | None, org_id: uuid.UUID
) -> None:
    """Reject any agent id that belongs to a different org."""
    if not agent_ids:
        return
    rows = db.query(Agent.id, Agent.org_id).filter(Agent.id.in_(agent_ids)).all()
    found_ids = {row[0] for row in rows}
    missing = [aid for aid in agent_ids if aid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"agent_ids not found: {missing}",
        )
    foreign = [row[0] for row in rows if row[1] != org_id]
    if foreign:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{len(foreign)} agent_ids belong to a different org; "
                "refusing to create a mixed-tenant export"
            ),
        )


# ── Rate limits (ADR-002 cost guardrails) ────────────────────────────


def _enforce_rate_limits(db: Session, org_id: uuid.UUID) -> JSONResponse | None:
    """Enforce the ADR-002 per-org cost guardrails.

    Two separate limits are checked:

    1. **Max concurrent builds** — count of jobs currently in ``queued``
       or ``building`` state. Protects the worker pool from a single
       org starving everyone else.
    2. **Max exports per rolling 24 hours** — count of jobs created in
       the last 24 hours regardless of terminal state. Protects
       storage + KMS sign volume from an abusive-or-misconfigured
       retry loop.

    Returns ``None`` when the request is allowed. Returns a 429
    ``JSONResponse`` with a structured ``error.code`` and
    ``Retry-After`` header when one of the limits is breached — the
    caller short-circuits and returns that response directly.
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    window_start = now - timedelta(hours=24)

    concurrent = (
        db.query(ComplianceExport)
        .filter(
            ComplianceExport.org_id == org_id,
            ComplianceExport.status.in_((QUEUED, BUILDING)),
        )
        .count()
    )
    if concurrent >= default_settings.compliance_export_max_concurrent_per_org:
        # Concurrent limit — retry in a few minutes once current
        # builds drain. 60 seconds is a reasonable hint; real wait
        # depends on bundle size.
        return _rate_limit_response(
            code="rate_limit_exceeded_concurrent",
            message=(
                "Too many concurrent export builds for this org; wait "
                "for one to finish before queueing another."
            ),
            limit=default_settings.compliance_export_max_concurrent_per_org,
            observed=concurrent,
            retry_after_seconds=60,
        )

    daily = (
        db.query(ComplianceExport)
        .filter(
            ComplianceExport.org_id == org_id,
            ComplianceExport.created_at >= window_start,
        )
        .count()
    )
    if daily >= default_settings.compliance_export_max_per_day_per_org:
        # Daily limit — retry on a window-rolling basis. The Retry-After
        # is a conservative estimate: time until the oldest request in
        # the window ages out.
        oldest = (
            db.query(ComplianceExport)
            .filter(
                ComplianceExport.org_id == org_id,
                ComplianceExport.created_at >= window_start,
            )
            .order_by(ComplianceExport.created_at.asc())
            .first()
        )
        retry_after = 3600  # 1h default fallback
        if oldest is not None:
            oldest_created = oldest.created_at
            if oldest_created.tzinfo is None:
                oldest_created = oldest_created.replace(tzinfo=datetime.UTC)
            seconds_until_rolls_off = int(
                (oldest_created + timedelta(hours=24) - now).total_seconds()
            )
            retry_after = max(60, min(seconds_until_rolls_off, 86400))
        return _rate_limit_response(
            code="rate_limit_exceeded_daily",
            message=(
                "Daily export quota for this org exhausted; wait for "
                "the 24-hour rolling window to advance."
            ),
            limit=default_settings.compliance_export_max_per_day_per_org,
            observed=daily,
            retry_after_seconds=retry_after,
        )

    return None


def _rate_limit_response(
    *,
    code: str,
    message: str,
    limit: int,
    observed: int,
    retry_after_seconds: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": {
                "code": code,
                "message": message,
                "limit": limit,
                "observed": observed,
            }
        },
        headers={"Retry-After": str(retry_after_seconds)},
    )


# ── Row → response ───────────────────────────────────────────────────


def _to_response(job: ComplianceExport) -> ExportResponse:
    """Map a ``ComplianceExport`` row to the API response shape."""
    error = None
    if job.status == "failed" and job.error_code is not None:
        from common.schemas.compliance_export import ExportError

        error = ExportError(
            code=job.error_code,
            message=job.error_message or "",
        )
    return ExportResponse(
        id=job.id,
        org_id=job.org_id,
        requested_by=job.requested_by,
        profile=job.profile,
        audit_period_start=job.audit_period_start,
        audit_period_end=job.audit_period_end,
        agent_ids=job.agent_ids,
        status=ExportStatus(job.status),
        progress_pct=job.progress_pct,
        archive_url=job.archive_url,
        archive_url_expires_at=job.archive_url_expires_at,
        archive_sha256=job.archive_sha256,
        archive_bytes=job.archive_bytes,
        manifest_envelope=job.manifest_envelope,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error=error,
    )


# ── Background task wrapper ──────────────────────────────────────────


# Module-level session factory — tests override this to point at
# their in-memory SQLite sessionmaker. Production is SessionLocal.
_background_session_factory = SessionLocal


def _run_job_in_background(job_id: uuid.UUID) -> None:
    """Open a fresh session for the background builder.

    The request-scoped session from ``get_db`` is closed by the time
    BackgroundTasks runs, so we open our own. Running this in the
    request thread is fine for the foundation — the placeholder
    builder finishes in milliseconds. Real profile builders will move
    to a Cloud Run job + Pub/Sub per ADR-002.
    """
    db = _background_session_factory()
    try:
        run_export_job(db, job_id)
    finally:
        db.close()


# ── Endpoints ────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a compliance export job",
    responses={
        202: {"description": "Export job accepted. Poll GET /exports/{id} for status."},
        400: {"description": "Validation error (bad profile, period, or agent_ids)."},
        403: {"description": "Caller is not an org owner/admin."},
        409: {
            "description": (
                "An export for the same (profile, period, agent_ids) is already "
                "in-flight for this org. Body contains the existing job."
            )
        },
        429: {
            "description": (
                "Rate limit: max concurrent builds or daily quota hit. "
                "Retry-After header carries the recommended cooldown."
            )
        },
    },
)
def create_export(
    body: ExportCreateRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExportResponse:
    """Queue an async export build.

    Returns 202 immediately with the queued job. The background builder
    transitions it to ``building`` then to ``ready`` (or ``failed``).
    Clients poll ``GET /exports/{id}`` to observe the state change.
    """
    org_id = _caller_org_id(db, user)
    _assert_org_admin(db, user, org_id)
    _verify_agent_ids_belong_to_org(db, body.agent_ids, org_id)

    # Cost guardrails before touching the DB with a new row. Order
    # matters — 409 idempotency runs after so a caller legitimately
    # re-checking a queued job doesn't get a misleading 429.
    rate_limit_response = _enforce_rate_limits(db, org_id)
    if rate_limit_response is not None:
        return rate_limit_response

    ids_hash = agent_ids_hash(body.agent_ids)

    # Idempotency: if a queued/building job for this exact scope already
    # exists, return it with 409. Matches the ADR's "don't build the
    # same thing twice" discipline; the client can choose to poll or
    # cancel-and-retry.
    existing = (
        db.query(ComplianceExport)
        .filter(
            ComplianceExport.org_id == org_id,
            ComplianceExport.profile == body.profile.value,
            ComplianceExport.audit_period_start == body.audit_period_start,
            ComplianceExport.audit_period_end == body.audit_period_end,
            ComplianceExport.agent_ids_hash == ids_hash,
            ComplianceExport.status.in_((QUEUED, BUILDING)),
        )
        .first()
    )
    if existing is not None:
        # Return JSONResponse directly — the app-wide HTTPException
        # handler flattens structured details into a generic envelope,
        # which would clobber the structured error code the client
        # relies on.
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "export_already_inflight",
                    "message": "An export for the same scope is already queued or building.",
                    "existing_export_id": str(existing.id),
                }
            },
        )

    job = ComplianceExport(
        org_id=org_id,
        requested_by=user.id,
        profile=body.profile.value,
        audit_period_start=body.audit_period_start,
        audit_period_end=body.audit_period_end,
        agent_ids=body.agent_ids,
        agent_ids_hash=ids_hash,
        status=QUEUED,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_job_in_background, job.id)

    logger.info(
        "compliance export queued",
        extra={
            "job_id": str(job.id),
            "org_id": str(org_id),
            "profile": job.profile,
            "period_days": (job.audit_period_end - job.audit_period_start).days,
            "agent_ids_count": len(body.agent_ids) if body.agent_ids else 0,
        },
    )

    return _to_response(job)


@router.get(
    "/{export_id}",
    response_model=ExportResponse,
    summary="Fetch a compliance export job",
    responses={
        200: {"description": "Current job state."},
        404: {
            "description": (
                "Export id not found, or belongs to another org (404-not-403 "
                "by the tenancy discipline from #264)."
            )
        },
    },
)
def get_export(
    export_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExportResponse:
    """Retrieve a single export job by id."""
    org_id = _caller_org_id(db, user)
    job = (
        db.query(ComplianceExport)
        .filter(
            ComplianceExport.id == export_id,
            ComplianceExport.org_id == org_id,
        )
        .first()
    )
    # Platform admins may fetch across orgs; everyone else gets 404.
    if job is None and user.role == "admin":
        job = db.query(ComplianceExport).filter(ComplianceExport.id == export_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="export not found",
        )
    return _to_response(job)


@router.post(
    "/{export_id}/cancel",
    response_model=ExportResponse,
    summary="Cancel a queued or building export job",
    responses={
        200: {"description": "Job transitioned to failed with error_code=cancelled."},
        403: {"description": "Caller is not an org owner/admin."},
        404: {"description": "Export id not found or belongs to another org."},
        409: {
            "description": (
                "Job is already in a terminal state (ready/failed); nothing to "
                "cancel. Body includes error.code == 'export_not_cancellable'."
            )
        },
    },
)
def cancel_export(
    export_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExportResponse | JSONResponse:
    """Cancel an in-flight export.

    Transitions the job to ``failed`` with ``error_code=cancelled``.
    The main use case today is unblocking the scope-idempotency
    guard when a previous pod was killed mid-build and left the job
    orphaned; the 10-minute lifespan reaper (#284) will eventually
    catch these, but a user-driven cancel is faster.

    AuthZ matches create: caller must be an org owner/admin for the
    owning org (or a platform admin). Same 404-not-403 tenancy
    discipline as ``GET /exports/{id}``.
    """
    org_id = _caller_org_id(db, user)
    _assert_org_admin(db, user, org_id)

    job = (
        db.query(ComplianceExport)
        .filter(
            ComplianceExport.id == export_id,
            ComplianceExport.org_id == org_id,
        )
        .first()
    )
    # Platform admins can cancel across orgs to unstick customer support.
    if job is None and user.role == "admin":
        job = db.query(ComplianceExport).filter(ComplianceExport.id == export_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="export not found",
        )

    if job.status not in (QUEUED, BUILDING):
        # Can't cancel a job that's already terminal. Structured
        # JSONResponse (not HTTPException) so the stable error code
        # reaches the client — the app-wide handler flattens details.
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "export_not_cancellable",
                    "message": (
                        f"Job is in {job.status!r}; only queued/building jobs can be cancelled."
                    ),
                    "current_status": job.status,
                }
            },
        )

    now = datetime.datetime.now(tz=datetime.UTC)
    job.status = "failed"
    job.error_code = "cancelled"
    job.error_message = f"Cancelled by user {user.id} at {now.isoformat()}."
    job.completed_at = now
    db.commit()
    db.refresh(job)

    logger.info(
        "compliance export cancelled",
        extra={
            "job_id": str(job.id),
            "org_id": str(job.org_id),
            "cancelled_by": str(user.id),
        },
    )
    return _to_response(job)


@router.get(
    "/{export_id}/download",
    summary="Download a completed export archive",
    responses={
        200: {
            "description": (
                "ZIP archive bytes. Same signed manifest as referenced in "
                "GET /exports/{id} (``manifest_envelope``)."
            ),
            "content": {"application/zip": {}},
        },
        404: {"description": "Export not found, wrong org, or not ready yet."},
        409: {"description": "Export is not in ready state."},
    },
)
def download_export(
    export_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Stream the archive ZIP to an authorized caller.

    Foundation PR ships direct file serving from local disk. The GCS
    signed-URL path lands with the storage-backend refactor — at that
    point ``archive_url`` on the job becomes the primary download
    surface and this endpoint becomes a fallback.
    """
    org_id = _caller_org_id(db, user)
    job = (
        db.query(ComplianceExport)
        .filter(
            ComplianceExport.id == export_id,
            ComplianceExport.org_id == org_id,
        )
        .first()
    )
    if job is None and user.role == "admin":
        job = db.query(ComplianceExport).filter(ComplianceExport.id == export_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="export not found",
        )
    if job.status != "ready":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "export_not_ready",
                    "message": f"export is in {job.status!r} state; no archive to download",
                }
            },
        )
    if not job.archive_storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="archive not found on disk",
        )
    archive_path = Path(job.archive_storage_path)
    if not archive_path.exists():
        # Archive was garbage-collected past retention, or storage
        # moved — tell the client to re-request a build rather than
        # 500ing on a stale pointer.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="archive expired; request a new export",
        )
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"export-{job.id}.zip",
    )


@router.get(
    "",
    response_model=ExportListResponse,
    summary="List compliance exports",
)
def list_exports(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    profile: str | None = Query(None, description="Filter by profile identifier."),
    statuses: str | None = Query(
        None,
        alias="status",
        description="Filter by status.",
    ),
    limit: int = Query(20, ge=1, le=100),
    before: str | None = Query(
        None,
        description="ISO-8601 created_at cursor from a previous response.",
    ),
) -> ExportListResponse:
    """List the caller's org's export jobs, newest first.

    Cursor-based pagination on ``created_at`` — stable even under
    concurrent inserts because export jobs are never updated after
    creation except for status transitions (which don't move the
    ordering column).
    """
    org_id = _caller_org_id(db, user)
    query = db.query(ComplianceExport).filter(ComplianceExport.org_id == org_id)
    if profile:
        query = query.filter(ComplianceExport.profile == profile)
    if statuses:
        query = query.filter(ComplianceExport.status == statuses)
    if before:
        try:
            cursor_dt = datetime.datetime.fromisoformat(before)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid 'before' cursor: {exc}",
            ) from exc
        query = query.filter(ComplianceExport.created_at < cursor_dt)

    # Fetch one extra to decide whether there's a next cursor without a
    # second COUNT query.
    rows = query.order_by(ComplianceExport.created_at.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    items = [_to_response(r) for r in rows[:limit]]
    next_cursor = rows[limit - 1].created_at.isoformat() if has_more else None
    return ExportListResponse(items=items, next_cursor=next_cursor)
