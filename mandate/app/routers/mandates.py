"""Mandate CRUD — issue, list, get, revoke.

All routes require developer auth (Clerk JWT or legacy X-API-Key).
Mandate issuance signs the document at creation time; subsequent
reads return the stored signatures unchanged.
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from common.models import User, get_db
from mandate.app.auth import get_current_user
from mandate.app.database import get_db as get_mongo
from mandate.app.schemas import (
    IssueMandateRequest,
    MandateDocument,
    MandateIssuer,
    MandateListResponse,
    MandateResponse,
    MandateRevocation,
    MandateStatus,
    MandateSubject,
    RevokeMandateRequest,
)
from mandate.app.signing import sign_mandate

logger = logging.getLogger("ai_identity.mandate.router")

router = APIRouter(prefix="/api/v1/mandates", tags=["mandates"])


def _new_mandate_id() -> str:
    """Generate a human-readable mandate ID: mnd_<8 hex chars>."""
    return "mnd_" + uuid.uuid4().hex[:8]


def _doc_to_response(doc: dict) -> MandateResponse:
    doc.pop("_id", None)
    return MandateResponse(**doc)


# ── Issue ──────────────────────────────────────────────────────────────────


@router.post("", status_code=201, response_model=MandateResponse, summary="Issue a mandate")
async def issue_mandate(
    body: IssueMandateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Issue a new mandate granting the subject agent a set of scopes.

    The mandate is signed immediately at creation using ECDSA-P256-SHA256.
    The ML-DSA-87 (post-quantum) signature slot will be added at H2 PQC launch.
    """
    mongo = get_mongo()
    now = datetime.now(UTC)

    mandate = MandateDocument(
        mandate_id=_new_mandate_id(),
        schema_version="1.0",
        status=MandateStatus.active,
        issuer=MandateIssuer(
            org_id=str(current_user.org_id) if current_user.org_id else str(current_user.id),
            user_id=str(current_user.id),
        ),
        subject=MandateSubject(
            agent_id=body.subject_agent_id,
            org_id=body.subject_org_id,
        ),
        scope=body.scope,
        conditions=body.conditions,
        policy_hash=body.policy_hash,
        valid_from=body.valid_from or now,
        valid_until=body.valid_until,
        metadata=body.metadata,
        created_at=now,
        updated_at=now,
    )

    # Sign before persisting
    try:
        sig = await sign_mandate(mandate)
        mandate.signatures = [sig]
    except RuntimeError as e:
        logger.error("Mandate signing failed: %s", e)
        raise HTTPException(status_code=503, detail="Signing service unavailable") from e

    doc = mandate.model_dump(mode="json")
    await mongo["mandates"].insert_one(doc)
    logger.info(
        "Mandate issued: %s → agent=%s scope=%s",
        mandate.mandate_id,
        body.subject_agent_id,
        body.scope,
    )

    doc.pop("_id", None)
    return MandateResponse(**doc)


# ── List ───────────────────────────────────────────────────────────────────


@router.get("", response_model=MandateListResponse, summary="List mandates")
async def list_mandates(
    agent_id: str | None = Query(None, description="Filter by subject agent_id"),
    status: MandateStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mongo = get_mongo()
    org_id = str(current_user.org_id) if current_user.org_id else str(current_user.id)

    filt: dict = {"issuer.org_id": org_id}
    if agent_id:
        filt["subject.agent_id"] = agent_id
    if status:
        filt["status"] = status.value

    total = await mongo["mandates"].count_documents(filt)
    cursor = (
        mongo["mandates"]
        .find(filt, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    docs = await cursor.to_list(length=page_size)
    return MandateListResponse(
        mandates=[MandateResponse(**d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Get ────────────────────────────────────────────────────────────────────


@router.get("/{mandate_id}", response_model=MandateResponse, summary="Get a mandate")
async def get_mandate(
    mandate_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mongo = get_mongo()
    org_id = str(current_user.org_id) if current_user.org_id else str(current_user.id)
    doc = await mongo["mandates"].find_one(
        {"mandate_id": mandate_id, "issuer.org_id": org_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Mandate not found")
    return MandateResponse(**doc)


# ── Revoke ─────────────────────────────────────────────────────────────────


@router.post("/{mandate_id}/revoke", response_model=MandateResponse, summary="Revoke a mandate")
async def revoke_mandate(
    mandate_id: str,
    body: RevokeMandateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mongo = get_mongo()
    org_id = str(current_user.org_id) if current_user.org_id else str(current_user.id)
    now = datetime.now(UTC)

    doc = await mongo["mandates"].find_one(
        {"mandate_id": mandate_id, "issuer.org_id": org_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Mandate not found")
    if doc["status"] != MandateStatus.active.value:
        raise HTTPException(status_code=409, detail=f"Mandate is already {doc['status']}")

    revocation = MandateRevocation(
        revoked_at=now,
        revoked_by=str(current_user.id),
        reason=body.reason,
    )

    await mongo["mandates"].update_one(
        {"mandate_id": mandate_id},
        {
            "$set": {
                "status": MandateStatus.revoked.value,
                "revocation": revocation.model_dump(mode="json"),
                "updated_at": now.isoformat(),
            }
        },
    )

    # Append to the immutable event log
    await mongo["mandate_events"].insert_one(
        {
            "mandate_id": mandate_id,
            "event_type": "revoked",
            "event_at": now.isoformat(),
            "actor": str(current_user.id),
            "reason": body.reason,
        }
    )

    updated = await mongo["mandates"].find_one({"mandate_id": mandate_id}, {"_id": 0})
    return MandateResponse(**updated)
