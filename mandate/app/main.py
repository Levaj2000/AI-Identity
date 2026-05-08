"""AI Identity — Mandate Service.

Issues, stores, and verifies mandate documents: cryptographically signed
permission grants that bridge agent identity to commerce (H2 milestone).
Documents are stored in MongoDB Atlas; classical signatures use GCP KMS.

Run locally: uvicorn mandate.app.main:app --reload --port 8003
Run on GKE:  uvicorn mandate.app.main:app --host 0.0.0.0 --port $PORT
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
from mandate.app.database import close_db, init_db

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=f"ai-identity-mandate@{settings.app_version}",
        traces_sample_rate=0.2 if settings.environment == "production" else 1.0,
        send_default_pii=False,
        enable_tracing=True,
    )

setup_logging()
logger = logging.getLogger("ai_identity.mandate")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Mandate Service starting — env=%s version=%s",
        settings.environment,
        settings.app_version,
    )
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="AI Identity — Mandate Service",
    summary="Cryptographically signed permission grants for AI agents",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    servers=[
        {"url": "https://mandate.ai-identity.co", "description": "Production"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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


@app.middleware("http")
async def request_logging(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "%s %s → %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    safe_detail = sanitize(str(exc.detail)) if exc.detail else "An error occurred"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": safe_detail}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An unexpected error occurred"}},
    )


from mandate.app.routers.mandates import router as mandates_router  # noqa: E402
from mandate.app.routers.verify import router as verify_router  # noqa: E402

app.include_router(mandates_router)
app.include_router(verify_router)


@app.api_route("/health", methods=["GET", "HEAD"], tags=["health"])
async def health():
    return {"status": "ok", "version": settings.app_version, "service": "ai-identity-mandate"}


@app.get("/", tags=["health"])
async def root():
    return {"service": "ai-identity-mandate", "version": settings.app_version, "docs": "/docs"}
