"""Agent Key management endpoints — create, list, revoke."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.auth.keys import generate_api_key, get_key_prefix, hash_key
from common.models import Agent, AgentKey, AgentStatus, KeyStatus, User, get_db
from common.schemas.agent import (
    AgentKeyCreateResponse,
    AgentKeyListResponse,
    AgentKeyResponse,
)

logger = logging.getLogger("ai_identity.api.keys")

router = APIRouter(prefix="/api/v1/agents/{agent_id}/keys", tags=["keys"])


# ── Helpers ──────────────────────────────────────────────────────────────


def _get_user_agent(db: Session, user: User, agent_id: uuid.UUID) -> Agent:
    """Fetch an agent by ID, scoped to the current user. Raises 404 if not found."""
    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.user_id == user.id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ── POST /api/v1/agents/{agent_id}/keys ──────────────────────────────────


@router.post("", response_model=AgentKeyCreateResponse, status_code=201)
def create_key(
    agent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a new API key for an agent (show-once)."""
    agent = _get_user_agent(db, user, agent_id)

    if agent.status == AgentStatus.revoked.value:
        raise HTTPException(status_code=400, detail="Cannot issue key for a revoked agent")

    # Generate and store the key
    plaintext_key = generate_api_key()
    agent_key = AgentKey(
        agent_id=agent.id,
        key_hash=hash_key(plaintext_key),
        key_prefix=get_key_prefix(plaintext_key),
        status=KeyStatus.active.value,
    )
    db.add(agent_key)
    db.commit()
    db.refresh(agent_key)

    logger.info("Key created for agent %s (key_id=%d)", agent.id, agent_key.id)

    return AgentKeyCreateResponse(
        key=_key_to_response(agent_key),
        api_key=plaintext_key,
    )


# ── GET /api/v1/agents/{agent_id}/keys ───────────────────────────────────


@router.get("", response_model=AgentKeyListResponse)
def list_keys(
    agent_id: uuid.UUID,
    status: str | None = Query(None, pattern="^(active|rotated|revoked)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List keys for an agent — returns prefix + status only, never the full key."""
    agent = _get_user_agent(db, user, agent_id)

    query = db.query(AgentKey).filter(AgentKey.agent_id == agent.id)

    if status:
        query = query.filter(AgentKey.status == status)

    total = query.count()
    keys = query.order_by(AgentKey.created_at.desc()).all()

    return AgentKeyListResponse(
        items=[_key_to_response(k) for k in keys],
        total=total,
    )


# ── DELETE /api/v1/agents/{agent_id}/keys/{key_id} ──────────────────────


@router.delete("/{key_id}", response_model=AgentKeyResponse)
def revoke_key(
    agent_id: uuid.UUID,
    key_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific API key for an agent."""
    agent = _get_user_agent(db, user, agent_id)

    key = (
        db.query(AgentKey)
        .filter(AgentKey.id == key_id, AgentKey.agent_id == agent.id)
        .first()
    )
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    if key.status == KeyStatus.revoked.value:
        raise HTTPException(status_code=400, detail="Key is already revoked")

    key.status = KeyStatus.revoked.value
    db.commit()
    db.refresh(key)

    logger.info("Key revoked: key_id=%d for agent %s", key.id, agent.id)
    return _key_to_response(key)


# ── Response Helper ──────────────────────────────────────────────────────


def _key_to_response(key: AgentKey) -> AgentKeyResponse:
    """Convert an AgentKey model to response schema."""
    return AgentKeyResponse(
        id=key.id,
        agent_id=key.agent_id,
        key_prefix=key.key_prefix,
        status=key.status,
        expires_at=key.expires_at,
        created_at=key.created_at,
    )
