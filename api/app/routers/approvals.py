"""Approvals router — human-in-the-loop review for enterprise tier.

List, view, approve, and reject pending gateway requests.
"""

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import Agent, ApprovalRequest, ApprovalStatus, User, get_db
from common.schemas.approval import (
    ApprovalAction,
    ApprovalListResponse,
    ApprovalPendingCount,
    ApprovalResolveRequest,
    ApprovalResponse,
)

logger = logging.getLogger("ai_identity.api.approvals")

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


def _to_response(approval: ApprovalRequest, agent_name: str | None = None) -> ApprovalResponse:
    """Convert an ApprovalRequest ORM object to a response schema."""
    return ApprovalResponse(
        id=str(approval.id),
        agent_id=str(approval.agent_id),
        agent_name=agent_name,
        user_id=str(approval.user_id),
        endpoint=approval.endpoint,
        method=approval.method,
        request_metadata=approval.request_metadata or {},
        status=approval.status,
        reviewer_id=str(approval.reviewer_id) if approval.reviewer_id else None,
        reviewer_note=approval.reviewer_note,
        resolved_at=approval.resolved_at,
        expires_at=approval.expires_at,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
    )


# ── List Approvals ──────────────────────────────────────────────────


@router.get(
    "",
    response_model=ApprovalListResponse,
    summary="List approval requests",
)
async def list_approvals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="Filter by status"),
    agent_id: str | None = Query(None, description="Filter by agent ID"),
) -> ApprovalListResponse:
    """List approval requests visible to the current user.

    Admin users see all approvals. Non-admin users see only their own.
    """
    # Lazy expire stale pending requests
    _expire_stale(db)

    query = db.query(ApprovalRequest, Agent.name).outerjoin(
        Agent, Agent.id == ApprovalRequest.agent_id
    )

    # Non-admin users see only their own
    if user.role != "admin":
        query = query.filter(ApprovalRequest.user_id == user.id)

    if status:
        query = query.filter(ApprovalRequest.status == status)
    if agent_id:
        query = query.filter(ApprovalRequest.agent_id == agent_id)

    total = query.count()
    rows = query.order_by(ApprovalRequest.created_at.desc()).offset(offset).limit(limit).all()

    items = [_to_response(approval, agent_name) for approval, agent_name in rows]

    return ApprovalListResponse(items=items, total=total, limit=limit, offset=offset)


# ── Pending Count (for sidebar badge) ───────────────────────────────


@router.get(
    "/pending/count",
    response_model=ApprovalPendingCount,
    summary="Count pending approvals",
)
async def pending_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApprovalPendingCount:
    """Return the number of pending approvals for sidebar badge."""
    query = db.query(func.count(ApprovalRequest.id)).filter(
        ApprovalRequest.status == ApprovalStatus.pending.value,
        ApprovalRequest.expires_at >= datetime.datetime.now(datetime.UTC),
    )

    if user.role != "admin":
        query = query.filter(ApprovalRequest.user_id == user.id)

    count = query.scalar() or 0
    return ApprovalPendingCount(count=count)


# ── Detail View ─────────────────────────────────────────────────────


@router.get(
    "/{approval_id}",
    response_model=ApprovalResponse,
    summary="Get approval detail",
)
async def get_approval(
    approval_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    """Get full details of an approval request."""
    row = (
        db.query(ApprovalRequest, Agent.name)
        .outerjoin(Agent, Agent.id == ApprovalRequest.agent_id)
        .filter(ApprovalRequest.id == approval_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")

    approval, agent_name = row

    # Non-admin users can only see their own
    if user.role != "admin" and approval.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Lazy expire if stale
    if (
        approval.status == ApprovalStatus.pending.value
        and approval.expires_at < datetime.datetime.now(datetime.UTC)
    ):
        approval.status = ApprovalStatus.expired.value
        db.commit()
        db.refresh(approval)

    return _to_response(approval, agent_name)


# ── Resolve (Approve / Reject) ──────────────────────────────────────


@router.post(
    "/{approval_id}/resolve",
    response_model=ApprovalResponse,
    summary="Approve or reject a pending request",
)
async def resolve_approval(
    approval_id: str,
    body: ApprovalResolveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    """Approve or reject a pending approval request."""
    row = (
        db.query(ApprovalRequest, Agent.name)
        .outerjoin(Agent, Agent.id == ApprovalRequest.agent_id)
        .filter(ApprovalRequest.id == approval_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")

    approval, agent_name = row

    # Non-admin users can only resolve their own
    if user.role != "admin" and approval.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if approval.status != ApprovalStatus.pending.value:
        raise HTTPException(
            status_code=409,
            detail=f"Approval is already {approval.status}, cannot resolve",
        )

    # Check if expired
    if approval.expires_at < datetime.datetime.now(datetime.UTC):
        approval.status = ApprovalStatus.expired.value
        db.commit()
        raise HTTPException(status_code=410, detail="Approval request has expired")

    # Resolve
    now = datetime.datetime.now(datetime.UTC)
    if body.action == ApprovalAction.approve:
        approval.status = ApprovalStatus.approved.value
    else:
        approval.status = ApprovalStatus.rejected.value

    approval.reviewer_id = user.id
    approval.reviewer_note = body.note
    approval.resolved_at = now
    db.commit()
    db.refresh(approval)

    logger.info(
        "Approval %s %s by %s (user %s)%s",
        approval_id,
        body.action.value,
        user.email,
        user.id,
        f" — note: {body.note}" if body.note else "",
    )

    return _to_response(approval, agent_name)


# ── Helpers ─────────────────────────────────────────────────────────


def _expire_stale(db: Session) -> int:
    """Expire pending approvals past their deadline."""
    now = datetime.datetime.now(datetime.UTC)
    count = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.status == ApprovalStatus.pending.value,
            ApprovalRequest.expires_at < now,
        )
        .update(
            {ApprovalRequest.status: ApprovalStatus.expired.value},
            synchronize_session=False,
        )
    )
    if count:
        db.commit()
    return count
