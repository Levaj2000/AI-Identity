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

from common.audit.writer import create_audit_entry
from common.models import User, get_db
from mandate.app.auth import get_current_user
from mandate.app.database import get_db as get_mongo
from mandate.app.schemas import (
    IssueMandateRequest,
    MandateDocument,
    MandateExceedance,
    MandateIssuer,
    MandateListResponse,
    MandateResponse,
    MandateRevocation,
    MandateStatus,
    MandateSubject,
    RecordSpendRequest,
    RecordSpendResult,
    RevokeMandateRequest,
)
from mandate.app.signing import sign_mandate
from mandate.app.spend import evaluate_spend

logger = logging.getLogger("ai_identity.mandate.router")

router = APIRouter(prefix="/api/v1/mandates", tags=["mandates"])


def _new_mandate_id() -> str:
    """Generate a human-readable mandate ID: mnd_<8 hex chars>."""
    return "mnd_" + uuid.uuid4().hex[:8]


def _doc_to_response(doc: dict) -> MandateResponse:
    doc.pop("_id", None)
    return MandateResponse(**doc)


def _write_mandate_audit(
    db: Session,
    *,
    subject_agent_id: str,
    endpoint: str,
    decision: str,
    metadata: dict,
) -> None:
    """Append a mandate lifecycle event to the hash-chained audit log.

    This is what puts granted → spend → exceeded/revoked into the same
    tamper-evident envelope (and OCSF export) as every gateway event.

    The subject agent id must be a platform agent UUID for org resolution;
    mandates issued to external/non-platform subjects are logged locally
    and skipped — they have no org chain to join.

    Deliberately NOT wrapped in try/except: if the audit chain cannot be
    written, the caller's HTTP request fails. An unauditable mandate
    operation is worse than a failed one — same fail-close stance as the
    gateway.
    """
    try:
        agent_uuid = uuid.UUID(subject_agent_id)
    except ValueError:
        logger.warning(
            "mandate audit skipped: subject agent_id %r is not a platform agent UUID",
            subject_agent_id,
        )
        return
    create_audit_entry(
        db,
        agent_id=agent_uuid,
        endpoint=endpoint,
        method="POST",
        decision=decision,
        request_metadata=metadata,
    )


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
        schema_version="1.1",
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
        spend_limit=body.spend_limit,
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
        "Mandate issued: %s → agent=%s scope=%s limit=%s",
        mandate.mandate_id,
        body.subject_agent_id,
        body.scope,
        body.spend_limit.limit_cents if body.spend_limit else None,
    )

    issue_meta: dict = {
        "action_type": "mandate_issued",
        "resource_type": "mandate",
        "mandate_id": mandate.mandate_id,
    }
    if body.spend_limit:
        issue_meta["mandate_limit_cents"] = body.spend_limit.limit_cents
        issue_meta["spend_currency"] = body.spend_limit.currency
    _write_mandate_audit(
        db,
        subject_agent_id=body.subject_agent_id,
        endpoint="/api/v1/mandates",
        decision="allow",
        metadata=issue_meta,
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
    # exceeded mandates may still be revoked (operator cleanup after a breach)
    if doc["status"] not in (MandateStatus.active.value, MandateStatus.exceeded.value):
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

    _write_mandate_audit(
        db,
        subject_agent_id=doc["subject"]["agent_id"],
        endpoint=f"/api/v1/mandates/{mandate_id}/revoke",
        decision="allow",
        metadata={
            "action_type": "mandate_revoked",
            "resource_type": "mandate",
            "mandate_id": mandate_id,
            "old_status": doc["status"],
            "new_status": MandateStatus.revoked.value,
        },
    )

    updated = await mongo["mandates"].find_one({"mandate_id": mandate_id}, {"_id": 0})
    return MandateResponse(**updated)


# ── Record spend ───────────────────────────────────────────────────────────


@router.post(
    "/{mandate_id}/spend",
    response_model=RecordSpendResult,
    summary="Record a spend against a mandate's limit",
)
async def record_spend(
    mandate_id: str,
    body: RecordSpendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate and record one spend against the mandate's spend limit.

    Default mode ENFORCES: a spend that would cross the limit is denied and
    not recorded (the mandate keeps its remaining budget). With
    ``settlement=true`` the spend is recorded even when it crosses — money
    that already moved can't be un-moved — and a crossing flips the mandate
    to ``exceeded``.

    Every call — allowed or denied — lands in the tamper-evident audit
    chain, so the full story (granted → spends → breach) is walkable in
    the OCSF export and offline-verifiable.
    """
    mongo = get_mongo()
    org_id = str(current_user.org_id) if current_user.org_id else str(current_user.id)
    now = datetime.now(UTC)

    doc = await mongo["mandates"].find_one(
        {"mandate_id": mandate_id, "issuer.org_id": org_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Mandate not found")

    mandate = MandateDocument(**doc)
    outcome = evaluate_spend(
        status=mandate.status,
        spend_limit=mandate.spend_limit,
        spent_cents=mandate.spent_cents,
        amount_cents=body.amount_cents,
        currency=body.currency,
        settlement=body.settlement,
    )

    # Persist state changes (accepted spends and/or a status flip)
    if outcome.accepted or outcome.new_status != mandate.status:
        update: dict = {"$set": {"updated_at": now.isoformat()}}
        if outcome.accepted:
            update["$set"]["spent_cents"] = outcome.new_spent_cents
        if outcome.new_status != mandate.status:
            update["$set"]["status"] = outcome.new_status.value
        if outcome.exceeded:
            update["$set"]["exceedance"] = MandateExceedance(
                exceeded_at=now,
                attempted_cents=body.amount_cents,
                spent_cents=outcome.new_spent_cents,
                limit_cents=mandate.spend_limit.limit_cents if mandate.spend_limit else 0,
                reference=body.reference,
            ).model_dump(mode="json")
        await mongo["mandates"].update_one({"mandate_id": mandate_id}, update)

    # Append to the immutable event log
    await mongo["mandate_events"].insert_one(
        {
            "mandate_id": mandate_id,
            "event_type": (
                "exceeded"
                if outcome.exceeded
                else ("spend_recorded" if outcome.accepted else "spend_denied")
            ),
            "event_at": now.isoformat(),
            "actor": str(current_user.id),
            "amount_cents": body.amount_cents,
            "currency": body.currency,
            "settlement": body.settlement,
            "spent_cents": outcome.new_spent_cents,
            "reference": body.reference,
            "deny_reason": outcome.deny_reason,
        }
    )

    # The chained, exportable record — denials included, that's the point.
    spend_meta: dict = {
        "action_type": (
            "mandate_limit_exceeded" if outcome.deny_reason else "mandate_spend_recorded"
        ),
        "resource_type": "mandate",
        "mandate_id": mandate_id,
        "spend_amount_cents": body.amount_cents,
        "spend_currency": body.currency,
        "spend_settlement": body.settlement,
        "mandate_spent_cents": outcome.new_spent_cents,
    }
    if mandate.spend_limit:
        spend_meta["mandate_limit_cents"] = mandate.spend_limit.limit_cents
    if body.reference:
        spend_meta["spend_reference"] = body.reference
    if outcome.deny_reason:
        spend_meta["deny_reason"] = outcome.deny_reason
    _write_mandate_audit(
        db,
        subject_agent_id=mandate.subject.agent_id,
        endpoint=f"/api/v1/mandates/{mandate_id}/spend",
        decision=outcome.audit_decision,
        metadata=spend_meta,
    )

    limit_cents = mandate.spend_limit.limit_cents if mandate.spend_limit else None
    return RecordSpendResult(
        mandate_id=mandate_id,
        accepted=outcome.accepted,
        exceeded=outcome.exceeded,
        status=outcome.new_status,
        spent_cents=outcome.new_spent_cents,
        limit_cents=limit_cents,
        remaining_cents=(
            max(0, limit_cents - outcome.new_spent_cents) if limit_cents is not None else None
        ),
        deny_reason=outcome.deny_reason,
    )
