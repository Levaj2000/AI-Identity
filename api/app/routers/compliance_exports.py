"""Compliance export API — stub (#273).

This module ships the contract for Milestone #34's compliance export
pipeline. The endpoints are wired, the schemas are authoritative, and
OpenAPI picks everything up — but the builder itself is not yet
implemented. Every write-side endpoint returns 501 Not Implemented
with a stable error code so downstream consumers can integrate
against the real response shape today.

Design reference: ``docs/ADR-002-compliance-exports.md``.
Scoping doc: ``docs/compliance/export-profiles.md``.

What this stub does today:

* Validates the POST request body against the real Pydantic schema —
  bad profile / bad date range / mixed-tenant agent_ids fail fast with
  proper 400s, **not** 501. Clients can write their own validation
  tests against the stub.
* Enforces authZ (org owner/admin, or platform admin) — a non-admin
  caller gets 403 before the 501.
* Returns a 501 with a documented ``error_code`` on the actual build
  request.
* Returns a 404-not-403 on cross-tenant GETs, matching #264.

What it does NOT do yet:

* No ``compliance_exports`` table. GET/list both 501 since there's
  nowhere to read from.
* No worker, no archive build, no GCS signed URLs.
* No rate limiting (the ADR's 5-concurrent / 20-per-day caps land
  with the builder).

Implementation follow-on is a separate sprint item tracked under
Milestone #34.
"""

from __future__ import annotations

import logging
import uuid  # noqa: TC003 — used at runtime by Pydantic model fields
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session  # noqa: TC002 — runtime Depends target

from api.app.auth import get_current_user
from common.models import Agent, OrgMembership, User, get_db
from common.schemas.compliance_export import (
    ExportCreateRequest,
    ExportListResponse,
    ExportResponse,
)

logger = logging.getLogger("ai_identity.api.compliance_exports")

router = APIRouter(prefix="/api/v1/exports", tags=["compliance.exports"])


# ── AuthZ helper ─────────────────────────────────────────────────────


def _assert_org_admin(db: Session, user: User, org_id: uuid.UUID) -> None:
    """Raise 403 unless the caller is an owner/admin of ``org_id``.

    Mirrors the predicate used by the attestation sign endpoint
    (``api/app/routers/attestations.py::_assert_org_admin``). Export
    creation is a destructive administrative action in the same sense
    — it produces a permanent, signed record of an org's activity —
    so we gate it the same way.
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

    The export API is intentionally not self-declaring on ``org_id`` —
    preserves the "caller cannot export across orgs" invariant from
    #263. Callers with multiple memberships get their primary org
    (``user.org_id``). Platform admins without an org get a 400 —
    they must use an admin-scoped call shape that isn't part of v1.
    """
    if user.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "caller has no primary org; platform admins must specify "
                "a target org (not supported in v1 stub)"
            ),
        )
    return user.org_id


def _verify_agent_ids_belong_to_org(
    db: Session, agent_ids: list[uuid.UUID] | None, org_id: uuid.UUID
) -> None:
    """Reject any agent id that belongs to a different org.

    Cross-tenant leakage guard. Same discipline as the attestation
    sign endpoint's cross-org range check (#263). Runs before we issue
    a 501 on the build itself so clients get a fast, specific 400 for
    this particular misuse pattern.
    """
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


# ── Stub responses ───────────────────────────────────────────────────


_STUB_ERROR_CODE = "export_builder_not_implemented"
_STUB_MESSAGE = (
    "The compliance export builder is scoped (#273 ADR) but not yet "
    "implemented. This endpoint will return 202 Accepted once the "
    "builder lands in the follow-on sprint. See "
    "docs/ADR-002-compliance-exports.md for the full contract."
)


def _stub_501(extra: dict | None = None) -> JSONResponse:
    """Build the standard 501 body.

    Matches the application-wide error envelope (see
    ``api/app/main.py::http_exception_handler``) so clients handling
    errors generically don't need a special case for this endpoint.
    """
    body = {
        "error": {
            "code": _STUB_ERROR_CODE,
            "message": _STUB_MESSAGE,
        }
    }
    if extra:
        body["error"].update(extra)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=body,
    )


# ── Endpoints ────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a compliance export job (stub — returns 501)",
    responses={
        202: {"description": "Export job accepted (once the builder lands)."},
        400: {"description": "Validation error (bad profile, period, or agent_ids)."},
        403: {"description": "Caller is not an org owner/admin."},
        501: {
            "description": (
                f"Builder not yet implemented. Body includes error.code == '{_STUB_ERROR_CODE}'."
            )
        },
    },
)
def create_export(
    body: ExportCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    """Create an asynchronous export build.

    This endpoint is a stub: request validation + authZ + tenancy
    checks run, but the final step returns 501. Use it to integrate
    against the contract today and flip to a live build once the
    follow-on sprint ships.
    """
    org_id = _caller_org_id(db, user)
    _assert_org_admin(db, user, org_id)
    _verify_agent_ids_belong_to_org(db, body.agent_ids, org_id)

    logger.info(
        "compliance export stub hit",
        extra={
            "org_id": str(org_id),
            "profile": body.profile.value,
            "period_days": (body.audit_period_end - body.audit_period_start).days,
            "agent_ids_count": len(body.agent_ids) if body.agent_ids else 0,
        },
    )

    return _stub_501(
        extra={
            "profile": body.profile.value,
            "org_id": str(org_id),
        }
    )


@router.get(
    "/{export_id}",
    response_model=ExportResponse,
    summary="Fetch a compliance export job (stub — returns 501)",
    responses={
        200: {"description": "Export job (once the builder lands and persistence exists)."},
        403: {"description": "Reserved — collapses into 404 today to avoid leaking tenancy."},
        404: {"description": "Export id not found, or belongs to another org."},
        501: {
            "description": (
                "Persistence not yet implemented. Body includes "
                f"error.code == '{_STUB_ERROR_CODE}'."
            )
        },
    },
)
def get_export(
    export_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    """Retrieve an export job by id.

    Stub — there is no ``compliance_exports`` table yet, so there are
    no rows to return. Returns 501 unconditionally for authorized
    callers. Once the table lands, the 501 is replaced by the real
    lookup and the 404-not-403 tenancy discipline from #264.
    """
    # Enforce auth eagerly so the stub mirrors real endpoint behavior
    # (authorized callers get 501; unauthenticated get 401 from the
    # dependency).
    _ = _caller_org_id(db, user)
    return _stub_501(extra={"export_id": str(export_id)})


@router.get(
    "",
    response_model=ExportListResponse,
    summary="List compliance exports (stub — returns 501)",
    responses={
        200: {"description": "List of export jobs (once persistence lands)."},
        501: {
            "description": (
                "Persistence not yet implemented. Body includes "
                f"error.code == '{_STUB_ERROR_CODE}'."
            )
        },
    },
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
        description="Opaque pagination cursor from a previous response.",
    ),
) -> JSONResponse:
    """List the caller's org's export jobs.

    Stub — see :func:`get_export` for the reasoning.
    """
    _ = _caller_org_id(db, user)
    return _stub_501(
        extra={
            "filter": {
                "profile": profile,
                "status": statuses,
                "limit": limit,
                "before": before,
            }
        }
    )
