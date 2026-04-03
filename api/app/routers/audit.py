"""Audit log endpoints — read-only access, integrity verification, and AI Forensics.

The audit log is append-only with an HMAC integrity chain. These endpoints
provide read access (scoped to the authenticated user's agents), chain
verification for SOC 2 compliance, and forensics features for incident
reconstruction and reporting.
"""

import csv
import io
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.app.auth import get_current_user, require_admin
from common.audit import verify_chain
from common.models import Agent, AuditLog, Policy, User, get_db
from common.schemas.agent import (
    AuditChainVerifyResponse,
    AuditLogListResponse,
    AuditLogResponse,
    AuditReconstructResponse,
    AuditStatsResponse,
    ForensicsReportResponse,
    PolicyResponse,
    TopEndpoint,
)

logger = logging.getLogger("ai_identity.api.audit")

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


# ── Helper: get user's agent IDs ────────────────────────────────────


def _user_agent_ids(db: Session, user: User) -> list[uuid.UUID]:
    """Return list of agent IDs owned by the user."""
    return [row[0] for row in db.query(Agent.id).filter(Agent.user_id == user.id).all()]


def _build_audit_query(
    db: Session,
    user_agent_ids: list[uuid.UUID],
    agent_id: uuid.UUID | None = None,
    decision: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    endpoint: str | None = None,
    action_type: str | None = None,
    model: str | None = None,
    cost_min: float | None = None,
    cost_max: float | None = None,
    user_id: uuid.UUID | None = None,
):
    """Build a filtered audit log query scoped to user's agents.

    Also includes shadow agent entries (denied requests where audit_log.user_id
    matches the current user) so the Forensics page can display them.
    """
    from sqlalchemy import or_

    # Base scope: entries for registered agents OR entries owned by this user
    # (shadow agent denials from inactive agents have user_id set)
    if user_id:
        query = db.query(AuditLog).filter(
            or_(
                AuditLog.agent_id.in_(user_agent_ids),
                AuditLog.user_id == user_id,
            )
        )
    else:
        query = db.query(AuditLog).filter(AuditLog.agent_id.in_(user_agent_ids))

    if agent_id:
        # Allow filtering by any agent_id the user has visibility into
        # (registered agents via ownership, shadow agents via user_id on audit entries)
        query = query.filter(AuditLog.agent_id == agent_id)

    if decision:
        query = query.filter(AuditLog.decision == decision)

    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)

    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    if endpoint:
        query = query.filter(AuditLog.endpoint.ilike(f"%{endpoint}%"))

    if action_type:
        # Filter by action_type inside JSONB request_metadata
        query = query.filter(AuditLog.request_metadata["action_type"].astext == action_type)

    if model:
        query = query.filter(AuditLog.request_metadata["model"].astext == model)

    if cost_min is not None:
        query = query.filter(AuditLog.cost_estimate_usd >= cost_min)

    if cost_max is not None:
        query = query.filter(AuditLog.cost_estimate_usd <= cost_max)

    return query


def _compute_stats(
    db: Session,
    user_agent_ids: list[uuid.UUID],
    agent_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    user_id: uuid.UUID | None = None,
) -> AuditStatsResponse:
    """Compute aggregated statistics for a filtered audit window."""
    from sqlalchemy import or_

    if user_id:
        base = db.query(AuditLog).filter(
            or_(AuditLog.agent_id.in_(user_agent_ids), AuditLog.user_id == user_id)
        )
    else:
        base = db.query(AuditLog).filter(AuditLog.agent_id.in_(user_agent_ids))

    if agent_id:
        base = base.filter(AuditLog.agent_id == agent_id)
    if start_date:
        base = base.filter(AuditLog.created_at >= start_date)
    if end_date:
        base = base.filter(AuditLog.created_at <= end_date)

    # Decision counts
    decision_counts = (
        base.with_entities(AuditLog.decision, func.count(AuditLog.id))
        .group_by(AuditLog.decision)
        .all()
    )
    counts = {d: c for d, c in decision_counts}

    # Aggregates
    agg = base.with_entities(
        func.count(AuditLog.id),
        func.coalesce(func.sum(AuditLog.cost_estimate_usd), 0),
        func.avg(AuditLog.latency_ms),
    ).first()

    total_events = agg[0] if agg else 0
    total_cost = float(agg[1]) if agg else 0.0
    avg_latency = round(float(agg[2]), 1) if agg and agg[2] is not None else None

    # Top endpoints
    top_eps = (
        base.with_entities(AuditLog.endpoint, func.count(AuditLog.id).label("cnt"))
        .group_by(AuditLog.endpoint)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )

    return AuditStatsResponse(
        total_events=total_events,
        allowed_count=counts.get("allow", 0) + counts.get("allowed", 0),
        denied_count=counts.get("deny", 0) + counts.get("denied", 0),
        error_count=counts.get("error", 0),
        total_cost_usd=total_cost,
        avg_latency_ms=avg_latency,
        top_endpoints=[TopEndpoint(endpoint=ep, count=cnt) for ep, cnt in top_eps],
    )


