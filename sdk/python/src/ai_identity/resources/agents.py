"""Agents resource — create, list, get, update, and delete AI agents."""

from ai_identity._http import HTTPClient
from ai_identity.models.agents import (
    Agent,
    AgentCreate,
    AgentCreateResponse,
    AgentList,
    AgentUpdate,
)

BASE = "/api/v1/agents"


class AgentsResource:
    """Manage AI agent identities."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    async def create(
        self,
        *,
        name: str,
        description: str | None = None,
        capabilities: list | None = None,
        metadata: dict | None = None,
    ) -> AgentCreateResponse:
        """Create a new agent and receive a show-once API key.

        Store the returned ``api_key`` securely — it cannot be retrieved again.
        """
        data = AgentCreate(
            name=name,
            description=description,
            capabilities=capabilities or [],
            metadata=metadata or {},
        )
        resp = await self._http.post(BASE, json=data.model_dump(exclude_none=True))
        return AgentCreateResponse.model_validate(resp)

    async def list(
        self,
        *,
        status: str | None = None,
        capability: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AgentList:
        """List agents with optional filters and pagination."""
        params = {
            "status": status,
            "capability": capability,
            "limit": limit,
            "offset": offset,
        }
        resp = await self._http.get(BASE, params=params)
        return AgentList.model_validate(resp)

    async def get(self, agent_id: str) -> Agent:
        """Get a single agent by ID."""
        resp = await self._http.get(f"{BASE}/{agent_id}")
        return Agent.model_validate(resp)

    async def update(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        capabilities: list | None = None,
        metadata: dict | None = None,
        status: str | None = None,
    ) -> Agent:
        """Update an agent. Only include fields you want to change."""
        data = AgentUpdate(
            name=name,
            description=description,
            capabilities=capabilities,
            metadata=metadata,
            status=status,
        )
        resp = await self._http.put(
            f"{BASE}/{agent_id}",
            json=data.model_dump(exclude_none=True),
        )
        return Agent.model_validate(resp)

    async def delete(self, agent_id: str) -> Agent:
        """Revoke (soft-delete) an agent. This is irreversible."""
        resp = await self._http.delete(f"{BASE}/{agent_id}")
        return Agent.model_validate(resp)
