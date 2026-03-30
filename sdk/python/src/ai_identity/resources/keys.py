"""Keys resource — create, list, rotate, and revoke agent API keys."""

from ai_identity._http import HTTPClient
from ai_identity.models.keys import (
    AgentKey,
    AgentKeyCreateResponse,
    AgentKeyList,
    AgentKeyRotateResponse,
)


def _base(agent_id: str) -> str:
    return f"/api/v1/agents/{agent_id}/keys"


class KeysResource:
    """Manage cryptographic API keys for agents."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    async def create(self, agent_id: str) -> AgentKeyCreateResponse:
        """Issue a new API key for an agent.

        Store the returned ``api_key`` securely — it cannot be retrieved again.
        """
        resp = await self._http.post(_base(agent_id))
        return AgentKeyCreateResponse.model_validate(resp)

    async def list(self, agent_id: str) -> AgentKeyList:
        """List all keys for an agent (prefixes and status only)."""
        resp = await self._http.get(_base(agent_id))
        return AgentKeyList.model_validate(resp)

    async def rotate(self, agent_id: str, key_id: int) -> AgentKeyRotateResponse:
        """Rotate a key. The old key enters a 24-hour grace period."""
        resp = await self._http.post(f"{_base(agent_id)}/{key_id}/rotate")
        return AgentKeyRotateResponse.model_validate(resp)

    async def revoke(self, agent_id: str, key_id: int) -> AgentKey:
        """Revoke a key immediately."""
        resp = await self._http.delete(f"{_base(agent_id)}/{key_id}")
        return AgentKey.model_validate(resp)
