"""AI Identity — Proxy Gateway.

Runtime gateway that authenticates agent API keys,
evaluates policies, and forwards or blocks requests.

SECURITY: This gateway implements FAIL-CLOSED enforcement.
When the policy engine is down, times out, or errors, requests are DENIED.
A circuit breaker trips after repeated failures to prevent cascading damage.

Run: uvicorn gateway.app.main:app --reload --port 8002
"""

import logging
import math
import time
import uuid
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from common.auth.sanitizer import sanitize
from common.config.logging import setup_logging
from common.config.settings import settings
from common.models import get_db
from common.models.base import SessionLocal
from gateway.app.circuit_breaker import CircuitState
from gateway.app.db import get_gateway_db
from gateway.app.enforce import enforce, policy_circuit_breaker
from gateway.app.rate_limiter import RateLimitResult, rate_limiter

# ── Sentry ───────────────────────────────────────────────────────────────

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=f"ai-identity-gateway@{settings.app_version}",
        traces_sample_rate=0.2 if settings.environment == "production" else 1.0,
        send_default_pii=False,
    )

# ── Logging ──────────────────────────────────────────────────────────────

setup_logging(service_name="ai-identity-gateway")
logger = logging.getLogger("ai_identity.gateway")

# ── App ──────────────────────────────────────────────────────────────────

