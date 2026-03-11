"""AI Identity — API Server.

Identity service and admin API for managing AI agents,
API keys, capabilities, and policies.

Run locally:  uvicorn api.app.main:app --reload --port 8001
Run on Render: uvicorn api.app.main:app --host 0.0.0.0 --port $PORT
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from common.config.logging import setup_logging
from common.config.settings import settings

# ── Logging ──────────────────────────────────────────────────────────────

setup_logging()
logger = logging.getLogger("ai_identity.api")

# ── App ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Identity — API",
    description="Identity service and admin API for AI agents",
    version=settings.app_version,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
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


class APIError(Exception):
    """Structured API error with code and status."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Return structured JSON for known API errors."""
    logger.warning(
        "API error: %s — %s",
        exc.code,
        exc.message,
        extra={"method": request.method, "path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — return 500 with safe message."""
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
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


# ── Routers ──────────────────────────────────────────────────────────────

from api.app.routers.agents import router as agents_router  # noqa: E402
from api.app.routers.keys import router as keys_router  # noqa: E402

app.include_router(agents_router)
app.include_router(keys_router)

# ── Routes ───────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    """Health check endpoint — used by Render and uptime monitors."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "service": "ai-identity-api",
    }


@app.get("/")
async def root():
    """Root endpoint — service info."""
    return {
        "service": "ai-identity-api",
        "version": settings.app_version,
        "docs": "/docs",
    }
