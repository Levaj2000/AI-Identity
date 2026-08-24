# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Working as a Delegated / Offload Agent

Tasks are often delegated here to run autonomously. Own the task end-to-end to the same bar as a clean handoff: a root-cause fix, tests, a fully green suite, and a tight diff.

**Definition of done — all of these, in order:**
1. **Plan first.** State the root cause and intended change before editing. For anything past a one-line fix, outline the approach.
2. **Fix the cause, not the symptom.** Prefer the defensive/correct fix over a patch that just silences the error.
3. **Add or update tests** that would have caught the bug. New behavior without a test is not done.
4. **Run the FULL suite and quote summaries verbatim** — backend `pytest` (covers api + gateway + common + mandate; bare `pytest`, not just `make test` — see "`make test` ≠ `pytest`") AND frontend `cd dashboard && npm test` (Vitest). Report passes and skips separately (see "Verification Before Reporting Done").
5. **Keep the diff tight.** Touch only what the task needs. Don't refactor adjacent code, reformat unrelated lines, or "improve" things unasked — surface those as a note instead.
6. **Report with evidence** — quoted test summaries, files changed, what was verified. No "should work."

**Stop and hand back (do NOT autonomously merge) when the task touches:**
- **OCSF / standards work** — schema files, `attestation.json`, profiles, anything feeding PRs #1641/#1661/#1662. Public-facing and reputation-bearing; facts and framing need a human pass.
- **Architecture / build-vs-buy** — new external dependencies, or any change to a public API contract.
- **Secrets, infra, or production migrations** — Secret Manager, GKE/deploy manifests, forward-only Alembic migrations.
- **Public-facing copy** — landing-page/marketing/docs claims (the "Four Pillars", no-vaporware code-state claims).
- **Ambiguous scope** — if the task could mean two things, ask rather than guess.

