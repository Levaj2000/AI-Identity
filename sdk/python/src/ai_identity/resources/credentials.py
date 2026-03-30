"""Credentials resource — store, list, rotate, and revoke upstream API keys."""

from ai_identity._http import HTTPClient
from ai_identity.models.credentials import (
    Credential,
    CredentialCreate,
    CredentialCreateResponse,
    CredentialList,
    CredentialRotate,
)


def _base(agent_id: str) -> str:
    return f"/api/v1/agents/{agent_id}/credentials"


class CredentialsResource:
    """Manage encrypted upstream credentials for agents."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    async def create(
        self,
        agent_id: str,
        *,
        provider: str,
        api_key: str,
        label: str | None = None,
    ) -> CredentialCreateResponse:
        """Store an upstream API key. It is encrypted at rest and never exposed again."""
        data = CredentialCreate(provider=provider, api_key=api_key, label=label)
        resp = await self._http.post(_base(agent_id), json=data.model_dump(exclude_none=True))
        return CredentialCreateResponse.model_validate(resp)

    async def list(self, agent_id: str) -> CredentialList:
        """List all credentials for an agent (metadata only, never the key)."""
        resp = await self._http.get(_base(agent_id))
        return CredentialList.model_validate(resp)

    async def rotate(self, agent_id: str, credential_id: int, *, api_key: str) -> Credential:
        """Rotate a credential's upstream API key."""
        data = CredentialRotate(api_key=api_key)
        resp = await self._http.put(
            f"{_base(agent_id)}/{credential_id}/rotate",
            json=data.model_dump(),
        )
        return Credential.model_validate(resp)

    async def revoke(self, agent_id: str, credential_id: int) -> Credential:
        """Revoke an upstream credential."""
        resp = await self._http.delete(f"{_base(agent_id)}/{credential_id}")
        return Credential.model_validate(resp)
