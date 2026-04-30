"""AI Identity — API Server.

Identity service and admin API for managing AI agents,
API keys, capabilities, and policies.

Run locally: uvicorn api.app.main:app --reload --port 8001
Run on GKE:  uvicorn api.app.main:app --host 0.0.0.0 --port $PORT
"""

import logging
import time
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from common.auth.sanitizer import sanitize
from common.config.logging import setup_logging
from common.config.settings import settings

# ── Sentry ───────────────────────────────────────────────────────────────


def _filter_transactions(event, hint):
    """Drop health/root transactions — monitoring noise, not actionable."""
    url = event.get("request", {}).get("url", "")
    if url.endswith(("/health", "/")):
        return None
    return event


if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=f"ai-identity-api@{settings.app_version}",
        traces_sample_rate=0.2 if settings.environment == "production" else 1.0,
        profiles_sample_rate=0.1 if settings.environment == "production" else 1.0,
        send_default_pii=False,
        enable_tracing=True,
        before_send_transaction=_filter_transactions,
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
        "name": "capabilities",
        "description": "Named permissions that can be bound to agents via policies — "
        "the vocabulary your policy engine uses to decide what an agent can do.",
    },
    {
        "name": "auth",
        "description": "User authentication — signup, login, JWT issuance, and "
        "session management for the dashboard and CLI.",
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
        "name": "audit.forensics",
        "description": "Incident reconstruction — deep-dive forensic queries over "
        "the audit log for compliance investigations and post-incident review.",
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
        "name": "compliance.exports",
        "description": "Compliance evidence exports — request a signed ZIP bundle "
        "covering an audit period for SOC 2, EU AI Act, or NIST AI RMF. "
        "Endpoints are wired with the real contract; the build pipeline is a stub "
        "(501 Not Implemented) pending the Milestone #34 follow-on sprint. "
        "See docs/ADR-002-compliance-exports.md.",
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
        "name": "approvals",
        "description": "Human-in-the-loop approval workflows — queue, review, and "
        "authorize sensitive agent actions before they execute.",
    },
    {
        "name": "shadow-agents",
        "description": "Detection of unauthorized agents — flags API activity from "
        "agents operating outside your org's registered identities.",
    },
    {
        "name": "support",
        "description": "Customer support ticket system — create tickets, add comments, "
        "track status, and link to agents/audit logs for context-aware support.",
    },
    {
        "name": "attachments",
        "description": "File attachments for support tickets — upload, download, and manage "
        "files with security validation (virus scanning, EXIF stripping, content type verification).",
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

    # Reap any compliance-export jobs stuck in queued/building from a
    # previous pod that got terminated mid-build. Without this, orphan
    # rows block re-requests with the same scope via the idempotency
    # guard. Runs non-fatally — a DB blip shouldn't stop the API from
    # booting. See common.compliance.orphan_cleanup for the policy.
    try:
        from common.compliance.orphan_cleanup import reap_orphaned_exports
        from common.models.base import SessionLocal

        db = SessionLocal()
        try:
            reaped = reap_orphaned_exports(db)
            if reaped:
                logger.info("Reaped %d orphaned compliance export(s) at startup", reaped)
        finally:
            db.close()
    except Exception as e:
        logger.warning("Orphan export cleanup skipped: %s", e)

    yield


app = FastAPI(
    title="AI Identity API",
    summary="Identity and key management for AI agents",
    description=API_DESCRIPTION,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
    servers=[
        {"url": "https://api.ai-identity.co", "description": "Production"},
    ],
    contact={
        "name": "AI Identity Team",
        "url": "https://ai-identity.co",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
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
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

    # Relaxed CSP for Swagger UI / ReDoc pages (need CDN assets + inline scripts);
    # strict CSP for all other API endpoints.
    if request.url.path in ("/docs", "/redoc", "/openapi.json"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

    return response


# ── Request Logging Middleware ───────────────────────────────────────────


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with timing and an end-to-end correlation ID.

    Two identifiers, derived from one UUID so they always agree:
      * correlation_id — full UUID, travels to audit_log.correlation_id
        and echoes as ``X-Correlation-ID``. Queryable for cross-service
        incident reconstruction.
      * request_id — first 8 hex chars. Log-friendly shorthand, echoed
        as ``X-Request-ID`` for backwards compatibility with clients
        that already use it.

    Incoming headers are honored (``X-Correlation-ID`` wins over
    ``X-Request-ID``) so a single trace survives hops through proxies,
    load balancers, and service mesh.
    """
    from common.audit.correlation import (
        reset_current_correlation_id,
        resolve_correlation_id,
        set_current_correlation_id,
        to_short_id,
    )

    correlation_id = resolve_correlation_id(
        request.headers.get("x-correlation-id"),
        request.headers.get("x-request-id"),
    )
    request_id = to_short_id(correlation_id)
    request.state.correlation_id = correlation_id
    request.state.request_id = request_id  # kept for existing log call-sites
    token = set_current_correlation_id(correlation_id)

    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        reset_current_correlation_id(token)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    log_extra = {
        "request_id": request_id,
        "correlation_id": correlation_id,
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
    response.headers["X-Correlation-ID"] = correlation_id
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
from api.app.routers.approvals import router as approvals_router  # noqa: E402
from api.app.routers.attachment_cleanup_cron import (  # noqa: E402
    router as attachment_cleanup_cron_router,
)
from api.app.routers.attachments import router as attachments_router  # noqa: E402
from api.app.routers.attestations import (  # noqa: E402
    router as attestations_router,
)
from api.app.routers.attestations import (  # noqa: E402
    sessions_router as attestations_sessions_router,
)
from api.app.routers.audit import router as audit_router  # noqa: E402
from api.app.routers.audit_sinks import router as audit_sinks_router  # noqa: E402
from api.app.routers.auth import router as auth_router  # noqa: E402
from api.app.routers.billing import router as billing_router  # noqa: E402
from api.app.routers.canned_responses import router as canned_responses_router  # noqa: E402
from api.app.routers.capabilities import router as capabilities_router  # noqa: E402
from api.app.routers.cleanup_cron import router as cleanup_cron_router  # noqa: E402
from api.app.routers.compliance import router as compliance_router  # noqa: E402
from api.app.routers.compliance_exports import router as compliance_exports_router  # noqa: E402
from api.app.routers.compliance_exports_cron import (  # noqa: E402
    router as compliance_exports_cron_router,
)
from api.app.routers.credentials import router as credentials_router  # noqa: E402
from api.app.routers.email_cron import router as email_cron_router  # noqa: E402
from api.app.routers.forensic_keys import router as forensic_keys_router  # noqa: E402
from api.app.routers.keys import router as keys_router  # noqa: E402
from api.app.routers.organizations import router as organizations_router  # noqa: E402
from api.app.routers.policies import router as policies_router  # noqa: E402
from api.app.routers.policy_evaluate import router as policy_evaluate_router  # noqa: E402
from api.app.routers.qa import router as qa_router  # noqa: E402
from api.app.routers.shadow import router as shadow_router  # noqa: E402
from api.app.routers.sla_escalation_cron import router as sla_escalation_cron_router  # noqa: E402
from api.app.routers.support_metrics import router as support_metrics_router  # noqa: E402
from api.app.routers.support_tickets import router as support_tickets_router  # noqa: E402
from api.app.routers.ticket_templates import router as ticket_templates_router  # noqa: E402
from api.app.routers.usage import router as usage_router  # noqa: E402
from api.app.routers.verify import router as verify_router  # noqa: E402
from common.observability.router import router as metrics_router  # noqa: E402

app.include_router(admin_router)
app.include_router(agents_router)
app.include_router(capabilities_router)
app.include_router(attestations_router)
app.include_router(attestations_sessions_router)
app.include_router(audit_router)
app.include_router(audit_sinks_router)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(canned_responses_router)
app.include_router(compliance_router)
app.include_router(support_metrics_router)
app.include_router(compliance_exports_router)
app.include_router(credentials_router)
app.include_router(cleanup_cron_router)
app.include_router(compliance_exports_cron_router)
app.include_router(email_cron_router)
app.include_router(sla_escalation_cron_router)
app.include_router(attachment_cleanup_cron_router)
app.include_router(attachments_router)
app.include_router(forensic_keys_router)
app.include_router(keys_router)
app.include_router(metrics_router)
app.include_router(policies_router)
app.include_router(policy_evaluate_router)
app.include_router(qa_router)
app.include_router(usage_router)
app.include_router(organizations_router)
app.include_router(agent_assignments_router)
app.include_router(approvals_router)
app.include_router(shadow_router)
app.include_router(support_tickets_router)
app.include_router(ticket_templates_router)
app.include_router(verify_router)

# ── Routes ───────────────────────────────────────────────────────────────


@app.api_route("/health", methods=["GET", "HEAD"], tags=["health"], summary="Health check")
async def health():
    """Returns service status, version, and name. Used by uptime monitors."""
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
