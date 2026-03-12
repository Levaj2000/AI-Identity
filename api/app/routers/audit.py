"""Audit log endpoints — read-only access and integrity verification.

The audit log is append-only with an HMAC integrity chain. These endpoints
provide read access (scoped to the authenticated user's agents) and a
chain verification endpoint for SOC 2 compliance checks.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.audit import verify_chain
from common.models import Agent, AuditLog, User, get_db
from common.schemas.agent import (
    AuditChainVerifyResponse,
    AuditLogListResponse,
    AuditLogResponse,
)

logger = logging.getLogger("ai_identity.api.audit")

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="List audit log entries",
    response_description="Paginated audit log entries, newest first",
)
def list_audit_logs(
    agent_id: uuid.UUID | None = Query(None, description="Filter by agent ID"),
    decision: str | None = Query(None, pattern="^(allow|deny|error)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit log entries with optional filters.

    Results are scoped to agents owned by the authenticated user.
    """
    # Get user's agent IDs for scoping
    user_agent_ids = [row[0] for row in db.query(Agent.id).filter(Agent.user_id == user.id).all()]

    query = db.query(AuditLog).filter(AuditLog.agent_id.in_(user_agent_ids))

    if agent_id:
        if agent_id not in user_agent_ids:
            return AuditLogListResponse(items=[], total=0, limit=limit, offset=offset)
        query = query.filter(AuditLog.agent_id == agent_id)

    if decision:
        query = query.filter(AuditLog.decision == decision)

    total = query.count()
    entries = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/verify",
    response_model=AuditChainVerifyResponse,
    summary="Verify audit chain integrity",
    response_description="Chain verification result",
)
def verify_audit_chain(
    agent_id: uuid.UUID | None = Query(
        None,
        description="Verify hash integrity for a specific agent only (no chain linkage)",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify the HMAC integrity chain of the audit log.

    Walks all entries in order, recomputes each HMAC, and checks
    that prev_hash links are consistent. Reports the first break found.

    Without agent_id: verifies the full global chain.
    With agent_id: verifies hash integrity for that agent's entries only.
    """
    if agent_id:
        agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

    result = verify_chain(db, agent_id=agent_id)

    logger.info(
        "Chain verification: valid=%s, entries=%s, verified=%s",
        result.valid,
        result.total_entries,
        result.entries_verified,
    )

    return AuditChainVerifyResponse(
        valid=result.valid,
        total_entries=result.total_entries,
        entries_verified=result.entries_verified,
        first_broken_id=result.first_broken_id,
        message=result.message,
    )