OPENAPI_TAGS = [
    {
        "name": "enforcement",
        "description": "Policy enforcement endpoints — fail-closed gateway with circuit breaker.",
    },
    {
        "name": "health",
        "description": "Service health and circuit breaker status.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — replaces deprecated on_event."""
    logger.info(
        "AI Identity Gateway starting — env=%s, version=%s, "
        "policy_timeout=%dms, circuit_breaker=%d failures/%ds window, "
        "rate_limit=%s (ip=%d/s, key=%d/s)",
        settings.environment,
        settings.app_version,
        settings.policy_eval_timeout_ms,
        settings.circuit_breaker_failure_threshold,
        settings.circuit_breaker_window_seconds,
        "enabled" if settings.rate_limit_enabled else "DISABLED",
        settings.rate_limit_per_ip,
        settings.rate_limit_per_key,
    )
    yield


app = FastAPI(
    title="AI Identity — Gateway",
    description=(
        "Proxy gateway for AI agent request routing and policy enforcement. "
        "Implements fail-closed enforcement: requests are denied when the policy "
        "engine is unreachable, times out, or errors."
    ),
    version=settings.app_version,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

# ── RLS Service Bypass ───────────────────────────────────────────────────
# Override the shared get_db so the gateway sets app.is_service = 'true'
# on every DB session, activating the service_bypass RLS policy.
app.dependency_overrides[get_db] = get_gateway_db

# ── Internal Service Auth ────────────────────────────────────────────────
# When adding gateway endpoints that should only be called by the API:
#
#   from fastapi import Depends
#   from common.auth.internal import require_internal_auth
#
#   @router.post("/internal/gateway/invalidate-cache",
#                dependencies=[Depends(require_internal_auth)])
#   async def invalidate_cache(...): ...
#
# The API signs outbound requests with:
#   from common.auth.internal import sign_request
#   headers = sign_request("POST", "/internal/gateway/invalidate-cache", body)
#   response = httpx.post(gateway_url + "/...", content=body, headers=headers)
#
# Both services must share the same INTERNAL_SERVICE_KEY env var.

# ── CORS ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
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


# ── Rate Limiting Middleware ────────────────────────────────────────────

# Health/info/monitoring endpoints exempt from rate limiting
_RATE_LIMIT_EXEMPT_PATHS = frozenset({"/health", "/", "/gateway/circuit-breaker"})


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Pre-policy rate limiter — runs before any route handler or DB access.

    Enforces per-IP and per-agent_id sliding window limits.
    Returns 429 with Retry-After header on breach.
    Adds X-RateLimit-* headers to ALL responses.
    """
    # Skip if rate limiting is disabled
    if not settings.rate_limit_enabled:
        return await call_next(request)

    # Exempt health/info/monitoring endpoints
    if request.url.path in _RATE_LIMIT_EXEMPT_PATHS:
        return await call_next(request)

    # Extract client IP (handle reverse proxy)
    client_ip = _get_client_ip(request)

    # Per-IP check (always runs)
    ip_result = rate_limiter.check_ip(client_ip)

    if not ip_result.allowed:
        logger.warning(
            "Rate limit exceeded (per-IP) for %s on %s %s",
            client_ip,
            request.method,
            request.url.path,
        )
        return _rate_limit_response(ip_result)

    # Per-key check (only when agent_id is present)
    agent_id = request.query_params.get("agent_id")
    key_result: RateLimitResult | None = None

    if agent_id:
        key_result = rate_limiter.check_key(agent_id)

        if not key_result.allowed:
            logger.warning(
                "Rate limit exceeded (per-key) for agent_id=%s from %s",
                agent_id,
                client_ip,
            )
            return _rate_limit_response(key_result)

    # Both checks passed — forward to route handler
    response = await call_next(request)

    # Add rate limit headers to ALL responses (use the more restrictive result)
    _add_rate_limit_headers(response, ip_result, key_result)

    return response


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For for reverse proxies.

    Takes the FIRST IP in X-Forwarded-For (the original client) if present.
    Falls back to request.client.host for direct connections.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit_response(result: RateLimitResult) -> JSONResponse:
    """Build a 429 response with rate limit headers and Retry-After."""
    retry_after = math.ceil(result.retry_after) if result.retry_after else 1

    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "rate_limit_exceeded",
                "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
            }
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(math.ceil(result.reset_after)),
        },
    )


def _add_rate_limit_headers(
    response,
    ip_result: RateLimitResult,
    key_result: RateLimitResult | None,
) -> None:
    """Add X-RateLimit-* headers reflecting the most restrictive limit.

    When both IP and key limits apply, report the one with fewer remaining.
    This gives the caller the most useful information about their closest limit.
    """
    if key_result is not None and key_result.remaining < ip_result.remaining:
        effective = key_result
    else:
        effective = ip_result

    response.headers["X-RateLimit-Limit"] = str(effective.limit)
    response.headers["X-RateLimit-Remaining"] = str(effective.remaining)
    response.headers["X-RateLimit-Reset"] = str(math.ceil(effective.reset_after))


# ── Error Handling ───────────────────────────────────────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPExceptions — sanitize detail to prevent key leakage."""
    safe_detail = sanitize(str(exc.detail)) if exc.detail else "An error occurred"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "gateway_error",
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

    if settings.sentry_dsn:
        sentry_sdk.set_context(
            "request_info",
            {
                "method": request.method,
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", None),
                "agent_id": request.query_params.get("agent_id"),
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "gateway_error",
                "message": "An unexpected error occurred",
            }
        },
    )


# ── Enforcement Endpoint ────────────────────────────────────────────────


@app.post(
    "/gateway/enforce",
    tags=["enforcement"],
    summary="Evaluate policy for an agent request (fail-closed)",
    response_description="Enforcement decision: allow, deny, or error",
)
def enforce_request(
    agent_id: uuid.UUID = Query(..., description="UUID of the requesting agent"),
    endpoint: str = Query(..., description="Target API endpoint (e.g., /v1/chat)"),
    method: str = Query("POST", description="HTTP method"),
    key_type: str | None = Query(
        None,
        pattern="^(runtime|admin)$",
        description="Key type: runtime (aid_sk_) or admin (aid_admin_). "
        "Runtime keys are rejected on management endpoints; admin keys on proxy endpoints.",
    ),
    db: Session = Depends(get_db),
):
    """Evaluate whether an agent's request should be allowed or denied.

    This is the fail-closed gateway core. Every request MUST pass through
    this endpoint before being forwarded to the upstream API.

    **Fail-closed guarantees:**
    - Runtime key on management endpoint → 403 (denied)
    - Admin key on proxy endpoint → 403 (denied)
    - Policy engine error → 503 (denied)
    - Policy evaluation timeout (>500ms) → 503 (denied)
    - No active policy → 403 (denied)
    - Circuit breaker open → 503 (all requests denied)
    - Agent revoked/suspended → 403 (denied)

    Only an explicit ALLOW from a successful policy evaluation permits forwarding.
    """
    result = enforce(
        db,
        agent_id=agent_id,
        endpoint=endpoint,
        method=method,
        key_type=key_type,
    )

    response = {
        "decision": result.decision.value,
        "status_code": result.status_code,
        "message": result.message,
    }

    if result.deny_reason:
        response["deny_reason"] = result.deny_reason.value

    if not result.allowed:
        return JSONResponse(
            status_code=result.status_code,
            content=response,
        )

    # ── Post-policy quota check ──────────────────────────────────────
    # Only count requests that pass policy enforcement.
    try:
        from common.models import Agent, User
        from common.models.user import TIER_QUOTAS

        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if agent:
            user = db.query(User).filter(User.id == agent.user_id).first()
            if user:
                quotas = TIER_QUOTAS.get(user.tier, TIER_QUOTAS["free"])
                max_req = quotas["max_requests_per_month"]

                if max_req != -1 and (user.requests_this_month or 0) >= max_req:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "decision": "deny",
                            "status_code": 429,
                            "message": (
                                f"Monthly request quota exceeded ({max_req} requests). "
                                f"Upgrade at https://ai-identity.co/#pricing"
                            ),
                            "deny_reason": "quota_exceeded",
                        },
                    )

                # Increment counter
                user.requests_this_month = (user.requests_this_month or 0) + 1
                db.commit()

                # Add quota headers to response
                response["quota"] = {
                    "tier": user.tier,
                    "requests_used": user.requests_this_month,
                    "requests_limit": max_req if max_req != -1 else None,
                }
    except Exception as e:
        # Quota check is non-blocking — log and allow
        logger.warning("Quota check failed (allowing request): %s", e)

    return response


