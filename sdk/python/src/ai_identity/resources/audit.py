"""Audit resource — query logs, stats, and verify chain integrity."""

from ai_identity._http import HTTPClient
from ai_identity.models.audit import AuditChainVerification, AuditList, AuditStats

BASE = "/api/v1/audit"


class AuditResource:
    """Query tamper-proof audit logs and forensic data."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    async def list(
        self,
        *,
        agent_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditList:
        """List audit log entries with optional agent filter."""
        params = {"agent_id": agent_id, "limit": limit, "offset": offset}
        resp = await self._http.get(BASE, params=params)
        return AuditList.model_validate(resp)

    async def stats(self, *, agent_id: str | None = None) -> AuditStats:
        """Get aggregated audit statistics."""
        params = {"agent_id": agent_id}
        resp = await self._http.get(f"{BASE}/stats", params=params)
        return AuditStats.model_validate(resp)

    async def verify_chain(self, agent_id: str) -> AuditChainVerification:
        """Verify the HMAC chain integrity for an agent's audit log.

        Returns whether the chain is intact and, if not, where it broke.
        """
        resp = await self._http.get(f"{BASE}/verify/{agent_id}")
        return AuditChainVerification.model_validate(resp)