# ── User Endpoints ──────────────────────────────────────────────────


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="List audit log entries",
    response_description="Paginated audit log entries, newest first",
)
def list_audit_logs(
    agent_id: uuid.UUID | None = Query(None, description="Filter by agent ID"),
    decision: str | None = Query(None, pattern="^(allowed|denied|error)$"),
    start_date: datetime | None = Query(None, description="Filter entries after this timestamp"),
    end_date: datetime | None = Query(None, description="Filter entries before this timestamp"),
    endpoint: str | None = Query(None, description="Filter by endpoint (partial match)"),
    action_type: str | None = Query(None, description="Filter by metadata action_type"),
    model: str | None = Query(None, description="Filter by metadata model"),
    cost_min: float | None = Query(None, description="Minimum cost_estimate_usd"),
    cost_max: float | None = Query(None, description="Maximum cost_estimate_usd"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit log entries with optional filters.

    Results are scoped to agents owned by the authenticated user.
    Supports filtering by agent, decision, date range, endpoint,
    metadata action_type, metadata model, and cost range.
    """
    user_agents = _user_agent_ids(db, user)

    query = _build_audit_query(
        db,
        user_agents,
        agent_id=agent_id,
        decision=decision,
        start_date=start_date,
        end_date=end_date,
        endpoint=endpoint,
        action_type=action_type,
        model=model,
        cost_min=cost_min,
        cost_max=cost_max,
        user_id=user.id,
    )

    total = query.count()
    entries = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


# ── Forensics Endpoints (must be before /verify and /admin) ─────────


@router.get(
    "/stats",
    response_model=AuditStatsResponse,
    summary="Aggregated audit statistics",
    response_description="Decision counts, cost totals, top endpoints",
    tags=["forensics"],
)
def audit_stats(
    agent_id: uuid.UUID | None = Query(None, description="Filter by agent ID"),
    start_date: datetime | None = Query(None, description="Window start"),
    end_date: datetime | None = Query(None, description="Window end"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregated statistics for audit log entries.

    Provides decision counts, cost totals, average latency, and top
    endpoints for the given time window. Scoped to user's agents.
    """
    user_agents = _user_agent_ids(db, user)

    return _compute_stats(
        db,
        user_agents,
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date,
        user_id=user.id,
    )


@router.get(
    "/reconstruct",
    response_model=AuditReconstructResponse,
    summary="Incident reconstruction",
    response_description="Full event chain with policy context and chain verification",
    tags=["forensics"],
)
def audit_reconstruct(
    agent_id: uuid.UUID = Query(..., description="Agent to investigate"),
    start_date: datetime = Query(..., description="Investigation window start"),
    end_date: datetime = Query(..., description="Investigation window end"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reconstruct an incident: all events, active policy, and chain integrity.

    Returns the complete decision history for an agent within a time window,
    along with the policy that was active and cryptographic chain verification.
    """
    user_agents = _user_agent_ids(db, user)

    # Verify agent ownership
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get events in window
    events = (
        db.query(AuditLog)
        .filter(
            AuditLog.agent_id == agent_id,
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date,
        )
        .order_by(AuditLog.created_at.asc())
        .all()
    )

    # Chain verification for this agent
    chain_result = verify_chain(db, agent_id=agent_id)

    # Active policy
    active_policy = (
        db.query(Policy)
        .filter(Policy.agent_id == agent_id, Policy.is_active.is_(True))
        .order_by(Policy.version.desc())
        .first()
    )

    # Stats for window
    stats = _compute_stats(
        db, user_agents, agent_id=agent_id, start_date=start_date, end_date=end_date
    )

    return AuditReconstructResponse(
        agent_id=agent_id,
        agent_name=agent.name,
        start_date=start_date,
        end_date=end_date,
        events=[AuditLogResponse.model_validate(e) for e in events],
        chain_verification=AuditChainVerifyResponse(
            valid=chain_result.valid,
            total_entries=chain_result.total_entries,
            entries_verified=chain_result.entries_verified,
            first_broken_id=chain_result.first_broken_id,
            message=chain_result.message,
        ),
        active_policy=PolicyResponse.model_validate(active_policy) if active_policy else None,
        stats=stats,
    )


@router.get(
    "/report",
    summary="Generate forensics report",
    response_description="Forensics report with chain-of-custody certificate",
    tags=["forensics"],
)
def audit_report(
    agent_id: uuid.UUID = Query(..., description="Agent to report on"),
    start_date: datetime = Query(..., description="Report window start"),
    end_date: datetime = Query(..., description="Report window end"),
    format: str = Query("json", pattern="^(json|csv)$", description="Output format"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an exportable forensics report.

    JSON format includes a chain-of-custody verification certificate.
    CSV format provides a flat event table for external analysis.
    """
    user_agents = _user_agent_ids(db, user)

    # Verify agent ownership
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get events
    events = (
        db.query(AuditLog)
        .filter(
            AuditLog.agent_id == agent_id,
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date,
        )
        .order_by(AuditLog.created_at.asc())
        .all()
    )

    # Chain verification
    chain_result = verify_chain(db, agent_id=agent_id)

    # Active policy
    active_policy = (
        db.query(Policy)
        .filter(Policy.agent_id == agent_id, Policy.is_active.is_(True))
        .order_by(Policy.version.desc())
        .first()
    )

    # Stats
    stats = _compute_stats(
        db, user_agents, agent_id=agent_id, start_date=start_date, end_date=end_date
    )

    event_responses = [AuditLogResponse.model_validate(e) for e in events]

    if format == "csv":
        # Build CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "agent_id",
                "endpoint",
                "method",
                "decision",
                "cost_estimate_usd",
                "latency_ms",
                "created_at",
                "entry_hash",
                "prev_hash",
                "request_metadata",
            ]
        )
        for e in event_responses:
            writer.writerow(
                [
                    e.id,
                    str(e.agent_id),
                    e.endpoint,
                    e.method,
                    e.decision,
                    e.cost_estimate_usd,
                    e.latency_ms,
                    e.created_at.isoformat(),
                    e.entry_hash,
                    e.prev_hash,
                    str(e.request_metadata),
                ]
            )

        # Add chain verification as footer
        writer.writerow([])
        writer.writerow(["# Chain Verification Certificate"])
        writer.writerow(["chain_valid", chain_result.valid])
        writer.writerow(["total_entries", chain_result.total_entries])
        writer.writerow(["entries_verified", chain_result.entries_verified])
        writer.writerow(["verification_message", chain_result.message])

        output.seek(0)
        filename = f"forensics-{agent.name}-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # JSON format
    report_id = f"fr-{agent_id.hex[:8]}-{start_date.strftime('%Y%m%d%H%M')}"
    chain_verify = AuditChainVerifyResponse(
        valid=chain_result.valid,
        total_entries=chain_result.total_entries,
        entries_verified=chain_result.entries_verified,
        first_broken_id=chain_result.first_broken_id,
        message=chain_result.message,
    )

    return ForensicsReportResponse(
        report_id=report_id,
        generated_at=datetime.now(tz=UTC),
        agent={
            "id": str(agent.id),
            "name": agent.name,
            "status": agent.status.value if hasattr(agent.status, "value") else str(agent.status),
            "description": agent.description,
        },
        time_window={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        events=event_responses,
        chain_verification=chain_verify,
        active_policy=PolicyResponse.model_validate(active_policy) if active_policy else None,
        stats=stats,
    )


# ── Chain Verification ──────────────────────────────────────────────


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


# ── Admin Audit Endpoints ────────────────────────────────────────────


@router.get(
    "/admin",
    response_model=AuditLogListResponse,
    summary="[Admin] List all audit entries system-wide",
    response_description="Paginated audit log (all users, all agents)",
)
def admin_list_audit_logs(
    agent_id: uuid.UUID | None = Query(None, description="Filter by agent ID"),
    user_id: uuid.UUID | None = Query(None, description="Filter by user ID"),
    decision: str | None = Query(None, pattern="^(allowed|denied|error)$"),
    action_type: str | None = Query(
        None,
        description="Filter by action_type in metadata (e.g. agent_created, key_rotated)",
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: list all audit log entries system-wide.

    No user-scoping — returns entries for all users and agents.
    Supports filtering by agent_id, user_id, decision, and action_type.
    """
    query = db.query(AuditLog)

    if agent_id:
        query = query.filter(AuditLog.agent_id == agent_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if decision:
        query = query.filter(AuditLog.decision == decision)
    if action_type:
        # Filter by action_type inside JSONB request_metadata
        query = query.filter(AuditLog.request_metadata["action_type"].astext == action_type)

    total = query.count()
    entries = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )
