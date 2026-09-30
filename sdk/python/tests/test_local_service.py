"""The Python SDK can exercise its HTTP path without a hosted API."""

import asyncio

import httpx
from ai_identity import AIIdentityClient


def test_agent_list_uses_configured_local_url(monkeypatch):
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "127.0.0.1"
        assert request.url.path == "/api/v1/agents"
        assert request.url.params["limit"] == "3"
        assert request.url.params["offset"] == "2"
        assert request.headers["X-API-Key"] == "aid_sk_local_only"
        return httpx.Response(200, json={"items": [], "total": 0, "limit": 3, "offset": 2})

    original_client = httpx.AsyncClient

    def local_client(*args, **kwargs):
        return original_client(*args, transport=httpx.MockTransport(respond), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", local_client)

    async def run():
        async with AIIdentityClient(
            api_key="aid_sk_local_only", base_url="http://127.0.0.1:4020"
        ) as client:
            result = await client.agents.list(limit=3, offset=2)
            assert result.total == 0
            assert result.items == []
            assert result.limit == 3
            assert result.offset == 2

    asyncio.run(run())
