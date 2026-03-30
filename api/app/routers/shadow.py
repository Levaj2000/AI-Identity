"""Shadow Agent Detection — analytics on denied gateway requests.

Surfaces unmanaged/unregistered agents hitting the gateway.
Customer-facing: account owners see their own shadow agents,
admins see all.
"""

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import AuditLog, User, get_db
from common.schemas.shadow import (
    ShadowAgentDetail,
    ShadowAgentListResponse,
    ShadowAgentStats,
    ShadowAgentSummary,
    ShadowEvent,
    TopEndpointHit,
)

logger = logging.getLogger("ai_identity.api.shadow")

router = APIRouter(prefix="/api/v1/shadow-agents", tags=["shadow-agents"])

# Deny reasons that indicate shadow/unmanaged agents
SHADOW_DENY_REASONS = ("agent_not_found", "agent_inactive")


def _deny_reason_col():
    """JSONB text extraction for deny_reason."""
    return AuditLog.request_metadata["deny_reason"].astext


def _base_query(
    db: Session, user: User, start_date: datetime.datetime, end_date: datetime.datetime
):
    """Build base query filtered by shadow deny reasons, date range, and user scope."""
    deny_reason = _deny_reason_col()
    query = db.query(AuditLog).filter(
        AuditLog.decision == "deny",
        deny_reason.in_(SHADOW_DENY_REASONS),
        AuditLog.created_at >= start_date,
        AuditLog.created_at <= end_date,
    )

    # Non-admin users see only their own (agent_inactive entries have user_id set)
    if user.role != "admin":
        query = query.filter(AuditLog.user_id == user.id)

    return query


def _default_start() -> datetime.datetime:
    """Default start date: 7 days ago."""
    return datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7)


def _default_end() -> datetime.datetime:
    """Default end date: now."""
    return datetime.datetime.now(datetime.UTC)


# ── Stats ───────────────────────────────────────────────────────────


@router.get(
    "/stats",
    response_model=ShadowAgentStats,
    summary="Shadow agent summary counts",
)
async def shadow_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: datetime.datetime | None = Query(None),
    end_date: datetime.datetime | None = Query(None),
) -> ShadowAgentStats:
    """Return aggregate counts of shadow agent activity."""
    start = start_date or _default_start()
    end = end_date or _default_end()
    deny_reason = _deny_reason_col()

    base = _base_query(db, user, start, end)

    total_hits = base.count()
    total_agents = base.with_entities(AuditLog.agent_id).distinct().count()

    not_found = (
        base.filter(deny_reason == "agent_not_found")
        .with_entities(AuditLog.agent_id)
        .distinct()
        .count()
    )

    inactive = (
        base.filter(deny_reason == "agent_inactive")
        .with_entities(AuditLog.agent_id)
        .distinct()
        .count()
    )

    return ShadowAgentStats(
        total_shadow_agents=total_agents,
        total_shadow_hits=total_hits,
        agents_not_found=not_found,
        agents_inactive=inactive,
    )


