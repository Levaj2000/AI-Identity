"""AI Identity SDK client."""

from __future__ import annotations

import asyncio
from typing import Any

from ai_identity._http import HTTPClient
from ai_identity.resources.agents import AgentsResource
from ai_identity.resources.audit import AuditResource
from ai_identity.resources.credentials import CredentialsResource
from ai_identity.resources.keys import KeysResource
from ai_identity.resources.policies import PoliciesResource

DEFAULT_BASE_URL = "https://api.ai-identity.co"


class AIIdentityClient:
    """Async client for the AI Identity API.

    Usage::

        async with AIIdentityClient(api_key="aid_sk_...") as client:
            agent = await client.agents.create(name="my-agent")
            print(agent.agent.id)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._http = HTTPClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self.agents = AgentsResource(self._http)
        self.keys = KeysResource(self._http)
        self.policies = PoliciesResource(self._http)
        self.credentials = CredentialsResource(self._http)
        self.audit = AuditResource(self._http)

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.close()

    async def __aenter__(self) -> AIIdentityClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


class SyncAIIdentityClient:
    """Synchronous wrapper around AIIdentityClient.

    Convenience for scripts and notebooks that don't use async/await::

        client = SyncAIIdentityClient(api_key="aid_sk_...")
        agents = client.agents.list()
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._async_client = AIIdentityClient(api_key, base_url=base_url, timeout=timeout)
        self.agents = _SyncWrapper(self._async_client.agents)
        self.keys = _SyncWrapper(self._async_client.keys)
        self.policies = _SyncWrapper(self._async_client.policies)
        self.credentials = _SyncWrapper(self._async_client.credentials)
        self.audit = _SyncWrapper(self._async_client.audit)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        asyncio.get_event_loop().run_until_complete(self._async_client.close())

    def __enter__(self) -> SyncAIIdentityClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class _SyncWrapper:
    """Wraps an async resource, making every async method callable synchronously."""

    def __init__(self, resource: Any) -> None:
        self._resource = resource

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._resource, name)
        if callable(attr):

            def sync_method(*args: Any, **kwargs: Any) -> Any:
                return asyncio.get_event_loop().run_until_complete(attr(*args, **kwargs))

            return sync_method
        return attr
