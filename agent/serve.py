"""Ada serve — ADK API + polished chat UI on one port.

Run from `agent/`:

    python serve.py            # http://127.0.0.1:8000
    python serve.py --port 8765
    python serve.py --host 0.0.0.0 --port 8000   # share on LAN
"""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app

AGENTS_DIR = Path(__file__).parent.resolve()
# Hidden so ADK's AgentLoader (which scans non-dotfile subdirs of AGENTS_DIR)
# doesn't try to load the static UI as an agent.
UI_DIR = AGENTS_DIR / ".ui"


def build_app(*, host: str, port: int):
    app = get_fast_api_app(
        agents_dir=str(AGENTS_DIR),
        web=False,
        allow_origins=["*"],
        host=host,
        port=port,
    )

    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def _root():
        return RedirectResponse(url="/ui/")

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