# ── Circuit Breaker Status ──────────────────────────────────────────────


@app.get(
    "/gateway/circuit-breaker",
    tags=["health"],
    summary="Circuit breaker status",
    response_description="Current circuit breaker state and metrics",
)
def circuit_breaker_status():
    """Return the current state of the policy engine circuit breaker.

    Use this for monitoring and alerting. When the state is OPEN,
    all agent requests are being denied (503).
    """
    status = policy_circuit_breaker.status
    return {
        "state": status.state.value,
        "failure_count": status.failure_count,
        "is_accepting_requests": status.state != CircuitState.OPEN,
        "config": {
            "failure_threshold": settings.circuit_breaker_failure_threshold,
            "window_seconds": settings.circuit_breaker_window_seconds,
            "recovery_seconds": settings.circuit_breaker_recovery_seconds,
            "policy_timeout_ms": settings.policy_eval_timeout_ms,
        },
    }


# ── Health ───────────────────────────────────────────────────────────────


@app.api_route("/health", methods=["GET", "HEAD"], tags=["health"], summary="Health check")
async def health():
    """Returns service status, version, and circuit breaker state.

    Includes a lightweight DB connectivity check: executes SELECT 1
    to verify the database is reachable. Reports 'degraded' if the
    circuit breaker is open OR the database is unreachable.
    """
    breaker_state = policy_circuit_breaker.state
    db_ok = False
    db_error = None

    try:
        db: Session = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_ok = True
        finally:
            db.close()
    except Exception as exc:
        db_error = type(exc).__name__
        logger.warning("Health check DB probe failed: %s", exc)

    is_healthy = db_ok and breaker_state != CircuitState.OPEN
    result = {
        "status": "ok" if is_healthy else "degraded",
        "version": settings.app_version,
        "service": "ai-identity-gateway",
        "circuit_breaker": breaker_state.value,
        "database": "connected" if db_ok else "unreachable",
    }
    if db_error:
        result["db_error"] = db_error
    return result


@app.get("/", tags=["health"], summary="Service info")
async def root():
    """Returns basic service information and a link to the API docs."""
    return {
        "service": "ai-identity-gateway",
        "version": settings.app_version,
        "docs": "/docs",
    }