Green to fully own: bugfixes with a clear repro, test/coverage additions, mechanical refactors within a file, dependency-level fixes — anything where a passing full suite is sufficient proof. (The Sentry transaction-filter fix in #359 is the model: defensive fix + new tests + full suite green + clean merge.)

## This Repo Is Public — Drafts and Prep Are Never Committed

Everything tracked here is world-readable. Two consequences:

- **Reply/comment drafts, outreach prep, strategy notes, and reviewer notes about named people do NOT get committed.** Deliver draft replies in chat, or write them to `private/` (gitignored). This applies to Slack replies, GitHub comment drafts, issue-filing prep, and any `*.notes.md`. `docs/` is only for artifacts meant to be linked publicly (reference bundles, class drafts, the crosswalk, specs).
- **CHANGELOG entries describe what shipped, not why strategically.** No negotiation posture, no notes about collaborators' access or availability, no "the play here is…" framing — that context goes in `private/` session notes.

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

`common/` is its own installable package (`common/setup.py`, name `ai-identity-common`). Local dev installs it editable: `pip install -e common/`. Existing module edits are picked up live, but **adding a new submodule may require a reinstall** before imports resolve. Both `api/` and `gateway/` import from it, so changes there affect both services. In the deployed images and CI it is installed with `--no-deps` — its `install_requires` ranges must stay satisfiable by the locks (they are all pinned there), so **never add a dependency to `common/setup.py` without also adding it to each service's `requirements.txt` and regenerating the locks**.

## Dependency Locks & Hermetic Image Builds (PyPI-yank immunity)

Context: on 2026-07-24 `liboqs-python==0.15.0` vanished from PyPI and broke every GKE deploy (#405). The deploy path no longer trusts PyPI at build time.

- **Locks**: `api|gateway|mandate/requirements.lock` pin the full transitive graph with hashes, cross-resolved for the image platform. **After ANY edit to a `requirements.txt`, regenerate that service's lock** — the exact `uv pip compile` command is in each lock's header — or the `lockfile-consistency` CI job (`scripts/check_lockfiles.py`) fails the PR. The three locks are each internally consistent but NOT jointly resolvable (transitive pins differ between services) — always install/download per-lock.
- **Image builds are hermetic**: the three deploy Dockerfiles install with `--no-index --find-links=/wheelhouse --require-hashes` from a BuildKit bind mount. pip physically cannot reach PyPI during an image build; a deletion/yank upstream cannot fail a deploy.
- **The wheelhouse** is populated in CI by `.github/actions/populate-wheelhouse`: per-lock `pip download` from the `pypi-cache` Artifact Registry **remote repo** (us-east1, pull-through proxy of PyPI — cached artifacts keep serving after upstream deletion), `actions/cache`d on the locks' hash. The deploy SA needs no extra grant (project-level `artifactregistry.writer` covers reads).
- **Pre-merge proof**: `image-build-check.yml` builds all three images with `--no-index` on any PR touching Dockerfiles or locks — a lock/Dockerfile mistake surfaces on the PR, not in the deploy.
- **New/bumped pins**: after regenerating a lock, the first CI run warms the AR cache automatically when the wheelhouse step downloads the new version (runner → AR → PyPI). Nothing manual.
- **Local image builds** need a wheelhouse first: `python3 -m pip download --only-binary=:all: --platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 --platform manylinux1_x86_64 --python-version 311 --implementation cp -r <svc>/requirements.lock -d wheelhouse` (plain PyPI is fine locally). Day-to-day local dev is unaffected: `docker compose` uses the root `Dockerfile`, which deliberately still installs from PyPI.
- **Known out of scope**: the root `Dockerfile` (compose local dev) is non-hermetic — off the GKE deploy path. `agent/requirements.txt` is exact-pinned (no lock — Ada builds manually via `agent/cloudbuild.yaml`, outside the wheelhouse machinery); regenerate pins deliberately, and if Ada ever joins CI deploys, add a hashed `agent/requirements.lock` and list `agent` in `scripts/check_lockfiles.py`.

## Bootstrapping Local Env

Use `make setup` — it runs `scripts/docker-setup.sh` which generates `.env` with cryptographically strong keys (master key, JWT secret, etc.). Do **not** hand-craft `.env` from `.env.example` for real keys; the example file uses placeholder values that will fail crypto operations.

## `make test` ≠ `pytest`

`make test` runs `pytest` separately inside the api and gateway containers and **skips both `common/tests/` and `mandate/tests/`**. Bare `pytest` (per `pyproject.toml` `testpaths`) covers all four — `api`, `gateway`, `common`, `mandate`. If you only run `make test`, common-library and mandate-service regressions slip through.

## Ruff Format: Double Quotes

`[tool.ruff.format] quote-style = "double"` — auto-fixers that prefer single quotes will fight the formatter. Configure your editor accordingly.

## PR Workflow

Per `CONTRIBUTING.md`: open an issue first, wait for a maintainer to assign it, then branch from `main`. Don't open speculative PRs without a tracked issue.

PRs target `main` by default. Do not ask "which branch should this merge into" as a routine question — the answer is `main` for any completed work. Only ask if the user has explicitly signaled a stacked-PR workflow (e.g. "build on top of PR #X", "this depends on the unmerged `feat/Y` branch") or if the change is genuinely a fix to an unmerged feature branch rather than a new contribution. Default behavior: branch off `main`, target `main`, merge to `main`.

## Private Strategy Documents Live in Notion, Not Here

Private strategy and relationship documents (commercial planning, partner
memos, anything marked PRIVATE) are maintained in the owner's Notion
workspace — that is their canonical home. **Never commit them to this
repository**, including under a `private/` directory, and never quote their
contents into public artifacts, PR bodies, or issue comments. When revising
one, update its Notion page rather than creating a repo file; a file handed
around in chat is an export, not the document. The public-repo CI gate
("no confidential material") is a backstop, not the policy.
