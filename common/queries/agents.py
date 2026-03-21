"""Shared agent query helpers — used by both api/ and gateway/ services."""

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from common.models import Agent, User


def get_user_agent(db: Session, user: User, agent_id: uuid.UUID) -> Agent:
    """Fetch an agent by ID, scoped to the current user.

    Raises:
        HTTPException(404): If the agent does not exist or belongs to another user.
    """
    query = db.query(Agent).filter(Agent.id == agent_id)
    if user.role != "admin":
        query = query.filter(Agent.user_id == user.id)
    agent = query.first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
