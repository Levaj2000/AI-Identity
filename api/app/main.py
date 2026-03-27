"""AI Identity — API Server.

Identity service and admin API for managing AI agents,
API keys, capabilities, and policies.

Run locally:  uvicorn api.app.main:app --reload --port 8001
Run on Render: uvicorn api.app.main:app --host 0.0.0.0 --port $PORT
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from common.auth.sanitizer import sanitize
from common.config.logging import setup_logging
from common.config.settings import settings

# ── Sentry ───────────────────────────────────────────────────────────────

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=f"ai-identity-api@{settings.app_version}",
        traces_sample_rate=0.2 if settings.environment == "production" else 1.0,
        profiles_sample_rate=0.1 if settings.environment == "production" else 1.0,
        send_default_pii=False,
        enable_tracing=True,
    )

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
        "name": "admin",
        "description": "Admin-only endpoints — platform stats, user management, "
        "tier overrides, and system health. Requires role=admin.",
    },
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
        "name": "compliance",
        "description": "Compliance assessment engine — run checks against NIST AI RMF, "
        "EU AI Act, SOC 2, and internal best practices. Automated evaluation "
        "of agent policies, key hygiene, audit integrity, and credential security.",
    },
    {
        "name": "usage",
        "description": "Account usage and quota management — check resource utilization "
        "against your tier limits and view available plans.",
    },
    {
        "name": "billing",
        "description": "Stripe billing integration — create checkout sessions, "
        "manage subscriptions via customer portal, and handle webhook events "
        "for automatic tier synchronization.",
    },
    {
        "name": "qa",
        "description": "Automated QA checklist — run 15-step E2E production validation, "
        "track results, and collect customer + staff sign-offs for onboarding.",
    },
    {
        "name": "organizations",
        "description": "Create and manage organizations — invite team members, "
        "assign roles, and share agents across your team.",
    },
    {
        "name": "agent-assignments",
        "description": "Assign users to specific agents with roles — "
        "owner, operator, or viewer for fine-grained access control.",
    },
    {
        "name": "health",
        "description": "Service health and status endpoints.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — replaces deprecated on_event."""
    logger.info(
        "AI Identity API starting — env=%s, version=%s",
        settings.environment,
        settings.app_version,
    )

    # Auto-create tables and ensure schema is up to date
    try:
        from sqlalchemy import inspect, text

        from common.models.base import Base, engine
        from common.models.compliance import ComplianceFramework  # noqa: F811

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured (including compliance)")

        # Defensive column migration — add columns that create_all misses
        # on existing tables. This handles the qa_runs.mode column addition.
        inspector = inspect(engine)
        if "qa_runs" in inspector.get_table_names():
            existing_cols = {c["name"] for c in inspector.get_columns("qa_runs")}
            if "mode" not in existing_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text("ALTER TABLE qa_runs ADD COLUMN mode VARCHAR(20) DEFAULT 'admin'")
                    )
                    conn.execute(text("UPDATE qa_runs SET mode = 'admin' WHERE mode IS NULL"))
                logger.info("Added 'mode' column to qa_runs table")

            if "user_id" not in existing_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text("ALTER TABLE qa_runs ADD COLUMN user_id UUID REFERENCES users(id)")
                    )
                    conn.execute(text("CREATE INDEX ix_qa_runs_user_id ON qa_runs (user_id)"))
                logger.info("Added 'user_id' column to qa_runs table")

        # Defensive migration: email tracking columns on users table
        if "users" in inspector.get_table_names():
            user_cols = {c["name"] for c in inspector.get_columns("users")}
            for col_name in ("welcome_email_sent_at", "followup_email_sent_at"):
                if col_name not in user_cols:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} TIMESTAMPTZ"))
                    logger.info("Added '%s' column to users table", col_name)

        # Seed compliance frameworks if empty
        from common.models.base import SessionLocal

        db = SessionLocal()
        try:
            count = db.query(ComplianceFramework).count()
            if count == 0:
                logger.info("Seeding compliance frameworks...")
                from scripts.seed_compliance import seed

                seed()
            else:
                logger.info("Compliance frameworks already seeded (%d found)", count)
        finally:
            db.close()
    except Exception as e:
        logger.warning("Compliance auto-seed skipped: %s", e)

    yield


app = FastAPI(
    title="AI Identity API",
    summary="Identity and key management for AI agents",
    description=API_DESCRIPTION,
    version=settings.app_version,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
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

# ── Security Headers Middleware ─────────────────────────────────────────


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add standard security headers to every response."""
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    return response


# ── Request Logging Middleware ───────────────────────────────────────────


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with timing and a unique request ID."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    log_extra = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }

    # Flag slow requests (P95 alert threshold: 500ms)
    if duration_ms > 500 and request.url.path != "/health":
        logger.warning(
            "SLOW REQUEST: %s %s → %s (%sms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra=log_extra,
        )
        if settings.sentry_dsn:
            sentry_sdk.set_tag("slow_request", True)
            sentry_sdk.set_context(
                "performance",
                {
                    "duration_ms": duration_ms,
                    "endpoint": request.url.path,
                    "method": request.method,
                },
            )
    else:
        logger.info(
            "%s %s → %s (%sms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra=log_extra,
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

    # Attach request context to Sentry event
    if settings.sentry_dsn:
        sentry_sdk.set_context(
            "request_info",
            {
                "method": request.method,
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", None),
            },
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

from api.app.routers.admin import router as admin_router  # noqa: E402
from api.app.routers.agent_assignments import router as agent_assignments_router  # noqa: E402
from api.app.routers.agents import router as agents_router  # noqa: E402
from api.app.routers.audit import router as audit_router  # noqa: E402
from api.app.routers.auth import router as auth_router  # noqa: E402
from api.app.routers.billing import router as billing_router  # noqa: E402
from api.app.routers.capabilities import router as capabilities_router  # noqa: E402
from api.app.routers.compliance import router as compliance_router  # noqa: E402
from api.app.routers.credentials import router as credentials_router  # noqa: E402
from api.app.routers.email_cron import router as email_cron_router  # noqa: E402
from api.app.routers.keys import router as keys_router  # noqa: E402
from api.app.routers.organizations import router as organizations_router  # noqa: E402
from api.app.routers.policies import router as policies_router  # noqa: E402
from api.app.routers.qa import router as qa_router  # noqa: E402
from api.app.routers.usage import router as usage_router  # noqa: E402

app.include_router(admin_router)
app.include_router(agents_router)
app.include_router(capabilities_router)
app.include_router(audit_router)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(compliance_router)
app.include_router(credentials_router)
app.include_router(email_cron_router)
app.include_router(keys_router)
app.include_router(policies_router)
app.include_router(qa_router)
app.include_router(usage_router)
app.include_router(organizations_router)
app.include_router(agent_assignments_router)

# ── Routes ───────────────────────────────────────────────────────────────


@app.api_route("/health", methods=["GET", "HEAD"], tags=["health"], summary="Health check")
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
