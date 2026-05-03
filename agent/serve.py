"""Ada serve — ADK API + polished chat UI on one port.

Run from `agent/`:

    python serve.py            # http://127.0.0.1:8000
    python serve.py --port 8765
    python serve.py --host 0.0.0.0 --port 8000   # share on LAN
"""

from __future__ import annotations

import argparse
import logging
import subprocess
from pathlib import Path

import uvicorn
from auth import ADA_ADMIN_KEY, allowed_origins, auth_middleware, auth_required
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app

logger = logging.getLogger(__name__)

AGENTS_DIR = Path(__file__).parent.resolve()
# Hidden so ADK's AgentLoader (which scans non-dotfile subdirs of AGENTS_DIR)
# doesn't try to load the static UI as an agent.
UI_DIR = AGENTS_DIR / ".ui"


def _startup_sha() -> str:
    """Capture the git SHA at process start so /version reflects loaded code,
    not what's on disk now (which may have moved underneath us)."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(AGENTS_DIR),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
        return out.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "unknown"


STARTUP_SHA = _startup_sha()


def build_app(*, host: str, port: int):
    origins = allowed_origins()
    app = get_fast_api_app(
        agents_dir=str(AGENTS_DIR),
        web=False,
        allow_origins=origins,
        host=host,
        port=port,
    )

    # Register the auth middleware AFTER ADK's own middleware stack so it runs
    # first on incoming requests (Starlette runs middleware last-added-first).
    app.middleware("http")(auth_middleware)

    if auth_required() and not ADA_ADMIN_KEY:
        logger.error(
            "ADA_REQUIRE_AUTH=1 but neither ADA_ADMIN_KEY nor AI_IDENTITY_ADMIN_KEY is set; "
            "protected routes will return 503"
        )
    elif not auth_required():
        logger.warning("Ada auth disabled (ADA_REQUIRE_AUTH != 1). Set to 1 in production deploys.")
    if host not in ("127.0.0.1", "localhost") and not auth_required():
        logger.error(
            "Server bound to %s without ADA_REQUIRE_AUTH=1 — exposing Ada past localhost "
            "without auth. Set ADA_REQUIRE_AUTH=1 and configure ADA_ADMIN_KEY before sharing.",
            host,
        )

    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def _root():
        return RedirectResponse(url="/ui/")

    @app.get("/version", include_in_schema=False)
    async def _version():
        return {
            "sha": STARTUP_SHA,
            "short": STARTUP_SHA[:8] if STARTUP_SHA != "unknown" else "unknown",
        }

    @app.get("/healthz", include_in_schema=False)
    async def _healthz():
        return {"status": "ok"}

    return app


def main():
    parser = argparse.ArgumentParser(description="Ada API + UI server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    app = build_app(host=args.host, port=args.port)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
