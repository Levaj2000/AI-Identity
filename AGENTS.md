# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Secrets Management (Non-Standard)

**CRITICAL**: This cluster uses Google Secret Manager + GKE CSI driver, NOT k8s Secrets.

Secrets are mounted as files at `/mnt/secrets/<KEY>` via `k8s/secretproviderclass.yaml`. Pods read these files and export as env vars before starting the app.

To read/write secrets:
```bash
# Read
gcloud secrets versions access latest --secret=ai-identity-RESEND_API_KEY --project=<project>

# Write/update
printf '%s' "$KEY" | gcloud secrets versions add ai-identity-RESEND_API_KEY --data-file=-

# Apply changes (pods must restart to see new values)
kubectl rollout restart deploy/api -n ai-identity
```

**DO NOT** use `kubectl create secret` - it will have no effect.

## Testing (SQLite Type Remapping Required)

Tests use in-memory SQLite, but models use PostgreSQL types. `api/tests/conftest.py` remaps `JSONB → JSON` and `UUID → Uuid()` at import time. This pattern is mandatory - tests will fail without it.

`User.org_id` is a FK to `organizations.id`. The shared `test_user` / `other_user` fixtures do not seed an Organization. If a test sets `user.org_id`, the test (or a local fixture) must `INSERT` the Organization first or every test errors with `FOREIGN KEY constraint failed` before assertions run. See `api/tests/test_audit_org_scoping.py:40-41` for the seed pattern.

## Verification Before Reporting Done

Never claim "tests pass" without running pytest and quoting its summary line verbatim (e.g. `===== 39 passed in 5.91s =====`). If tests cannot be executed in the current environment, say so — do not substitute static review for actual execution. Line counts (`wc -l`) and test counts (`pytest --collect-only -q | tail -1`) are different numbers; quote the pytest one.

Skipped tests are not passing tests. Report `57 passed, 6 skipped` separately — never roll skips into the green count. Tests that depend on env vars should set them via `monkeypatch` or `conftest.py`, not gate themselves with `pytest.skip("X not configured")`. A skip-on-missing-env pattern silently disables coverage exactly where it's most needed.

## Brand Consistency (Enforced by Pre-commit)

The "Four Pillars" (Identity → Policy → Compliance → Forensics) is canonical. Never write "three pillars". The pre-commit hook `scripts/check-pillar-consistency.sh` enforces this in `landing-page/`, `docs/`, and `marketing/` directories.

## Code Style (Ruff)

- Line length: 100 (not 88)
- Ignores: `E501` (line too long, handled by formatter), `B008` (FastAPI Depends pattern)
- CLI targets Python 3.9+, so `datetime.UTC` is forbidden there (use `datetime.now(UTC)` instead)

## Running Single Tests

```bash
# In Docker
docker compose exec api pytest api/tests/test_agents.py::test_create_agent -v

# Locally (requires .venv activation)
pytest api/tests/test_agents.py::test_create_agent -v
```

## Database Migrations

Migrations auto-run on `docker compose up` (the api container's `command:` chains `alembic upgrade head` before uvicorn). To run manually:
```bash
docker compose exec api alembic upgrade head
```

Alembic files are excluded from ruff linting (`exclude = ["alembic/"]` in `pyproject.toml`). Migrations are forward-only — no auto-generated downgrades to rely on.

## `common/` Is an Editable Package

`common/` is its own installable package (`common/setup.py`, name `ai-identity-common`). Local dev installs it editable: `pip install -e common/`. Existing module edits are picked up live, but **adding a new submodule may require a reinstall** before imports resolve. Both `api/` and `gateway/` import from it, so changes there affect both services.

## Bootstrapping Local Env

Use `make setup` — it runs `scripts/docker-setup.sh` which generates `.env` with cryptographically strong keys (master key, JWT secret, etc.). Do **not** hand-craft `.env` from `.env.example` for real keys; the example file uses placeholder values that will fail crypto operations.

## `make test` ≠ `pytest`

`make test` runs `pytest` separately inside the api and gateway containers and **skips `common/tests/`**. Bare `pytest` (per `pyproject.toml` `testpaths`) covers all three. If you only run `make test`, common-library regressions slip through.

## Ruff Format: Double Quotes

`[tool.ruff.format] quote-style = "double"` — auto-fixers that prefer single quotes will fight the formatter. Configure your editor accordingly.

## PR Workflow

Per `CONTRIBUTING.md`: open an issue first, wait for a maintainer to assign it, then branch from `main`. Don't open speculative PRs without a tracked issue.

PRs target `main` by default. Do not ask "which branch should this merge into" as a routine question — the answer is `main` for any completed work. Only ask if the user has explicitly signaled a stacked-PR workflow (e.g. "build on top of PR #X", "this depends on the unmerged `feat/Y` branch") or if the change is genuinely a fix to an unmerged feature branch rather than a new contribution. Default behavior: branch off `main`, target `main`, merge to `main`.
