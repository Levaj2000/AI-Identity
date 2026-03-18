"""Agent CRUD endpoints — create, read, update, list, delete."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from api.app.quota import check_agent_quota
from common.audit.writer import create_audit_entry
from common.auth.keys import generate_api_key, get_key_prefix, hash_key
from common.models import Agent, AgentKey, AgentStatus, KeyStatus, KeyType, User, get_db
from common.queries import get_user_agent
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


@router.post(
    "",
    response_model=AgentCreateResponse,
    status_code=201,
    summary="Create agent",
    response_description="The created agent with a show-once API key",
    responses={
        422: {"description": "Validation error (e.g. missing name, invalid capabilities type)"},
    },
)
def create_agent(
    body: AgentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new AI agent with an initial API key.

    The response includes a plaintext `api_key` that starts with `aid_sk_`.
    **Store it immediately** — it is only shown once and cannot be retrieved later.

    The agent starts with `status=active` and can optionally include
    `capabilities` (list) and `metadata` (dict).
    """
    # Enforce tier quota on agent creation
    check_agent_quota(db, user)

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

    # Generate the initial API key (always runtime — admin keys must be created explicitly)
    plaintext_key = generate_api_key(key_type=KeyType.runtime.value)
    agent_key = AgentKey(
        agent_id=agent.id,
        key_hash=hash_key(plaintext_key),
        key_prefix=get_key_prefix(plaintext_key),
        key_type=KeyType.runtime.value,
        status=KeyStatus.active.value,
    )
    db.add(agent_key)

    db.commit()
    db.refresh(agent)

    logger.info("Agent created: %s (%s) by user %s", agent.name, agent.id, user.id)

    create_audit_entry(
        db,
        agent_id=agent.id,
        endpoint="/api/v1/agents",
        method="POST",
        decision="allowed",
        user_id=user.id,
        request_metadata={
            "action_type": "agent_created",
            "resource_type": "agent",
            "agent_name": agent.name,
        },
    )

    return AgentCreateResponse(
        agent=_agent_to_response(agent),
        api_key=plaintext_key,
    )


# ── GET /api/v1/agents ──────────────────────────────────────────────────


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List agents",
    response_description="Paginated list of agents",
)
def list_agents(
    status: str | None = Query(
        None,
        pattern="^(active|suspended|revoked)$",
        description="Filter by agent status",
    ),
    capability: str | None = Query(
        None,
        min_length=1,
        max_length=100,
        description="Filter agents that have this capability (e.g. `chat_completion`)",
    ),
    limit: int = Query(20, ge=1, le=100, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all agents belonging to the current user.

    Supports filtering by `status` and/or `capability`, with pagination
    via `limit` and `offset`. Results are ordered by creation date (newest first).
    """
    query = db.query(Agent).filter(Agent.user_id == user.id)

    if status:
        query = query.filter(Agent.status == status)

    if capability:
        # Cross-compatible filter: works with both PostgreSQL JSONB and SQLite JSON
        query = query.filter(cast(Agent.capabilities, String).contains(f'"{capability}"'))

    total = query.count()
    agents = query.order_by(Agent.created_at.desc()).offset(offset).limit(limit).all()

    return AgentListResponse(
        items=[_agent_to_response(a) for a in agents],
        total=total,
        limit=limit,
        offset=offset,
    )


# ── GET /api/v1/agents/{agent_id} ───────────────────────────────────────


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent",
    response_description="Full agent details",
    responses={
        404: {"description": "Agent not found or belongs to another user"},
    },
)
def get_agent(
    agent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single agent by ID.

    Returns the full agent record including capabilities and metadata.
    The agent must belong to the authenticated user.
    """
    agent = get_user_agent(db, user, agent_id)
    return _agent_to_response(agent)


# ── PUT /api/v1/agents/{agent_id} ───────────────────────────────────────


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent",
    response_description="The updated agent",
    responses={
        400: {"description": "Cannot update a revoked agent"},
        404: {"description": "Agent not found or belongs to another user"},
        422: {"description": "Validation error or no fields provided"},
    },
)
def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an agent's name, description, capabilities, metadata, or status.

    Only include the fields you want to change — omitted fields are left unchanged.
    Capabilities and metadata are replaced entirely (not merged).
    Revoked agents cannot be updated.
    """
    agent = get_user_agent(db, user, agent_id)

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

    create_audit_entry(
        db,
        agent_id=agent.id,
        endpoint=f"/api/v1/agents/{agent.id}",
        method="PUT",
        decision="allowed",
        user_id=user.id,
        request_metadata={
            "action_type": "agent_updated",
            "resource_type": "agent",
            "agent_name": agent.name,
        },
    )

    return _agent_to_response(agent)


# ── DELETE /api/v1/agents/{agent_id} ────────────────────────────────────


@router.delete(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Revoke agent",
    response_description="The revoked agent",
    responses={
        400: {"description": "Agent is already revoked"},
        404: {"description": "Agent not found or belongs to another user"},
    },
)
def delete_agent(
    agent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete an agent by setting its status to revoked.

    All active and rotated API keys for the agent are immediately revoked.
    The agent record is preserved for audit purposes but can no longer be
    updated or issued new keys.
    """
    agent = get_user_agent(db, user, agent_id)

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

    logger.info("Agent revoked: %s (%s) — %d keys revoked", agent.name, agent.id, revoked_count)

    create_audit_entry(
        db,
        agent_id=agent.id,
        endpoint=f"/api/v1/agents/{agent.id}",
        method="DELETE",
        decision="allowed",
        user_id=user.id,
        request_metadata={
            "action_type": "agent_revoked",
            "resource_type": "agent",
            "agent_name": agent.name,
            "old_status": "active",
            "new_status": "revoked",
            "keys_revoked": str(revoked_count),
        },
    )

    return _agent_to_response(agent)


# ── Helpers ──────────────────────────────────────────────────────────────


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
