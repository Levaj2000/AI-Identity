"""Admin router — platform stats, user management, system health.

All endpoints require admin role (user.role == "admin").
"""

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from api.app.auth import require_admin
from common.models import User, get_db
from common.models.agent import Agent, AgentStatus
from common.models.agent_key import AgentKey
from common.models.audit_log import AuditLog
from common.models.user import TIER_QUOTAS
from common.schemas.admin import (
    AdminAgentListResponse,
    AdminAgentSummary,
    AdminHealthResponse,
    AdminStatsResponse,
    AdminTierUpdate,
    AdminUserAgent,
    AdminUserAuditEntry,
    AdminUserDetail,
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


class CreateUserRequest(BaseModel):
    """Request body for creating a new user."""

    email: str
    role: str = "owner"
    tier: str = "free"


@router.post(
    "/users",
    response_model=AdminUserSummary,
    status_code=201,
    summary="Create a new user (admin)",
)
async def create_user(
    body: CreateUserRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserSummary:
    """Provision a new user account.

    Used to onboard design partners and create test accounts.
    The user's email serves as their API key (MVP auth).
    """
    email = body.email.strip().lower()

    # Check if user already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    user = User(
        id=uuid.uuid4(),
        email=email,
        role=body.role,
        tier=body.tier,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("Admin created user: %s (%s, tier=%s)", email, user.id, body.tier)

    return AdminUserSummary(
        id=str(user.id),
        email=user.email,
        role=user.role,
        tier=user.tier,
        requests_this_month=0,
        agent_count=0,
        has_subscription=False,
        stripe_customer_id=None,
        created_at=user.created_at,
    )


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


# ── User Detail ────────────────────────────────────────────────────


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetail,
    summary="Get detailed user profile (admin)",
)
async def get_user_detail(
    user_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserDetail:
    """Return full user profile with agents and recent audit logs."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Agents with key counts
    key_count_sq = (
        db.query(AgentKey.agent_id, func.count(AgentKey.id).label("key_count"))
        .group_by(AgentKey.agent_id)
        .subquery()
    )
    agent_rows = (
        db.query(Agent, func.coalesce(key_count_sq.c.key_count, 0))
        .outerjoin(key_count_sq, Agent.id == key_count_sq.c.agent_id)
        .filter(Agent.user_id == user.id)
        .order_by(Agent.created_at.desc())
        .all()
    )
    agents = [
        AdminUserAgent(
            id=str(agent.id),
            name=agent.name,
            status=agent.status,
            key_count=key_count,
            created_at=agent.created_at,
        )
        for agent, key_count in agent_rows
    ]

    # Build agent name lookup for audit logs
    agent_name_map = {str(a.id): a.name for a, _ in agent_rows}

    # Recent audit logs (last 50)
    audit_rows = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(50)
        .all()
    )
    recent_audit_logs = [
        AdminUserAuditEntry(
            id=entry.id,
            agent_id=str(entry.agent_id),
            agent_name=agent_name_map.get(str(entry.agent_id)),
            endpoint=entry.endpoint,
            method=entry.method,
            decision=entry.decision,
            latency_ms=entry.latency_ms,
            created_at=entry.created_at,
        )
        for entry in audit_rows
    ]

    quotas = TIER_QUOTAS.get(user.tier, TIER_QUOTAS["free"])

    return AdminUserDetail(
        id=str(user.id),
        email=user.email,
        role=user.role,
        tier=user.tier,
        requests_this_month=user.requests_this_month,
        agent_count=len(agents),
        has_subscription=user.stripe_subscription_id is not None,
        stripe_customer_id=user.stripe_customer_id,
        stripe_subscription_id=user.stripe_subscription_id,
        welcome_email_sent_at=user.welcome_email_sent_at,
        followup_email_sent_at=user.followup_email_sent_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        quotas=quotas,
        agents=agents,
        recent_audit_logs=recent_audit_logs,
    )


# ── Agent Management ──────────────────────────────────────────────


@router.get(
    "/agents",
    response_model=AdminAgentListResponse,
    summary="List all agents with owner info",
)
async def list_agents(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by agent name"),
) -> AdminAgentListResponse:
    """Return paginated list of agents with owner email and key counts."""
    # Subquery: count keys per agent
    key_count_sq = (
        db.query(AgentKey.agent_id, func.count(AgentKey.id).label("key_count"))
        .group_by(AgentKey.agent_id)
        .subquery()
    )

    query = (
        db.query(Agent, User.email, func.coalesce(key_count_sq.c.key_count, 0))
        .join(User, Agent.user_id == User.id)
        .outerjoin(key_count_sq, Agent.id == key_count_sq.c.agent_id)
    )

    if status:
        query = query.filter(Agent.status == status)
    if search:
        query = query.filter(Agent.name.ilike(f"%{search}%"))

    total = query.count()
    rows = query.order_by(Agent.created_at.desc()).offset(offset).limit(limit).all()

    items = [
        AdminAgentSummary(
            id=str(agent.id),
            name=agent.name,
            status=agent.status,
            owner_email=owner_email,
            key_count=key_count,
            created_at=agent.created_at,
        )
        for agent, owner_email, key_count in rows
    ]

    return AdminAgentListResponse(items=items, total=total, limit=limit, offset=offset)


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
