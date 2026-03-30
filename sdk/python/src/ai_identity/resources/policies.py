"""Policies resource — create and list agent policies."""

from ai_identity._http import HTTPClient
from ai_identity.models.policies import Policy, PolicyCreate


def _base(agent_id: str) -> str:
    return f"/api/v1/agents/{agent_id}/policies"


class PoliciesResource:
    """Manage fail-closed gateway policies for agents."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    async def create(self, agent_id: str, *, rules: dict) -> Policy:
        """Create a new policy for an agent.

        Rules define what the agent can and cannot do. The gateway enforces
        these rules before requests reach the model provider.
        """
        data = PolicyCreate(rules=rules)
        resp = await self._http.post(_base(agent_id), json=data.model_dump())
        return Policy.model_validate(resp)

    async def list(self, agent_id: str) -> list[Policy]:
        """List all policies for an agent."""
        resp = await self._http.get(_base(agent_id))
        if isinstance(resp, list):
            return [Policy.model_validate(p) for p in resp]
        # Handle paginated response
        items = resp.get("items", resp)
        return [Policy.model_validate(p) for p in items]
