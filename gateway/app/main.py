"""AI Identity — Proxy Gateway.

Runtime gateway that authenticates agent API keys,
evaluates policies, and forwards or blocks requests.

SECURITY: This gateway implements FAIL-CLOSED enforcement.
When the policy engine is down, times out, or errors, requests are DENIED.
A circuit breaker trips after repeated failures to prevent cascading damage.

Run: uvicorn gateway.app.main:app --reload --port 8002
"""

import logging
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from common.auth.sanitizer import sanitize
from common.config.logging import setup_logging
from common.config.settings import settings
from common.models import get_db
from gateway.app.circuit_breaker import CircuitState
from gateway.app.enforce import enforce, policy_circuit_breaker

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

app = FastAPI(
    title="AI Identity — Gateway",
    description=(
        "Proxy gateway for AI agent request routing and policy enforcement. "
        "Implements fail-closed enforcement: requests are denied when the policy "
        "engine is unreachable, times out, or errors."
    ),
    version=settings.app_version,
    openapi_tags=OPENAPI_TAGS,
)

# ── CORS ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
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
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "gateway_error",
                "message": "An unexpected error occurred",
            }
        },
    )


# ── Startup ──────────────────────────────────────────────────────────────


@app.on_event("startup")
async def startup():
    """Log service start with environment info and fail-closed config."""
    logger.info(
        "AI Identity Gateway starting — env=%s, version=%s, "
        "policy_timeout=%dms, circuit_breaker=%d failures/%ds window",
        settings.environment,
        settings.app_version,
        settings.policy_eval_timeout_ms,
        settings.circuit_breaker_failure_threshold,
        settings.circuit_breaker_window_seconds,
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
    db: Session = Depends(get_db),
):
    """Evaluate whether an agent's request should be allowed or denied.

    This is the fail-closed gateway core. Every request MUST pass through
    this endpoint before being forwarded to the upstream API.

    **Fail-closed guarantees:**
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


@app.get("/health", tags=["health"], summary="Health check")
async def health():
    """Returns service status, version, and circuit breaker state."""
    breaker_state = policy_circuit_breaker.state
    return {
        "status": "ok" if breaker_state != CircuitState.OPEN else "degraded",
        "version": settings.app_version,
        "service": "ai-identity-gateway",
        "circuit_breaker": breaker_state.value,
    }


@app.get("/", tags=["health"], summary="Service info")
async def root():
    """Returns basic service information and a link to the API docs."""
    return {
        "service": "ai-identity-gateway",
        "version": settings.app_version,
        "docs": "/docs",
    }
