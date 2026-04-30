# Code Mode Rules (Non-Obvious Only)

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

## Test Fixtures: Seed FK Parents Before Setting `org_id`

`User.org_id` is a FK to `organizations.id` (`common/models/user.py:69`). The shared `test_user` / `other_user` fixtures in `api/tests/conftest.py` do **not** seed an `Organization` row. If your test needs a populated `user.org_id`, create the Organization first or every test using the fixture will error with `sqlite3.IntegrityError: FOREIGN KEY constraint failed` before any assertion runs.

Canonical seed pattern (see `api/tests/test_audit_org_scoping.py:40-41`):
```python
from common.models.organization import Organization

org = Organization(id=ORG_ID, name="Test Org", owner_id=owner.id, tier="business")
db_session.add(org)
db_session.commit()
```

Do not modify the shared `test_user` / `other_user` fixtures to set `org_id` without also adding Organization seeds — every other test file that depends on those fixtures will break.

## Verification Before Reporting Done

Never claim "tests pass" without running them and quoting the actual pytest summary line. Include it verbatim:
> `===== 39 passed in 5.91s =====`

If you cannot execute the tests in your current environment, say so explicitly. Do not substitute "the implementation looks correct" for "the tests pass."

Line count is not test count. A 725-line test file may contain 39 tests. `wc -l` and `pytest --collect-only -q | tail -1` report different numbers — quote the pytest one.

Skipped tests are not passing tests. Report `57 passed, 6 skipped` honestly — do not roll the skipped into the headline number. If the 6 skipped tests cover the most important paths (auth, escalation, idempotency), that is a 0-of-6 result on the actual logic, regardless of the green count.

## Don't Gate Tests on Real Env Vars

`pytest.skip("X_KEY not configured")` silently disables a test when `X_KEY` isn't in the environment. The result is a green test run that has tested nothing. Configure the dependency in the test instead — set a fake value via `monkeypatch.setattr(settings, "x_key", "test-value-xyz")` or seed it in `conftest.py` so the test always runs. Reserve env-gated skips for tests that genuinely require an external service that cannot be faked, and mark them with `@pytest.mark.integration` so they are excluded from unit runs deliberately, not invisibly.

## Mutate-Then-Read Bugs

When a handler mutates a field and then reads it for a derived value (logging, email payloads, return values), capture the original first. Reassigning state and then computing relative-to-state in the same scope produces values that look right in isolation but are wrong by the time they're used:

```python
# WRONG — by the time hours_overdue is computed, sla_due_at has been moved
ticket.sla_due_at = calculate_new_due_at(...)
hours_overdue = (now - ticket.sla_due_at).total_seconds() / 3600  # negative

# RIGHT — capture before mutation
original_due_at = ticket.sla_due_at
ticket.sla_due_at = calculate_new_due_at(...)
hours_overdue = (now - original_due_at).total_seconds() / 3600
```

## Boolean Resets Defeat Their Own Guards

If a query filters by `flag == False` to find work to do, and the handler sets `flag = True` then sets it back to `False` before returning, the guard is permanently disarmed. Either keep the flag set, or add a separate counter cap (e.g. `escalation_count >= 3`) to prevent infinite re-entry. Whenever you reset a flag inside the same handler that set it, write a regression test that runs the handler twice on the same row and asserts the second run is a no-op.

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

## File Editing Restrictions

Code mode can only edit files matching `\.py$|\.ts$|\.tsx$|\.js$|\.jsx$|\.json$|\.yaml$|\.yml$|\.toml$|\.md$|\.sh$|\.sql$`. Attempts to edit other files will be rejected with FileRestrictionError.

## `common/` Is an Editable Install

`common/` is its own pip package (`pip install -e common/`). Edits to existing modules hot-reload, but **new submodules require reinstall** before `from common.foo import ...` resolves. Both `api/` and `gateway/` import from `common/` — every change there is cross-service.

## Ruff Quote Style

`[tool.ruff.format] quote-style = "double"`. If your editor auto-fixes to single quotes, the formatter will reverse it on commit and the loop wastes time.

## Test Run Surface

`pyproject.toml` `testpaths = ["api/tests", "gateway/tests", "common/tests"]`. Bare `pytest` covers all three. `make test` only runs api + gateway in containers — common regressions are invisible from `make test`.

## Forward-Only Migrations

Alembic migrations auto-run on container start. Treat them as forward-only — there is no rollback playbook, so additive/safe changes only (no destructive column drops without a multi-step plan).

## No MCP or Browser Tools

Code mode does not have access to MCP servers or browser automation tools.
