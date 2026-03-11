"""AI Identity — API Server.

Identity service and admin API for managing AI agents,
API keys, capabilities, and policies.

Run: uvicorn api.app.main:app --reload --port 8001
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Identity — API",
    description="Identity service and admin API for AI agents",
    version="0.1.0",
)

# CORS — permissive for local dev, tighten for production
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
    return {"status": "ok", "service": "ai-identity-api"}


@app.get("/")
async def root():
    """Root endpoint — service info."""
    return {
        "service": "ai-identity-api",
        "version": "0.1.0",
        "docs": "/docs",
    }
