"""Shadow Agent Detection — analytics on denied gateway requests.

Surfaces unmanaged/unregistered agents hitting the gateway.
Customer-facing: account owners see their own shadow agents,
admins see all.

Action flows: block (gateway enforcement), dismiss (UI hide).
"""

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import AuditLog, User, get_db
from common.models.blocked_agent import BlockedAgent
from common.models.dismissed_shadow import DismissedShadowAgent
from common.schemas.shadow import (
    BlockAgentRequest,
    BlockAgentResponse,
    DismissResponse,
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
SHADOW_DENY_REASONS = ("agent_not_found", "agent_inactive", "agent_blocked")


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


def _get_blocked_set(db: Session, user: User, agent_ids: list[str]) -> set[str]:
    """Return set of agent_ids that are blocked by this user."""
    if not agent_ids:
        return set()
    rows = (
        db.query(BlockedAgent.agent_id)
        .filter(BlockedAgent.user_id == user.id, BlockedAgent.agent_id.in_(agent_ids))
        .all()
    )
    return {r.agent_id for r in rows}


def _get_dismissed_set(db: Session, user: User, agent_ids: list[str]) -> set[str]:
    """Return set of agent_ids that are dismissed by this user."""
    if not agent_ids:
        return set()
    rows = (
        db.query(DismissedShadowAgent.agent_id)
        .filter(
            DismissedShadowAgent.user_id == user.id, DismissedShadowAgent.agent_id.in_(agent_ids)
        )
        .all()
    )
    return {r.agent_id for r in rows}


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

    # Blocked + dismissed counts
    blocked_count = db.query(BlockedAgent).filter(BlockedAgent.user_id == user.id).count()
    dismissed_count = (
        db.query(DismissedShadowAgent).filter(DismissedShadowAgent.user_id == user.id).count()
    )

    return ShadowAgentStats(
        total_shadow_agents=total_agents,
        total_shadow_hits=total_hits,
        agents_not_found=not_found,
        agents_inactive=inactive,
        agents_blocked=blocked_count,
        agents_dismissed=dismissed_count,
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
    deny_reason: str | None = Query(
        None, description="Filter: agent_not_found, agent_inactive, or agent_blocked"
    ),
    include_dismissed: bool = Query(False, description="Include dismissed shadow agents"),
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
    agent_ids = [str(r.agent_id) for r in rows]
    top_endpoints_map: dict[str, list[str]] = {}
    if agent_ids:
        endpoint_rows = (
            base.filter(AuditLog.agent_id.in_([r.agent_id for r in rows]))
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

    # Batch-fetch blocked + dismissed status
    blocked_set = _get_blocked_set(db, user, agent_ids)
    dismissed_set = _get_dismissed_set(db, user, agent_ids)

    items = [
        ShadowAgentSummary(
            agent_id=str(r.agent_id),
            deny_reason=r.deny_reason,
            hit_count=r.hit_count,
            first_seen=r.first_seen,
            last_seen=r.last_seen,
            top_endpoints=top_endpoints_map.get(str(r.agent_id), []),
            is_blocked=str(r.agent_id) in blocked_set,
            is_dismissed=str(r.agent_id) in dismissed_set,
        )
        for r in rows
    ]

    # Filter out dismissed unless requested
    if not include_dismissed:
        items = [item for item in items if not item.is_dismissed]

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

    # Blocked + dismissed status
    blocked = (
        db.query(BlockedAgent)
        .filter(BlockedAgent.user_id == user.id, BlockedAgent.agent_id == agent_id)
        .first()
    )
    dismissed = (
        db.query(DismissedShadowAgent)
        .filter(DismissedShadowAgent.user_id == user.id, DismissedShadowAgent.agent_id == agent_id)
        .first()
    )

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
        is_blocked=blocked is not None,
        blocked_at=blocked.created_at if blocked else None,
        is_dismissed=dismissed is not None,
    )


# ── Block / Unblock ────────────────────────────────────────────────


@router.post(
    "/{agent_id}/block",
    response_model=BlockAgentResponse,
    summary="Block a shadow agent",
)
async def block_shadow_agent(
    agent_id: str,
    body: BlockAgentRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BlockAgentResponse:
    """Explicitly block this agent_id at the gateway."""
    existing = (
        db.query(BlockedAgent)
        .filter(BlockedAgent.user_id == user.id, BlockedAgent.agent_id == agent_id)
        .first()
    )
    if existing:
        return BlockAgentResponse(agent_id=agent_id, blocked=True, blocked_at=existing.created_at)

    blocked = BlockedAgent(
        agent_id=agent_id,
        user_id=user.id,
        reason=body.reason if body else None,
    )
    db.add(blocked)
    db.commit()
    db.refresh(blocked)

    logger.info("Shadow agent blocked: agent_id=%s user_id=%s", agent_id, user.id)

    return BlockAgentResponse(agent_id=agent_id, blocked=True, blocked_at=blocked.created_at)


@router.delete(
    "/{agent_id}/block",
    status_code=204,
    summary="Unblock a shadow agent",
)
async def unblock_shadow_agent(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove this agent_id from the blocklist."""
    deleted = (
        db.query(BlockedAgent)
        .filter(BlockedAgent.user_id == user.id, BlockedAgent.agent_id == agent_id)
        .delete()
    )
    db.commit()

    if not deleted:
        raise HTTPException(status_code=404, detail="Agent is not blocked")

    logger.info("Shadow agent unblocked: agent_id=%s user_id=%s", agent_id, user.id)


# ── Dismiss / Un-dismiss ───────────────────────────────────────────


@router.post(
    "/{agent_id}/dismiss",
    response_model=DismissResponse,
    summary="Dismiss a shadow agent",
)
async def dismiss_shadow_agent(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DismissResponse:
    """Hide this shadow agent from the default list view."""
    existing = (
        db.query(DismissedShadowAgent)
        .filter(DismissedShadowAgent.user_id == user.id, DismissedShadowAgent.agent_id == agent_id)
        .first()
    )
    if existing:
        return DismissResponse(agent_id=agent_id, dismissed=True)

    dismissed = DismissedShadowAgent(agent_id=agent_id, user_id=user.id)
    db.add(dismissed)
    db.commit()

    logger.info("Shadow agent dismissed: agent_id=%s user_id=%s", agent_id, user.id)

    return DismissResponse(agent_id=agent_id, dismissed=True)


@router.delete(
    "/{agent_id}/dismiss",
    status_code=204,
    summary="Un-dismiss a shadow agent",
)
async def undismiss_shadow_agent(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Restore this shadow agent to the default list view."""
    deleted = (
        db.query(DismissedShadowAgent)
        .filter(DismissedShadowAgent.user_id == user.id, DismissedShadowAgent.agent_id == agent_id)
        .delete()
    )
    db.commit()

    if not deleted:
        raise HTTPException(status_code=404, detail="Agent is not dismissed")

    logger.info("Shadow agent un-dismissed: agent_id=%s user_id=%s", agent_id, user.id)
