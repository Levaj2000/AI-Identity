"""AI Identity — API Server.

Identity service and admin API for managing AI agents,
API keys, capabilities, and policies.

Run locally:  uvicorn api.app.main:app --reload --port 8001
Run on Render: uvicorn api.app.main:app --host 0.0.0.0 --port $PORT
"""

import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from common.auth.sanitizer import sanitize
from common.config.logging import setup_logging
from common.config.settings import settings

# ── Logging ──────────────────────────────────────────────────────────────

setup_logging()
logger = logging.getLogger("ai_identity.api")

# ── App ──────────────────────────────────────────────────────────────────

API_DESCRIPTION = """\
**AI Identity** is the identity layer for AI agents. It gives every agent a
verifiable identity, cryptographic API keys, and (soon) policy-based guardrails.

## Getting Started

1. **Create an agent** — `POST /api/v1/agents` with a name and capabilities
2. **Use the API key** — the response includes a show-once `api_key` (`aid_sk_…`)
3. **Manage keys** — rotate, revoke, or issue additional keys without downtime

## Authentication

All endpoints require an `X-API-Key` header with a valid developer API key.
Agent-scoped keys (`aid_sk_…`) are used by agents themselves; developer keys
are used to manage agents via this admin API.
"""

OPENAPI_TAGS = [
    {
        "name": "agents",
        "description": "Create, list, update, and delete AI agents. "
        "Each agent gets a UUID identity and cryptographic API key at creation.",
    },
    {
        "name": "keys",
        "description": "Manage API keys for agents — create, list, revoke, and rotate. "
        "Keys use SHA-256 hashing and are shown only once at creation time.",
    },
    {
        "name": "policies",
        "description": "Create and manage policies that control what endpoints "
        "an agent can access through the gateway.",
    },
    {
        "name": "audit",
        "description": "Append-only audit log with HMAC integrity chain. "
        "Read-only access and chain verification for SOC 2 compliance.",
    },
    {
        "name": "credentials",
        "description": "Manage encrypted upstream API credentials for agents. "
        "Credentials are Fernet-encrypted at rest — plaintext keys never touch disk.",
    },
    {
        "name": "health",
        "description": "Service health and status endpoints.",
    },
]

app = FastAPI(
    title="AI Identity API",
    summary="Identity and key management for AI agents",
    description=API_DESCRIPTION,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=OPENAPI_TAGS,
    contact={
        "name": "AI Identity Team",
        "url": "https://github.com/Levaj2000/AI-Identity",
    },
    license_info={
        "name": "MIT",
    },
)

# ── CORS ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Logging Middleware ───────────────────────────────────────────


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with timing and a unique request ID."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "%s %s → %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    response.headers["X-Request-ID"] = request_id
    return response


# ── Error Handling ───────────────────────────────────────────────────────


class APIError(Exception):
    """Structured API error with code and status."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Return structured JSON for known API errors — sanitize messages."""
    safe_message = sanitize(exc.message)
    logger.warning(
        "API error: %s — %s",
        exc.code,
        safe_message,
        extra={"method": request.method, "path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": safe_message,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPExceptions — sanitize detail to prevent key leakage."""
    safe_detail = sanitize(str(exc.detail)) if exc.detail else "An error occurred"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "http_error",
                "message": safe_detail,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — return safe 500, never leak internals."""
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
    # SECURITY: Never return exception details to the client.
    # The logger.exception above logs the full sanitized traceback for debugging.
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
            }
        },
    )


# ── Startup / Shutdown ───────────────────────────────────────────────────


@app.on_event("startup")
async def startup():
    """Log service start with environment info."""
    logger.info(
        "AI Identity API starting — env=%s, version=%s",
        settings.environment,
        settings.app_version,
    )


# ── Internal Service Auth ────────────────────────────────────────────────
# When adding endpoints that should only be called by the Gateway:
#
#   from fastapi import Depends
#   from common.auth.internal import require_internal_auth
#
#   @router.get("/internal/agents/lookup",
#               dependencies=[Depends(require_internal_auth)])
#   async def lookup_agent_for_gateway(...): ...
#
# The Gateway signs outbound requests with:
#   from common.auth.internal import sign_request
#   headers = sign_request("GET", "/internal/agents/lookup")
#   response = httpx.get(api_url + "/internal/agents/lookup", headers=headers)
#
# Both services must share the same INTERNAL_SERVICE_KEY env var.

# ── Routers ──────────────────────────────────────────────────────────────

from api.app.routers.agents import router as agents_router  # noqa: E402
from api.app.routers.audit import router as audit_router  # noqa: E402
from api.app.routers.credentials import router as credentials_router  # noqa: E402
from api.app.routers.keys import router as keys_router  # noqa: E402
from api.app.routers.policies import router as policies_router  # noqa: E402

app.include_router(agents_router)
app.include_router(audit_router)
app.include_router(credentials_router)
app.include_router(keys_router)
app.include_router(policies_router)

# ── Routes ───────────────────────────────────────────────────────────────


@app.get("/health", tags=["health"], summary="Health check")
async def health():
    """Returns service status, version, and name. Used by Render and uptime monitors."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "service": "ai-identity-api",
    }


@app.get("/", tags=["health"], summary="Service info")
async def root():
    """Returns basic service information and a link to the API docs."""
    return {
        "service": "ai-identity-api",
        "version": settings.app_version,
        "docs": "/docs",
    }
