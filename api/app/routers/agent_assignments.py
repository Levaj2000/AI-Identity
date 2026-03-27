"""Agent assignment CRUD — assign users to specific agents with roles."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import Agent, User, get_db
from common.models.agent_assignment import AgentAssignment
from common.models.org_membership import OrgMembership
from common.schemas.organization import (
    AgentAssignmentCreate,
    AgentAssignmentResponse,
    AgentAssignmentUpdate,
)

logger = logging.getLogger("ai_identity.api.agent_assignments")

router = APIRouter(prefix="/api/v1/agents", tags=["agent-assignments"])


# ── Helpers ───────────────────────────────────────────────────────────


def _require_agent_admin(db: Session, user: User, agent_id: uuid.UUID) -> Agent:
    """Require the user to be the agent creator, an org admin/owner, or a platform admin.

    Returns the agent if authorized, raises 403/404 otherwise.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Platform admin
    if user.role == "admin":
        return agent

    # Agent creator
    if agent.user_id == user.id:
        return agent

    # Org admin/owner for org agents
    if agent.org_id and user.org_id == agent.org_id:
        membership = (
            db.query(OrgMembership)
            .filter(
                OrgMembership.org_id == user.org_id,
                OrgMembership.user_id == user.id,
            )
            .first()
        )
        if membership and membership.role in ("owner", "admin"):
            return agent

    raise HTTPException(status_code=403, detail="Insufficient access to manage agent assignments")


# ── POST /api/v1/agents/{agent_id}/assignments ───────────────────────


@router.post(
    "/{agent_id}/assignments",
    response_model=AgentAssignmentResponse,
    status_code=201,
    summary="Assign user to agent",
)
def create_assignment(
    agent_id: uuid.UUID,
    body: AgentAssignmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assign a user to an agent with a specific role.

    Requires agent owner, org admin/owner, or platform admin.
    """
    _require_agent_admin(db, user, agent_id)

    # Verify target user exists
    target = db.query(User).filter(User.id == body.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for existing assignment
    existing = (
        db.query(AgentAssignment)
        .filter(
            AgentAssignment.agent_id == agent_id,
            AgentAssignment.user_id == body.user_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already assigned to this agent")

    assignment = AgentAssignment(
        id=uuid.uuid4(),
        agent_id=agent_id,
        user_id=body.user_id,
        role=body.role,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    logger.info(
        "Agent assignment created: user %s -> agent %s with role %s",
        body.user_id,
        agent_id,
        body.role,
    )
    return AgentAssignmentResponse(
        user_id=target.id,
        email=target.email,
        role=assignment.role,
        created_at=assignment.created_at,
    )


# ── GET /api/v1/agents/{agent_id}/assignments ────────────────────────


@router.get(
    "/{agent_id}/assignments",
    response_model=list[AgentAssignmentResponse],
    summary="List agent assignments",
)
def list_assignments(
    agent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all user assignments for an agent.

    The caller must have access to the agent (creator, org member, or admin).
    """
    # Verify agent access
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if user.role != "admin":
        has_access = agent.user_id == user.id or (agent.org_id and agent.org_id == user.org_id)
        if not has_access:
            raise HTTPException(status_code=404, detail="Agent not found")

    assignments = (
        db.query(AgentAssignment)
        .filter(AgentAssignment.agent_id == agent_id)
        .order_by(AgentAssignment.created_at)
        .all()
    )

    results = []
    for a in assignments:
        assigned_user = db.query(User).filter(User.id == a.user_id).first()
        if assigned_user:
            results.append(
                AgentAssignmentResponse(
                    user_id=a.user_id,
                    email=assigned_user.email,
                    role=a.role,
                    created_at=a.created_at,
                )
            )

    return results


# ── PATCH /api/v1/agents/{agent_id}/assignments/{user_id} ────────────


@router.patch(
    "/{agent_id}/assignments/{user_id}",
    response_model=AgentAssignmentResponse,
    summary="Update assignment role",
)
def update_assignment(
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    body: AgentAssignmentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change an agent assignment role.

    Requires agent owner, org admin/owner, or platform admin.
    """
    _require_agent_admin(db, user, agent_id)

    assignment = (
        db.query(AgentAssignment)
        .filter(
            AgentAssignment.agent_id == agent_id,
            AgentAssignment.user_id == user_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment.role = body.role
    db.commit()
    db.refresh(assignment)

    assigned_user = db.query(User).filter(User.id == user_id).first()
    logger.info(
        "Agent assignment updated: user %s -> agent %s role %s",
        user_id,
        agent_id,
        body.role,
    )
    return AgentAssignmentResponse(
        user_id=assignment.user_id,
        email=assigned_user.email if assigned_user else "",
        role=assignment.role,
        created_at=assignment.created_at,
    )


# ── DELETE /api/v1/agents/{agent_id}/assignments/{user_id} ───────────


@router.delete(
    "/{agent_id}/assignments/{user_id}",
    status_code=200,
    summary="Remove assignment",
)
def remove_assignment(
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a user's assignment from an agent.

    Requires agent owner, org admin/owner, or platform admin.
    """
    _require_agent_admin(db, user, agent_id)

    assignment = (
        db.query(AgentAssignment)
        .filter(
            AgentAssignment.agent_id == agent_id,
            AgentAssignment.user_id == user_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()

    logger.info("Agent assignment removed: user %s from agent %s", user_id, agent_id)
    return {"detail": "Assignment removed"}
