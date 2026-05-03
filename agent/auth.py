"""Ada server auth — verify-key middleware against AI Identity.

Used by `serve.py`. When `ADA_REQUIRE_AUTH=1`, every protected request must
carry an `X-Agent-Key` header that AI Identity's `/api/v1/keys/verify`
recognizes as a valid runtime key. Without that flag, the middleware logs a
warning at startup and lets requests through — preserving the local
double-click-launcher experience while making production deploys (#322) able
to flip a single env var to enable auth.

Mirrors the dashboard's `app/ai_identity.py` verify client. Plaintext keys
are never logged.

Surfaced by Insight #74 (Ada production-readiness audit). Pairs with the
secret-file denylist from Sprint 12 #325 — together they unblock running
Ada on a non-localhost host.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger(__name__)

AI_IDENTITY_API_URL = os.getenv("AI_IDENTITY_API_URL", "https://api.ai-identity.co").rstrip("/")
ADA_ADMIN_KEY = os.getenv("ADA_ADMIN_KEY") or os.getenv("AI_IDENTITY_ADMIN_KEY", "")
VERIFY_TIMEOUT_S = float(os.getenv("AI_IDENTITY_VERIFY_TIMEOUT_S", "3.0"))

# Paths that NEVER require auth (UI shell, health, version, OpenAPI docs).
# Everything else is protected when auth is enabled.
PUBLIC_PATHS = frozenset(
    {
        "/",
        "/version",
        "/health",  # ADK ships this; launcher polls it on startup
        "/healthz",
        "/readyz",
        "/openapi.json",
        "/docs",
        "/redoc",
    }
)
PUBLIC_PREFIXES: tuple[str, ...] = ("/ui/", "/docs/", "/redoc/")


@dataclass(frozen=True)
class VerifiedAgent:
    """Result of a successful verify-key call."""

    agent_id: str
    agent_name: str
    role: str
    metadata: dict


def verify_agent_key(plaintext_key: str) -> VerifiedAgent | None:
    """Call AI Identity's verify-key endpoint. Return VerifiedAgent on success, None otherwise.

    The plaintext key is sent in the request body and never logged. The admin
    key in `X-API-Key` is the dashboard-style admin credential that authorizes
    verify calls; if it's not configured, this function returns None and the
    caller should treat that as auth-not-configured (the middleware logs and
    refuses requests rather than failing open).
    """
    if not ADA_ADMIN_KEY:
        return None
    if not plaintext_key:
        return None

    url = f"{AI_IDENTITY_API_URL}/api/v1/keys/verify"
    try:
        resp = httpx.post(
            url,
            json={"key": plaintext_key},
            headers={"X-API-Key": ADA_ADMIN_KEY},
            timeout=VERIFY_TIMEOUT_S,
        )
    except httpx.RequestError as exc:
        logger.warning("verify_agent_key network error: %s", type(exc).__name__)
        return None

    if resp.status_code != 200:
        logger.warning("verify_agent_key non-200: %s", resp.status_code)
        return None

    body = resp.json()
    if not body.get("valid"):
        return None

    metadata = body.get("metadata") or {}
    return VerifiedAgent(
        agent_id=body["agent_id"],
        agent_name=body.get("agent_name", ""),
        role=metadata.get("role", ""),
        metadata=metadata,
    )


def needs_auth(path: str) -> bool:
    """Return True if `path` requires a valid X-Agent-Key when auth is enabled.

    Default-deny: anything not in the explicit public allowlist is protected.
    A new endpoint is auth-required by default unless added to PUBLIC_PATHS or
    PUBLIC_PREFIXES — safer than maintaining a protected-routes list.
    """
    if path in PUBLIC_PATHS:
        return False
    return not any(path.startswith(p) for p in PUBLIC_PREFIXES)


def auth_required() -> bool:
    """Whether to enforce X-Agent-Key on protected routes.

    Read at request time (not import time) so tests can monkeypatch the env
    var without re-importing the module.
    """
    return os.getenv("ADA_REQUIRE_AUTH", "0").lower() in ("1", "true", "yes")


async def auth_middleware(request: Request, call_next):
    """ASGI middleware: enforce X-Agent-Key on protected paths when enabled.

    OPTIONS preflight is always passed through to the CORS middleware below;
    GET/POST/etc. on protected paths return 401 without a verifiable key.
    """
    if request.method == "OPTIONS":
        return await call_next(request)

    if not auth_required():
        return await call_next(request)

    if not needs_auth(request.url.path):
        return await call_next(request)

    if not ADA_ADMIN_KEY:
        # Auth required but admin key not configured — refuse rather than fail open.
        return JSONResponse(
            status_code=503,
            content={"error": "ada auth required but ADA_ADMIN_KEY/AI_IDENTITY_ADMIN_KEY not set"},
        )

    key = request.headers.get("X-Agent-Key", "")
    if not key:
        return JSONResponse(
            status_code=401,
            content={"error": "missing X-Agent-Key header"},
        )

    verified = verify_agent_key(key)
    if verified is None:
        return JSONResponse(
            status_code=401,
            content={"error": "invalid X-Agent-Key"},
        )

    request.state.agent = verified
    return await call_next(request)


def allowed_origins() -> list[str]:
    """Comma-separated origins from `ADA_ALLOWED_ORIGINS`, default localhost-only.

    Read at startup (build_app) — changing the env var requires a restart.
    Use a wildcard `*` only if explicitly set; never the default.
    """
    raw = os.getenv(
        "ADA_ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
