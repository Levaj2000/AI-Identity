# Advance Mode Rules (Non-Obvious Only)

## Secrets Management Pattern

Never use `kubectl create secret` - this cluster uses Google Secret Manager with CSI driver. Secrets are files at `/mnt/secrets/<KEY>`, not k8s Secret objects. See `k8s/secretproviderclass.yaml`.

## SQLAlchemy Type Remapping for Tests

Tests use SQLite but models use PostgreSQL. `api/tests/conftest.py` remaps types at import:
```python
# JSONB → JSON, UUID → Uuid()
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()
        elif isinstance(column.type, UUID):
            column.type = Uuid()
```

This pattern is mandatory - copy it when adding new test files.

## Enum Storage Pattern

SQLAlchemy stores enum values as strings in the database, not as enum objects. When passing to functions, use the field directly:
```python
# CORRECT
priority=ticket.priority  # Already a string

# WRONG - causes AttributeError
priority=ticket.priority.value  # .value doesn't exist
```

## CLI Python Version Constraint

CLI targets Python 3.9+ for offline verification. Use `datetime.now(UTC)` instead of `datetime.UTC` (requires 3.11+). This is enforced by ruff: `"cli/**" = ["UP017"]` in `pyproject.toml`.

## Brand Consistency Hook

Pre-commit enforces "Four Pillars" (never "three pillars") in `landing-page/`, `docs/`, `marketing/`. See `scripts/check-pillar-consistency.sh`.

## `common/` Is an Editable Install

`common/` is its own pip package (`pip install -e common/`). Edits to existing modules hot-reload, but **new submodules require reinstall** before `from common.foo import ...` resolves. Changes affect both `api/` and `gateway/`.

## Ruff Quote Style

`[tool.ruff.format] quote-style = "double"`. Editor auto-fixers that prefer single quotes will fight the formatter on every commit.

## Test Run Surface

`testpaths` in `pyproject.toml` covers `api/tests`, `gateway/tests`, **and** `common/tests`. `make test` only exercises api + gateway containers and skips `common/tests` — run `pytest` directly to catch shared-library regressions.

## Forward-Only Migrations

Alembic migrations auto-run on container start. No rollback playbook — design changes additively.

## Secrets Touch Production

Any `gcloud secrets versions add ...` writes to live infrastructure. Pair with `kubectl rollout restart deploy/<svc> -n ai-identity` to make pods see the new value. Confirm with the user before rotating production secrets.

## MCP and Browser Tools Available

Advance mode has access to MCP servers and browser automation tools that Code mode does not.
