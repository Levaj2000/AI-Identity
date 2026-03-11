"""AI Identity — Proxy Gateway.

Runtime gateway that authenticates agent API keys,
evaluates policies, and forwards or blocks requests.

Run: uvicorn gateway.app.main:app --reload --port 8002
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Identity — Gateway",
    description="Proxy gateway for AI agent request routing and policy enforcement",
    version="0.1.0",
)

# CORS — the gateway proxies requests, so CORS is more restrictive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "ai-identity-gateway"}


@app.get("/")
async def root():
    """Root endpoint — service info."""
    return {
        "service": "ai-identity-gateway",
        "version": "0.1.0",
        "docs": "/docs",
    }
