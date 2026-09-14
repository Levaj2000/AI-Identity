"""Forensic retention policy API (v0.5.0).

Policy CRUD with create-time validation, immutable versioning, the
explain endpoint, legal holds, and the retention-event feed.

Design authority: Notion "Forensic Retention Policies — Policy Model (v0.5.0)".
Validation semantics live in :mod:`common.validation.retention`; this router
is the HTTP surface over it.

All write endpoints record ``created_by``/``placed_by`` as the opaque
principal ``str(user.id)`` — never an email.
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import User, get_db
from common.models.legal_hold import HOLD_STATUSES, LegalHold
from common.models.org_membership import OrgMembership
from common.models.organization import Organization
from common.models.retention_event import RETENTION_EVENT_TYPES, RetentionEvent
from common.models.retention_policy import RetentionPolicy
from common.schemas.retention import (
    ExplainRequest,
    ExplainResponse,
    HoldCreate,
    HoldRelease,
    HoldResponse,
    RetentionEventResponse,
    RetentionPolicyCreate,
    RetentionPolicyResponse,
)
from common.validation.retention import RetentionPolicyValidator, selector_matches

logger = logging.getLogger("ai_identity.api.retention")

router = APIRouter(prefix="/api/v1/organizations/{org_id}/retention", tags=["retention"])

# Tiers allowed to place legal holds (design doc tier matrix: free and pro
# have no holds; holds are ceiling-exempt and a durability upsell).
_HOLD_TIERS = frozenset({"business", "enterprise"})


# ── Helpers ────────────────────────────────────────────────────────────


def _require_org_access(db: Session, user: User, org_id: uuid.UUID) -> Organization:
    """Return the org, or raise 404/403. Platform admins bypass membership."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if user.role == "admin":
        return org
    membership = (
        db.query(OrgMembership)
        .filter(OrgMembership.org_id == org_id, OrgMembership.user_id == user.id)
        .first()
    )
    if membership is None and user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return org


def _active_policy(db: Session, org_id: uuid.UUID) -> RetentionPolicy | None:
    return (
        db.query(RetentionPolicy)
        .filter(RetentionPolicy.org_id == org_id, RetentionPolicy.status == "active")
        .first()
    )


def _emit_event(
    db: Session,
    *,
    org_id: uuid.UUID,
    event_type: str,
    payload: dict,
    created_by: str,
) -> RetentionEvent:
    event = RetentionEvent(
        org_id=org_id,
        event_type=event_type,
        payload=payload,
        created_by=created_by,
    )
    db.add(event)
    return event


# ── Policies ───────────────────────────────────────────────────────────


