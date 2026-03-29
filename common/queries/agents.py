"""Shared agent query helpers — used by both api/ and gateway/ services."""

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from common.models import Agent, User


def get_user_agent(db: Session, user: User, agent_id: uuid.UUID) -> Agent:
    """Fetch an agent by ID, scoped to the current user or their organization.

    Raises:
        HTTPException(404): If the agent does not exist or is not accessible.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if user.role == "admin":
        return agent

    # Solo agent: must be the owner
    if agent.org_id is None:
        if agent.user_id != user.id:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    # Org agent: user must be in the same org
    if agent.org_id == user.org_id:
        return agent

    raise HTTPException(status_code=404, detail="Agent not found")
