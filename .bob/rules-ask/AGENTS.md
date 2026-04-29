# Ask Mode Rules (Non-Obvious Only)

## Architecture Context

- `api/` = FastAPI identity service (port 8001), NOT a generic API directory
- `gateway/` = FastAPI proxy with policy enforcement (port 8002), separate from API
- `common/` = Shared SQLAlchemy models, Pydantic schemas, auth utilities - imported by both api/ and gateway/
- `cli/` = Single-file, zero-dependency Python script for offline forensic verification (targets Python 3.9+)

## Secrets Management (Non-Standard)

This cluster uses Google Secret Manager + GKE CSI driver, NOT k8s Secrets. Secrets are mounted as files at `/mnt/secrets/<KEY>`. Never suggest `kubectl create secret` commands - they have no effect. See `k8s/secretproviderclass.yaml` for the actual pattern.

## Testing Infrastructure

Tests use in-memory SQLite but models use PostgreSQL types. `api/tests/conftest.py` performs type remapping at import time (`JSONB → JSON`, `UUID → Uuid()`). This is not obvious from file structure.

## Brand Voice

"Four Pillars" (Identity → Policy → Compliance → Forensics) is canonical and enforced by pre-commit hook. Never say "three pillars". See `scripts/check-pillar-consistency.sh`.

## CLI Python Version

CLI targets Python 3.9+ for maximum compatibility in offline/air-gapped environments. This means `datetime.UTC` (3.11+) is forbidden - use `datetime.now(UTC)` instead. Enforced by ruff config.

## Database Migrations

Migrations auto-run on `docker compose up` via the api container's command. Alembic files are excluded from ruff linting (`exclude = ["alembic/"]` in `pyproject.toml`). Treat them as forward-only — no downgrade path is maintained.

## `common/` Is a Shared Editable Package

`common/setup.py` declares `ai-identity-common`. It's installed editable in dev (`pip install -e common/`) and imported by both `api/` and `gateway/`. When the user asks "where does X live," shared models / auth / schemas / config are in `common/`, not duplicated in the services.

## Service Topology

Three deployable units, all on Render/GKE:
- `api/` (FastAPI, port 8001) — identity service
- `gateway/` (FastAPI, port 8002) — policy enforcement proxy
- `dashboard/` (React + Vite + TypeScript, separate package) — admin UI

The `cli/` is not deployed — it's a single-file forensic verification script users download.

## PR Process

`CONTRIBUTING.md` requires opening an issue first, then waiting for maintainer assignment before opening a PR. If a user asks how to contribute a change, point them at the issue tracker first.