@router.post("/policies", response_model=RetentionPolicyResponse, status_code=201)
def create_policy(
    org_id: uuid.UUID,
    body: RetentionPolicyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Publish a new retention policy version.

    The current active version (if any) flips to ``superseded``; the new
    version becomes active. A ``policy_published`` retention event is
    chained. Validation errors return 400; non-fatal findings (e.g.
    broad-before-narrow) are returned in ``warnings``.
    """
    org = _require_org_access(db, user, org_id)
    if org.tier == "free":
        raise HTTPException(
            status_code=403,
            detail="Custom retention policies are not available on the free tier",
        )

    current = _active_policy(db, org_id)
    validator = RetentionPolicyValidator(org_tier=org.tier, current_policy=current)
    errors, warnings = validator.validate(body)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    now = datetime.now(UTC)
    if current is not None:
        current.status = "superseded"
        # Flush the flip first: the partial unique index allows exactly one
        # active version per org, so the slot must be released before the new
        # active row is inserted (independent of UoW statement ordering).
        db.flush()
        version = current.version + 1
        policy_id = current.policy_id
        supersedes = current.id
    else:
        version = 1
        policy_id = f"retpol_{uuid.uuid4().hex[:12]}"
        supersedes = None

    policy = RetentionPolicy(
        policy_id=policy_id,
        org_id=org_id,
        version=version,
        status="active",
        rules=[rule.model_dump(mode="json") for rule in body.rules],
        default_rule=body.default_rule,
        created_by=str(user.id),
        effective_at=body.effective_at or now,
        supersedes=supersedes,
        change_reason=body.change_reason,
        approvals=[approval.model_dump(mode="json") for approval in body.approvals],
    )
    db.add(policy)
    db.flush()
    _emit_event(
        db,
        org_id=org_id,
        event_type="policy_published",
        payload={
            "policy_id": policy_id,
            "version": version,
            "supersedes": str(supersedes) if supersedes else None,
            "warnings": warnings,
        },
        created_by=str(user.id),
    )
    db.commit()
    db.refresh(policy)

    response = RetentionPolicyResponse.model_validate(policy)
    response.warnings = warnings
    return response


@router.get("/policies", response_model=list[RetentionPolicyResponse])
def list_policies(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List policy versions, newest first."""
    _require_org_access(db, user, org_id)
    policies = (
        db.query(RetentionPolicy)
        .filter(RetentionPolicy.org_id == org_id)
        .order_by(RetentionPolicy.version.desc())
        .all()
    )
    return [RetentionPolicyResponse.model_validate(policy) for policy in policies]


@router.get("/policies/active", response_model=RetentionPolicyResponse)
def get_active_policy(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the org's active retention policy version."""
    _require_org_access(db, user, org_id)
    policy = _active_policy(db, org_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="No active retention policy")
    return RetentionPolicyResponse.model_validate(policy)


@router.post("/policies/explain", response_model=ExplainResponse)
def explain_policy(
    org_id: uuid.UUID,
    body: ExplainRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the first matching rule for a record descriptor.

    Evaluates the active policy's rules top to bottom (first-match) against
    the descriptor. A selector key only matches when the descriptor carries
    that key.
    """
    _require_org_access(db, user, org_id)
    policy = _active_policy(db, org_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="No active retention policy")
    descriptor = body.model_dump(exclude_none=True)
    for index, rule in enumerate(policy.rules or []):
        if selector_matches(rule.get("selector") or {}, descriptor):
            return ExplainResponse(rule_id=rule.get("rule_id"), rule=rule, matched_index=index)
    raise HTTPException(status_code=404, detail="No rule matched the descriptor")


# ── Legal holds ────────────────────────────────────────────────────────


@router.post("/holds", response_model=HoldResponse, status_code=201)
def place_hold(
    org_id: uuid.UUID,
    body: HoldCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Place a legal hold. Holds are ceiling-exempt: they freeze pruning
    past the plan's retention ceiling for as long as they are active."""
    org = _require_org_access(db, user, org_id)
    if org.tier not in _HOLD_TIERS:
        raise HTTPException(
            status_code=403,
            detail=f"Legal holds are not available on the {org.tier} tier",
        )
    hold = LegalHold(
        org_id=org_id,
        selector=body.selector,
        status="active",
        placed_by=str(user.id),
    )
    db.add(hold)
    db.flush()
    _emit_event(
        db,
        org_id=org_id,
        event_type="hold_placed",
        payload={"hold_id": str(hold.id), "selector": body.selector},
        created_by=str(user.id),
    )
    db.commit()
    db.refresh(hold)
    return HoldResponse.model_validate(hold)


@router.get("/holds", response_model=list[HoldResponse])
def list_holds(
    org_id: uuid.UUID,
    status: str = Query(default="active", description="Filter by hold status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List legal holds, optionally filtered by status."""
    _require_org_access(db, user, org_id)
    if status not in HOLD_STATUSES:
        raise HTTPException(
            status_code=400, detail=f'Invalid status "{status}" (allowed: {sorted(HOLD_STATUSES)})'
        )
    holds = (
        db.query(LegalHold)
        .filter(LegalHold.org_id == org_id, LegalHold.status == status)
        .order_by(LegalHold.placed_at.desc())
        .all()
    )
    return [HoldResponse.model_validate(hold) for hold in holds]


@router.post("/holds/{hold_id}/release", response_model=HoldResponse)
def release_hold(
    org_id: uuid.UUID,
    hold_id: uuid.UUID,
    body: HoldRelease,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Release a legal hold. The releaser must differ from the placer."""
    _require_org_access(db, user, org_id)
    hold = db.query(LegalHold).filter(LegalHold.id == hold_id, LegalHold.org_id == org_id).first()
    if hold is None:
        raise HTTPException(status_code=404, detail="Hold not found")
    if hold.status != "active":
        raise HTTPException(status_code=400, detail="Hold is not active")
    released_by = str(user.id)
    if released_by == hold.placed_by:
        raise HTTPException(
            status_code=400,
            detail="Hold release requires an approver different from the placer",
        )
    hold.status = "released"
    hold.released_at = datetime.now(UTC)
    hold.released_by = released_by
    hold.release_reason = body.release_reason
    _emit_event(
        db,
        org_id=org_id,
        event_type="hold_released",
        payload={"hold_id": str(hold.id), "release_reason": body.release_reason},
        created_by=released_by,
    )
    db.commit()
    db.refresh(hold)
    return HoldResponse.model_validate(hold)


# ── Retention events ───────────────────────────────────────────────────


@router.get("/events", response_model=list[RetentionEventResponse])
def list_events(
    org_id: uuid.UUID,
    event_type: str | None = Query(default=None, description="Filter by event type"),
    limit: int = Query(default=100, le=1000, description="Max events to return"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List retention events, newest first — the feed attestation
    cross-checks use to verify every missing record has a tombstone."""
    _require_org_access(db, user, org_id)
    if event_type is not None and event_type not in RETENTION_EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f'Invalid event_type "{event_type}" (allowed: {sorted(RETENTION_EVENT_TYPES)})'
            ),
        )
    query = db.query(RetentionEvent).filter(RetentionEvent.org_id == org_id)
    if event_type is not None:
        query = query.filter(RetentionEvent.event_type == event_type)
    events = (
        query.order_by(RetentionEvent.created_at.desc(), RetentionEvent.id.desc())
        .limit(limit)
        .all()
    )
    return [RetentionEventResponse.model_validate(event) for event in events]
