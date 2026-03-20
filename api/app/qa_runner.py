"""QA Runner — automated 15-step E2E checklist for design partner onboarding.

Runs against production (or any environment) to verify the full agent
lifecycle: health → auth → agent CRUD → policy → gateway enforce →
audit → key rotation → cleanup.
"""

import contextlib
import logging
import time
import uuid
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("ai_identity.api.qa_runner")

TIMEOUT = 15.0  # seconds per request


@dataclass
class CheckResult:
    """Result of a single QA check."""

    step: int
    name: str
    section: str
    passed: bool
    duration_ms: int
    details: str
    error: str | None = None


@dataclass
class QARunResult:
    """Result of a full QA run."""

    checks: list[CheckResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    total: int = 0
    duration_ms: int = 0

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.total > 0

    def to_dict(self) -> dict:
        return {
            "checks": [
                {
                    "step": c.step,
                    "name": c.name,
                    "section": c.section,
                    "passed": c.passed,
                    "duration_ms": c.duration_ms,
                    "details": c.details,
                    "error": c.error,
                }
                for c in self.checks
            ],
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
            "duration_ms": self.duration_ms,
            "all_passed": self.all_passed,
        }


def _check(
    result: QARunResult,
    step: int,
    name: str,
    section: str,
    passed: bool,
    duration_ms: int,
    details: str,
    error: str | None = None,
) -> bool:
    """Record a check result and return whether it passed."""
    cr = CheckResult(
        step=step,
        name=name,
        section=section,
        passed=passed,
        duration_ms=duration_ms,
        details=details,
        error=error,
    )
    result.checks.append(cr)
    result.total += 1
    if passed:
        result.passed += 1
    else:
        result.failed += 1
    return passed


async def run_qa_checks(api_url: str, gateway_url: str, api_key: str) -> QARunResult:
    """Run all 15 QA checks and return structured results.

    Creates temporary resources (agent, policy, keys) and cleans them up.
    Safe to run against production — all test data is removed at the end.
    """
    result = QARunResult()
    run_start = time.perf_counter()
    agent_id: str | None = None

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

        # ── 1. API Health ───────────────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.get(f"{api_url}/health")
            data = r.json()
            ok = r.status_code == 200 and data.get("status") == "ok"
            _check(
                result,
                1,
                "API health check",
                "Health & Infrastructure",
                ok,
                _ms(t),
                f"status={data.get('status')}, version={data.get('version')}",
            )
        except Exception as e:
            _check(
                result,
                1,
                "API health check",
                "Health & Infrastructure",
                False,
                _ms(t),
                "Failed to reach API",
                str(e),
            )
            result.duration_ms = _ms(run_start)
            return result  # Can't continue without API

        # ── 2. Gateway Health ───────────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.get(f"{gateway_url}/health")
            data = r.json()
            ok = (
                r.status_code == 200
                and data.get("database") == "connected"
                and data.get("circuit_breaker") == "closed"
            )
            _check(
                result,
                2,
                "Gateway health check",
                "Health & Infrastructure",
                ok,
                _ms(t),
                f"db={data.get('database')}, cb={data.get('circuit_breaker')}",
            )
        except Exception as e:
            _check(
                result,
                2,
                "Gateway health check",
                "Health & Infrastructure",
                False,
                _ms(t),
                "Failed to reach gateway",
                str(e),
            )
            result.duration_ms = _ms(run_start)
            return result  # Can't continue without gateway

        # ── 3. Dashboard reachable ──────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.get("https://dashboard.ai-identity.co", follow_redirects=True)
            ok = r.status_code == 200
            _check(
                result,
                3,
                "Dashboard loads",
                "Health & Infrastructure",
                ok,
                _ms(t),
                f"status={r.status_code}",
            )
        except Exception as e:
            _check(
                result,
                3,
                "Dashboard loads",
                "Health & Infrastructure",
                False,
                _ms(t),
                "Failed to reach dashboard",
                str(e),
            )

        # ── 4. Auth check ───────────────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.get(f"{api_url}/api/v1/auth/me", headers=headers)
            ok = r.status_code == 200
            data = r.json() if ok else {}
            _check(
                result,
                4,
                "Auth / API key valid",
                "Authentication & Agent Lifecycle",
                ok,
                _ms(t),
                f"user={data.get('email', 'unknown')}" if ok else f"status={r.status_code}",
            )
        except Exception as e:
            _check(
                result,
                4,
                "Auth / API key valid",
                "Authentication & Agent Lifecycle",
                False,
                _ms(t),
                "Auth check failed",
                str(e),
            )

        # ── 5. Create agent ─────────────────────────────────────────
        t = time.perf_counter()
        try:
            qa_name = f"QA-{uuid.uuid4().hex[:8]}"
            r = await client.post(
                f"{api_url}/api/v1/agents",
                headers=headers,
                json={
                    "name": qa_name,
                    "description": "Automated QA checklist agent — will be cleaned up",
                    "capabilities": ["chat_completion"],
                    "metadata": {"qa_run": "true"},
                },
            )
            data = r.json()
            ok = r.status_code == 201 and data.get("agent", {}).get("status") == "active"
            if ok:
                agent_id = data["agent"]["id"]
            _check(
                result,
                5,
                "Create agent",
                "Authentication & Agent Lifecycle",
                ok,
                _ms(t),
                f"agent_id={agent_id}" if ok else f"status={r.status_code}",
            )
        except Exception as e:
            _check(
                result,
                5,
                "Create agent",
                "Authentication & Agent Lifecycle",
                False,
                _ms(t),
                "Failed to create agent",
                str(e),
            )

        if not agent_id:
            result.duration_ms = _ms(run_start)
            return result  # Can't continue without agent

        # ── 6. List agents ──────────────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.get(f"{api_url}/api/v1/agents?limit=50", headers=headers)
            data = r.json()
            found = any(a["id"] == agent_id for a in data.get("items", []))
            ok = r.status_code == 200 and found
            _check(
                result,
                6,
                "List agents (find QA agent)",
                "Authentication & Agent Lifecycle",
                ok,
                _ms(t),
                f"total={data.get('total')}, found_qa={found}",
            )
        except Exception as e:
            _check(
                result,
                6,
                "List agents (find QA agent)",
                "Authentication & Agent Lifecycle",
                False,
                _ms(t),
                "Failed to list agents",
                str(e),
            )

        # ── 7. Get agent by ID ──────────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.get(f"{api_url}/api/v1/agents/{agent_id}", headers=headers)
            data = r.json()
            ok = r.status_code == 200 and data.get("name") == qa_name
            _check(
                result,
                7,
                "Get agent by ID",
                "Authentication & Agent Lifecycle",
                ok,
                _ms(t),
                f"name={data.get('name')}, status={data.get('status')}",
            )
        except Exception as e:
            _check(
                result,
                7,
                "Get agent by ID",
                "Authentication & Agent Lifecycle",
                False,
                _ms(t),
                "Failed to get agent",
                str(e),
            )

        # ── 8. Gateway deny without policy ──────────────────────────
        t = time.perf_counter()
        try:
            r = await client.post(
                f"{gateway_url}/gateway/enforce",
                params={"agent_id": agent_id, "endpoint": "/v1/chat/completions", "method": "POST"},
            )
            data = r.json()
            ok = data.get("decision") == "deny" and data.get("deny_reason") == "no_active_policy"
            _check(
                result,
                8,
                "Gateway deny (no policy)",
                "Gateway Policy Enforcement",
                ok,
                _ms(t),
                f"decision={data.get('decision')}, reason={data.get('deny_reason')}",
            )
        except Exception as e:
            _check(
                result,
                8,
                "Gateway deny (no policy)",
                "Gateway Policy Enforcement",
                False,
                _ms(t),
                "Gateway enforce failed",
                str(e),
            )

        # ── 9. Create policy ────────────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.post(
                f"{api_url}/api/v1/agents/{agent_id}/policies",
                headers=headers,
                json={
                    "rules": {
                        "allowed_endpoints": ["/v1/chat/*", "/v1/embeddings"],
                        "allowed_methods": ["POST", "GET"],
                    }
                },
            )
            data = r.json()
            ok = r.status_code == 201 and data.get("is_active") is True
            _check(
                result,
                9,
                "Create policy",
                "Gateway Policy Enforcement",
                ok,
                _ms(t),
                f"version={data.get('version')}, active={data.get('is_active')}",
            )
        except Exception as e:
            _check(
                result,
                9,
                "Create policy",
                "Gateway Policy Enforcement",
                False,
                _ms(t),
                "Failed to create policy",
                str(e),
            )

        # ── 10. Gateway allow ───────────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.post(
                f"{gateway_url}/gateway/enforce",
                params={"agent_id": agent_id, "endpoint": "/v1/chat/completions", "method": "POST"},
            )
            data = r.json()
            ok = data.get("decision") == "allow"
            _check(
                result,
                10,
                "Gateway allow (matching policy)",
                "Gateway Policy Enforcement",
                ok,
                _ms(t),
                f"decision={data.get('decision')}",
            )
        except Exception as e:
            _check(
                result,
                10,
                "Gateway allow (matching policy)",
                "Gateway Policy Enforcement",
                False,
                _ms(t),
                "Gateway enforce failed",
                str(e),
            )

        # ── 11. Gateway deny non-matching ───────────────────────────
        t = time.perf_counter()
        try:
            r = await client.post(
                f"{gateway_url}/gateway/enforce",
                params={"agent_id": agent_id, "endpoint": "/v1/admin/secrets", "method": "DELETE"},
            )
            data = r.json()
            ok = data.get("decision") == "deny" and data.get("deny_reason") == "policy_denied"
            _check(
                result,
                11,
                "Gateway deny (non-matching)",
                "Gateway Policy Enforcement",
                ok,
                _ms(t),
                f"decision={data.get('decision')}, reason={data.get('deny_reason')}",
            )
        except Exception as e:
            _check(
                result,
                11,
                "Gateway deny (non-matching)",
                "Gateway Policy Enforcement",
                False,
                _ms(t),
                "Gateway enforce failed",
                str(e),
            )

        # ── 12. Audit log ───────────────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.get(
                f"{api_url}/api/v1/audit",
                headers=headers,
                params={"agent_id": agent_id, "limit": 10},
            )
            data = r.json()
            entries = data.get("items", [])
            has_allow = any(e.get("decision") == "allow" for e in entries)
            has_deny = any(e.get("decision") == "deny" for e in entries)
            has_hashes = all(e.get("entry_hash") for e in entries) if entries else False
            ok = r.status_code == 200 and has_allow and has_deny and has_hashes
            _check(
                result,
                12,
                "Audit log records decisions",
                "Audit & Compliance",
                ok,
                _ms(t),
                f"entries={len(entries)}, has_allow={has_allow}, has_deny={has_deny}, has_hashes={has_hashes}",
            )
        except Exception as e:
            _check(
                result,
                12,
                "Audit log records decisions",
                "Audit & Compliance",
                False,
                _ms(t),
                "Audit query failed",
                str(e),
            )

        # ── 13. Audit chain verify ──────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.get(f"{api_url}/api/v1/audit/verify", headers=headers)
            data = r.json()
            ok = r.status_code == 200 and data.get("valid") is True
            _check(
                result,
                13,
                "Audit chain integrity",
                "Audit & Compliance",
                ok,
                _ms(t),
                f"valid={data.get('valid')}, verified={data.get('entries_verified')}",
            )
        except Exception as e:
            _check(
                result,
                13,
                "Audit chain integrity",
                "Audit & Compliance",
                False,
                _ms(t),
                "Audit verify failed",
                str(e),
            )

        # ── 14. Key rotation ───────────────────────────────────────
        t = time.perf_counter()
        try:
            r = await client.post(
                f"{api_url}/api/v1/agents/{agent_id}/keys/rotate",
                headers=headers,
            )
            data = r.json()
            ok = (
                r.status_code == 201
                and data.get("new_key", {}).get("status") == "active"
                and data.get("rotated_key", {}).get("status") == "rotated"
            )
            _check(
                result,
                14,
                "Key rotation",
                "Key Management & Cleanup",
                ok,
                _ms(t),
                f"new_key={data.get('new_key', {}).get('status')}, rotated={data.get('rotated_key', {}).get('status')}",
            )
        except Exception as e:
            _check(
                result,
                14,
                "Key rotation",
                "Key Management & Cleanup",
                False,
                _ms(t),
                "Key rotation failed",
                str(e),
            )

        # ── 15. Revoke agent + verify gateway denies ────────────────
        t = time.perf_counter()
        try:
            r = await client.delete(f"{api_url}/api/v1/agents/{agent_id}", headers=headers)
            revoke_ok = r.status_code == 200

            # Verify gateway denies revoked agent
            r2 = await client.post(
                f"{gateway_url}/gateway/enforce",
                params={"agent_id": agent_id, "endpoint": "/v1/chat/completions", "method": "POST"},
            )
            data2 = r2.json()
            gateway_denies = data2.get("decision") in ("deny", "error")
            ok = revoke_ok and gateway_denies
            _check(
                result,
                15,
                "Revoke agent + gateway denies",
                "Key Management & Cleanup",
                ok,
                _ms(t),
                f"revoked={revoke_ok}, gateway_denies={gateway_denies}, reason={data2.get('deny_reason')}",
            )
        except Exception as e:
            _check(
                result,
                15,
                "Revoke agent + gateway denies",
                "Key Management & Cleanup",
                False,
                _ms(t),
                "Revoke/verify failed",
                str(e),
            )
            # Best-effort cleanup
            with contextlib.suppress(Exception):
                await client.delete(f"{api_url}/api/v1/agents/{agent_id}", headers=headers)

    result.duration_ms = _ms(run_start)
    return result


def _ms(start: float) -> int:
    """Milliseconds since start."""
    return round((time.perf_counter() - start) * 1000)
