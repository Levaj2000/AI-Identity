"""Agent CRUD endpoints — create, read, update, list, delete."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.auth.keys import generate_api_key, get_key_prefix, hash_key
from common.models import Agent, AgentKey, AgentStatus, KeyStatus, User, get_db
from common.schemas.agent import (
    AgentCreate,
    AgentCreateResponse,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)

logger = logging.getLogger("ai_identity.api.agents")

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


# ── POST /api/v1/agents ─────────────────────────────────────────────────


@router.post("", response_model=AgentCreateResponse, status_code=201)
def create_agent(
    body: AgentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new agent with an initial API key (show-once)."""
    agent = Agent(
        id=uuid.uuid4(),
        user_id=user.id,
        name=body.name,
        description=body.description,
        status=AgentStatus.active.value,
        capabilities=body.capabilities,
        metadata_=body.metadata,
    )
    db.add(agent)

    # Generate the initial API key
    plaintext_key = generate_api_key()
    agent_key = AgentKey(
        agent_id=agent.id,
        key_hash=hash_key(plaintext_key),
        key_prefix=get_key_prefix(plaintext_key),
        status=KeyStatus.active.value,
    )
    db.add(agent_key)

    db.commit()
    db.refresh(agent)

    logger.info("Agent created: %s (%s) by user %s", agent.name, agent.id, user.id)

    return AgentCreateResponse(
        agent=_agent_to_response(agent),
        api_key=plaintext_key,
    )


# ── GET /api/v1/agents ──────────────────────────────────────────────────


@router.get("", response_model=AgentListResponse)
def list_agents(
    status: str | None = Query(None, pattern="^(active|suspended|revoked)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List agents for the current user, with optional status filter and pagination."""
    query = db.query(Agent).filter(Agent.user_id == user.id)

    if status:
        query = query.filter(Agent.status == status)

    total = query.count()
    agents = query.order_by(Agent.created_at.desc()).offset(offset).limit(limit).all()

    return AgentListResponse(
        items=[_agent_to_response(a) for a in agents],
        total=total,
        limit=limit,
        offset=offset,
    )


# ── GET /api/v1/agents/{agent_id} ───────────────────────────────────────


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single agent by ID. Must belong to the current user."""
    agent = _get_user_agent(db, user, agent_id)
    return _agent_to_response(agent)


# ── PUT /api/v1/agents/{agent_id} ───────────────────────────────────────


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an agent's name, description, capabilities, metadata, or status."""
    agent = _get_user_agent(db, user, agent_id)

    if agent.status == AgentStatus.revoked.value:
        raise HTTPException(status_code=400, detail="Cannot update a revoked agent")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")

    # Map schema field 'metadata' to model attribute 'metadata_'
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")

    for field, value in update_data.items():
        setattr(agent, field, value)

    db.commit()
    db.refresh(agent)

    logger.info("Agent updated: %s (%s)", agent.name, agent.id)
    return _agent_to_response(agent)


# ── DELETE /api/v1/agents/{agent_id} ────────────────────────────────────


@router.delete("/{agent_id}", response_model=AgentResponse)
def delete_agent(
    agent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete an agent: set status=revoked and revoke all associated keys."""
    agent = _get_user_agent(db, user, agent_id)

    if agent.status == AgentStatus.revoked.value:
        raise HTTPException(status_code=400, detail="Agent is already revoked")

    # Revoke the agent
    agent.status = AgentStatus.revoked.value

    # Revoke all active/rotated keys
    revoked_count = (
        db.query(AgentKey)
        .filter(
            AgentKey.agent_id == agent.id,
            AgentKey.status.in_([KeyStatus.active.value, KeyStatus.rotated.value]),
        )
        .update({"status": KeyStatus.revoked.value}, synchronize_session="fetch")
    )

    db.commit()
    db.refresh(agent)

    logger.info(
        "Agent revoked: %s (%s) — %d keys revoked", agent.name, agent.id, revoked_count
    )
    return _agent_to_response(agent)


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


def _agent_to_response(agent: Agent) -> AgentResponse:
    """Convert an Agent model to an AgentResponse schema.

    Handles the metadata_ → metadata field name mapping.
    """
    return AgentResponse(
        id=agent.id,
        user_id=agent.user_id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        capabilities=agent.capabilities,
        metadata=agent.metadata_,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )
