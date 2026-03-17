"""Quota enforcement — tier-based limits on agents, keys, credentials, and requests.

Usage in routers:
    from api.app.quota import check_agent_quota, check_key_quota, check_request_quota

    # Before creating an agent:
    check_agent_quota(db, user)

    # Before creating a key:
    check_key_quota(db, user, agent_id)

    # On each gateway request (called from gateway):
    check_request_quota(db, user)
"""

import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from common.models import Agent, AgentKey, AgentStatus, KeyStatus, User
from common.models.upstream_credential import CredentialStatus, UpstreamCredential

logger = logging.getLogger("ai_identity.api.quota")


class QuotaExceeded(HTTPException):
    """Raised when a user exceeds their tier quota."""

    def __init__(self, resource: str, limit: int, current: int, tier: str):
        detail = (
            f"Quota exceeded: {resource}. "
            f"Your {tier} plan allows {limit}, you have {current}. "
            f"Upgrade your plan at https://ai-identity.co/#pricing"
        )
        super().__init__(status_code=429, detail=detail)
        self.resource = resource
        self.limit = limit
        self.current = current


def check_agent_quota(db: Session, user: User) -> None:
    """Raise 429 if user has reached their max_agents limit."""
    quotas = user.quotas
    max_agents = quotas["max_agents"]

    if max_agents == -1:  # unlimited
        return

    current_count = (
        db.query(Agent)
        .filter(Agent.user_id == user.id, Agent.status != AgentStatus.revoked.value)
        .count()
    )

    if current_count >= max_agents:
        raise QuotaExceeded("agents", max_agents, current_count, user.tier)

    logger.debug("Agent quota check: %d/%d (%s tier)", current_count, max_agents, user.tier)


def check_key_quota(db: Session, user: User, agent_id) -> None:
    """Raise 429 if agent has reached the max_keys_per_agent limit."""
    quotas = user.quotas
    max_keys = quotas["max_keys_per_agent"]

    if max_keys == -1:  # unlimited
        return

    current_count = (
        db.query(AgentKey)
        .filter(AgentKey.agent_id == agent_id, AgentKey.status == KeyStatus.active.value)
        .count()
    )

    if current_count >= max_keys:
        raise QuotaExceeded("keys per agent", max_keys, current_count, user.tier)


def check_credential_quota(db: Session, user: User) -> None:
    """Raise 429 if user has reached their max_credentials limit."""
    quotas = user.quotas
    max_creds = quotas["max_credentials"]

    if max_creds == -1:  # unlimited
        return

    # Count active credentials across all user's agents
    current_count = (
        db.query(UpstreamCredential)
        .join(Agent, UpstreamCredential.agent_id == Agent.id)
        .filter(
            Agent.user_id == user.id,
            UpstreamCredential.status == CredentialStatus.active.value,
        )
        .count()
    )

    if current_count >= max_creds:
        raise QuotaExceeded("upstream credentials", max_creds, current_count, user.tier)


def check_request_quota(db: Session, user: User) -> None:
    """Raise 429 if user has exceeded monthly request quota.

    Also handles monthly counter reset when the reset day is reached.
    """
    quotas = user.quotas
    max_requests = quotas["max_requests_per_month"]

    if max_requests == -1:  # unlimited
        return

    # Check if we need to reset the monthly counter
    now = datetime.now(UTC)
    if user.updated_at and user.updated_at.month != now.month:
        user.requests_this_month = 0
        db.commit()

    if user.requests_this_month >= max_requests:
        raise QuotaExceeded(
            "requests this month", max_requests, user.requests_this_month, user.tier
        )


def increment_request_count(db: Session, user: User) -> None:
    """Increment the user's monthly request counter."""
    user.requests_this_month = (user.requests_this_month or 0) + 1
    db.commit()


def get_usage_summary(db: Session, user: User) -> dict:
    """Return current usage vs limits for the user's tier."""
    quotas = user.quotas

    active_agents = (
        db.query(Agent)
        .filter(Agent.user_id == user.id, Agent.status != AgentStatus.revoked.value)
        .count()
    )

    total_active_keys = (
        db.query(AgentKey)
        .join(Agent, AgentKey.agent_id == Agent.id)
        .filter(Agent.user_id == user.id, AgentKey.status == KeyStatus.active.value)
        .count()
    )

    active_credentials = (
        db.query(UpstreamCredential)
        .join(Agent, UpstreamCredential.agent_id == Agent.id)
        .filter(
            Agent.user_id == user.id,
            UpstreamCredential.status == CredentialStatus.active.value,
        )
        .count()
    )

    def _fmt(current: int, limit: int) -> dict:
        return {
            "current": current,
            "limit": limit if limit != -1 else None,
            "unlimited": limit == -1,
            "percentage": round(current / limit * 100, 1) if limit > 0 else 0.0,
        }

    return {
        "tier": user.tier,
        "agents": _fmt(active_agents, quotas["max_agents"]),
        "active_keys": _fmt(
            total_active_keys, quotas["max_keys_per_agent"] * max(active_agents, 1)
        ),
        "credentials": _fmt(active_credentials, quotas["max_credentials"]),
        "requests_this_month": _fmt(
            user.requests_this_month or 0, quotas["max_requests_per_month"]
        ),
        "audit_retention_days": quotas["audit_retention_days"],
    }