# ── List ────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=ShadowAgentListResponse,
    summary="List detected shadow agents",
)
async def list_shadow_agents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: datetime.datetime | None = Query(None),
    end_date: datetime.datetime | None = Query(None),
    min_hits: int = Query(1, ge=1, description="Minimum hit count threshold"),
    deny_reason: str | None = Query(None, description="Filter: agent_not_found or agent_inactive"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ShadowAgentListResponse:
    """List detected shadow agents grouped by agent_id."""
    start = start_date or _default_start()
    end = end_date or _default_end()
    deny_reason_col = _deny_reason_col()

    base = _base_query(db, user, start, end)
    if deny_reason and deny_reason in SHADOW_DENY_REASONS:
        base = base.filter(deny_reason_col == deny_reason)

    # Aggregate by agent_id + deny_reason
    agg = base.with_entities(
        AuditLog.agent_id,
        deny_reason_col.label("deny_reason"),
        func.count(AuditLog.id).label("hit_count"),
        func.min(AuditLog.created_at).label("first_seen"),
        func.max(AuditLog.created_at).label("last_seen"),
    ).group_by(AuditLog.agent_id, deny_reason_col)

    if min_hits > 1:
        agg = agg.having(func.count(AuditLog.id) >= min_hits)

    # Get total before pagination
    total_query = agg.subquery()
    total = db.query(func.count()).select_from(total_query).scalar() or 0
    total_hits_val = db.query(func.coalesce(func.sum(total_query.c.hit_count), 0)).scalar() or 0

    # Paginate
    rows = agg.order_by(func.count(AuditLog.id).desc()).offset(offset).limit(limit).all()

    # Batch-fetch top endpoints for the page
    agent_ids = [r.agent_id for r in rows]
    top_endpoints_map: dict[str, list[str]] = {}
    if agent_ids:
        endpoint_rows = (
            base.filter(AuditLog.agent_id.in_(agent_ids))
            .with_entities(
                AuditLog.agent_id,
                AuditLog.endpoint,
                func.count(AuditLog.id).label("cnt"),
            )
            .group_by(AuditLog.agent_id, AuditLog.endpoint)
            .order_by(func.count(AuditLog.id).desc())
            .all()
        )
        for ep_row in endpoint_rows:
            aid = str(ep_row.agent_id)
            if aid not in top_endpoints_map:
                top_endpoints_map[aid] = []
            if len(top_endpoints_map[aid]) < 3:
                top_endpoints_map[aid].append(ep_row.endpoint)

    items = [
        ShadowAgentSummary(
            agent_id=str(r.agent_id),
            deny_reason=r.deny_reason,
            hit_count=r.hit_count,
            first_seen=r.first_seen,
            last_seen=r.last_seen,
            top_endpoints=top_endpoints_map.get(str(r.agent_id), []),
        )
        for r in rows
    ]

    return ShadowAgentListResponse(
        items=items,
        total=total,
        total_hits=total_hits_val,
        limit=limit,
        offset=offset,
    )


# ── Detail ──────────────────────────────────────────────────────────


@router.get(
    "/{agent_id}",
    response_model=ShadowAgentDetail,
    summary="Shadow agent detail",
)
async def shadow_agent_detail(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: datetime.datetime | None = Query(None),
    end_date: datetime.datetime | None = Query(None),
) -> ShadowAgentDetail:
    """Full detail for a single shadow agent."""
    start = start_date or _default_start()
    end = end_date or _default_end()
    deny_reason_col = _deny_reason_col()

    base = _base_query(db, user, start, end).filter(AuditLog.agent_id == agent_id)

    # Aggregate stats
    stats = (
        base.with_entities(
            deny_reason_col.label("deny_reason"),
            func.count(AuditLog.id).label("hit_count"),
            func.min(AuditLog.created_at).label("first_seen"),
            func.max(AuditLog.created_at).label("last_seen"),
        )
        .group_by(deny_reason_col)
        .first()
    )

    if not stats:
        raise HTTPException(status_code=404, detail="No shadow activity found for this agent")

    # Top endpoints
    endpoint_rows = (
        base.with_entities(
            AuditLog.endpoint,
            AuditLog.method,
            func.count(AuditLog.id).label("cnt"),
        )
        .group_by(AuditLog.endpoint, AuditLog.method)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )

    # Recent events
    recent = base.order_by(AuditLog.created_at.desc()).limit(50).all()

    return ShadowAgentDetail(
        agent_id=agent_id,
        deny_reason=stats.deny_reason,
        hit_count=stats.hit_count,
        first_seen=stats.first_seen,
        last_seen=stats.last_seen,
        top_endpoints=[
            TopEndpointHit(endpoint=r.endpoint, method=r.method, count=r.cnt) for r in endpoint_rows
        ],
        recent_events=[
            ShadowEvent(
                id=e.id,
                endpoint=e.endpoint,
                method=e.method,
                deny_reason=(e.request_metadata or {}).get("deny_reason", "unknown"),
                request_metadata=e.request_metadata or {},
                created_at=e.created_at,
            )
            for e in recent
        ],
    )
