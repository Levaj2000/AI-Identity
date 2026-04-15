"""Policy management endpoints — create and list policies for agents."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import Policy, User, get_db
from common.queries import get_user_agent
from common.schemas.agent import PolicyCreate, PolicyResponse
from common.validation.policy import PolicyValidator

logger = logging.getLogger("ai_identity.api.policies")

router = APIRouter(prefix="/api/v1/agents/{agent_id}/policies", tags=["policies"])


# ── POST /api/v1/agents/{agent_id}/policies ─────────────────────────────


@router.post(
    "",
    response_model=PolicyResponse,
    status_code=201,
    summary="Create policy",
    response_description="The created policy",
)
def create_policy(
    agent_id: uuid.UUID,
    body: PolicyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new policy for an agent.

    Only one policy can be active at a time. Creating a new policy
    automatically deactivates any existing active policy for the agent.

    **Rules schema:**
    - `allowed_endpoints` — list of endpoint patterns (`/v1/*`, `*`, exact)
    - `denied_endpoints` — list of explicitly blocked patterns (checked first)
    - `allowed_methods` — list of HTTP methods (`GET`, `POST`, etc.)
    - `max_cost_usd` — optional per-request cost cap
    """
    agent = get_user_agent(db, user, agent_id)

    # Deactivate any existing active policies for this agent.
    db.query(Policy).filter(
        Policy.agent_id == agent.id,
        Policy.is_active.is_(True),
    ).update({"is_active": False})

    # Determine next version number.
    max_version = (
        db.query(Policy.version)
        .filter(Policy.agent_id == agent.id)
        .order_by(Policy.version.desc())
        .first()
    )
    next_version = (max_version[0] + 1) if max_version else 1

    policy = Policy(
        agent_id=agent.id,
        rules=body.rules,
        version=next_version,
        is_active=True,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    logger.info(
        "Policy v%d created for agent %s by user %s",
        policy.version,
        agent.id,
        user.id,
    )

    # Re-validate with the agent's metadata in context to surface non-fatal
    # warnings (e.g., `when` references a metadata key the agent isn't tagged
    # with). The policy is already saved — warnings don't block creation,
    # they're authoring nudges the dashboard renders as yellow flags.
    contextual = PolicyValidator().validate(body.rules, agent_metadata=agent.metadata_ or {})
    warnings = (
        [{"field": w.field, "message": w.message} for w in contextual.warnings]
        if contextual.warnings
        else None
    )

    response = PolicyResponse.model_validate(policy)
    response.warnings = warnings
    return response


# ── GET /api/v1/agents/{agent_id}/policies ──────────────────────────────


@router.get(
    "",
    response_model=list[PolicyResponse],
    summary="List policies",
    response_description="All policies for this agent (newest first)",
)
def list_policies(
    agent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all policies for an agent, ordered by version (newest first)."""
    agent = get_user_agent(db, user, agent_id)
    policies = (
        db.query(Policy).filter(Policy.agent_id == agent.id).order_by(Policy.version.desc()).all()
    )
    return policies


# ── GET /api/v1/agents/{agent_id}/policies/active ───────────────────────


@router.get(
    "/active",
    response_model=PolicyResponse,
    summary="Get active policy",
    response_description="The currently active policy for this agent",
)
def get_active_policy(
    agent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the currently active policy for an agent."""
    agent = get_user_agent(db, user, agent_id)
    policy = (
        db.query(Policy).filter(Policy.agent_id == agent.id, Policy.is_active.is_(True)).first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="No active policy")
    return policy
