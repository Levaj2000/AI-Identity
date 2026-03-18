"""Admin router — platform stats, user management, system health.

All endpoints require admin role (user.role == "admin").
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from api.app.auth import require_admin
from common.models import User, get_db
from common.models.agent import Agent, AgentStatus
from common.models.audit_log import AuditLog
from common.schemas.admin import (
    AdminHealthResponse,
    AdminStatsResponse,
    AdminTierUpdate,
    AdminUserListResponse,
    AdminUserSummary,
)

logger = logging.getLogger("ai_identity.api.admin")

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── Platform Stats ───────────────────────────────────────────────────


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Platform-wide statistics",
)
async def get_platform_stats(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminStatsResponse:
    """Return aggregate platform stats: users, agents, requests by tier/status."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_agents = db.query(func.count(Agent.id)).scalar() or 0
    total_active = (
        db.query(func.count(Agent.id)).filter(Agent.status == AgentStatus.active.value).scalar()
        or 0
    )
    total_requests = db.query(func.coalesce(func.sum(User.requests_this_month), 0)).scalar() or 0

    # Users by tier
    tier_rows = db.query(User.tier, func.count(User.id)).group_by(User.tier).all()
    users_by_tier = {tier: count for tier, count in tier_rows}

    # Agents by status
    status_rows = db.query(Agent.status, func.count(Agent.id)).group_by(Agent.status).all()
    agents_by_status = {status: count for status, count in status_rows}

    return AdminStatsResponse(
        total_users=total_users,
        total_agents=total_agents,
        total_active_agents=total_active,
        total_requests=total_requests,
        users_by_tier=users_by_tier,
        agents_by_status=agents_by_status,
    )


# ── User Management ─────────────────────────────────────────────────


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List all users with usage info",
)
async def list_users(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tier: str | None = Query(None, description="Filter by tier"),
    search: str | None = Query(None, description="Search by email"),
) -> AdminUserListResponse:
    """Return paginated list of users with agent counts."""
    # Subquery: count agents per user
    agent_count_sq = (
        db.query(Agent.user_id, func.count(Agent.id).label("agent_count"))
        .group_by(Agent.user_id)
        .subquery()
    )

    query = db.query(User, func.coalesce(agent_count_sq.c.agent_count, 0)).outerjoin(
        agent_count_sq, User.id == agent_count_sq.c.user_id
    )

    if tier:
        query = query.filter(User.tier == tier)
    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))

    total = query.count()
    rows = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    items = [
        AdminUserSummary(
            id=str(user.id),
            email=user.email,
            role=user.role,
            tier=user.tier,
            requests_this_month=user.requests_this_month,
            agent_count=agent_count,
            has_subscription=user.stripe_subscription_id is not None,
            stripe_customer_id=user.stripe_customer_id,
            created_at=user.created_at,
        )
        for user, agent_count in rows
    ]

    return AdminUserListResponse(items=items, total=total, limit=limit, offset=offset)


@router.patch(
    "/users/{user_id}/tier",
    response_model=AdminUserSummary,
    summary="Change a user's tier (admin override)",
)
async def update_user_tier(
    user_id: str,
    body: AdminTierUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserSummary:
    """Override a user's tier. Does NOT sync with Stripe — manual admin action."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_tier = user.tier
    user.tier = body.tier.value
    db.commit()
    db.refresh(user)

    agent_count = db.query(func.count(Agent.id)).filter(Agent.user_id == user.id).scalar() or 0

    logger.info(
        "Admin tier change: user %s (%s) %s → %s",
        user.id,
        user.email,
        old_tier,
        body.tier.value,
    )

    return AdminUserSummary(
        id=str(user.id),
        email=user.email,
        role=user.role,
        tier=user.tier,
        requests_this_month=user.requests_this_month,
        agent_count=agent_count,
        has_subscription=user.stripe_subscription_id is not None,
        stripe_customer_id=user.stripe_customer_id,
        created_at=user.created_at,
    )


# ── System Health ────────────────────────────────────────────────────


@router.get(
    "/health",
    response_model=AdminHealthResponse,
    summary="System health metrics",
)
async def get_system_health(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminHealthResponse:
    """Return system health: DB latency and table row counts."""
    # DB latency
    start = time.perf_counter()
    db.execute(text("SELECT 1"))
    db_latency_ms = round((time.perf_counter() - start) * 1000, 2)

    # Table counts
    table_counts = {}
    for model, name in [(User, "users"), (Agent, "agents"), (AuditLog, "audit_logs")]:
        table_counts[name] = db.query(func.count(model.id)).scalar() or 0

    return AdminHealthResponse(
        status="healthy",
        db_latency_ms=db_latency_ms,
        table_counts=table_counts,
    )
