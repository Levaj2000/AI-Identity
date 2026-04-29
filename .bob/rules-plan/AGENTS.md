# Plan Mode Rules (Non-Obvious Only)

## Architecture Constraints

- **api/** and **gateway/** are separate FastAPI services (ports 8001, 8002) that share code via **common/**
- **common/** contains SQLAlchemy models, Pydantic schemas, auth utilities - changes here affect both services
- **cli/** is intentionally single-file, zero-dependency for offline/air-gapped forensic verification (Python 3.9+ target)

## Secrets Management (Non-Standard Infrastructure)

This cluster uses Google Secret Manager + GKE CSI driver, NOT k8s Secrets. Secrets are files at `/mnt/secrets/<KEY>`, not Secret objects. Any plan involving secrets must use `gcloud secrets` commands, not `kubectl create secret`. See `k8s/secretproviderclass.yaml`.

## Testing Architecture

Tests use in-memory SQLite but production uses PostgreSQL. `api/tests/conftest.py` performs type remapping at import time (`JSONB → JSON`, `UUID → Uuid()`). New test files must follow this pattern or fail.

## Database Migration Strategy

Migrations auto-run on container start via `docker-compose.yml` command. Alembic files are excluded from linting (`exclude = ["alembic/"]` in `pyproject.toml`). Plan for forward-only migrations.

## CLI Design Constraint

CLI targets Python 3.9+ for maximum compatibility in offline environments. This means `datetime.UTC` (3.11+) is forbidden - use `datetime.now(UTC)`. Enforced by ruff per-file ignore.

## Brand Consistency Enforcement

"Four Pillars" (Identity → Policy → Compliance → Forensics) is canonical and enforced by pre-commit hook in `landing-page/`, `docs/`, `marketing/`. Plans involving these directories must use this terminology.

## `common/` Is an Editable Package

`common/` is its own installable pip package (`ai-identity-common`, `pip install -e common/`), imported by both `api/` and `gateway/`. Plans that change shared models, schemas, or auth helpers must account for the cross-service blast radius and the editable-install reinstall step when adding new submodules.

## Test Coverage Surface

`pyproject.toml` `testpaths` covers `api/tests`, `gateway/tests`, **and** `common/tests`. `make test` only runs api + gateway in containers — plans that rely on CI catching common-library regressions must invoke bare `pytest` (or extend `make test`).

## Pre-commit Brand + Format Coverage

Pre-commit runs ruff (lint + format), ESLint and Prettier (dashboard-only via `cd dashboard`), `--allow-multiple-documents` YAML check, and the Four Pillars hook. Plans touching `landing-page/`, `docs/`, or `marketing/` must keep canonical terminology; plans touching `dashboard/` must keep ESLint + Prettier clean.

## Forward-Only Migration Strategy

Confirmed by `alembic/` layout — no rollback playbook is maintained. Plans involving destructive schema changes (drop column, narrow type) need a multi-phase staging: add new → backfill → swap reads → swap writes → drop old.

## CI / Mypy

`pyproject.toml` configures mypy strict, but **verify whether mypy actually runs in CI before relying on it as a gate** — it is not in `.pre-commit-config.yaml`. If a plan assumes type-check enforcement, validate the actual pipeline first.

## File Editing Restrictions

Plan mode can only edit markdown files (`\.md$`). Attempts to edit code files will be rejected with FileRestrictionError.
