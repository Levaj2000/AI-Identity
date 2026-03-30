# Change Management Policy

**Document Owner:** Jeff Leva, CEO
**Version:** 1.0
**Last Reviewed:** March 30, 2026
**Next Review:** June 25, 2026

---

## 1. Purpose

This policy defines how code, configuration, and infrastructure changes are proposed, reviewed, tested, deployed, and rolled back at AI Identity. All changes to production follow this process.

## 2. Change Workflow Overview

```
Feature branch --> Pre-commit hooks --> Push --> CI (GitHub Actions) --> PR review --> Merge to main --> Auto-deploy (Render/Vercel)
```

No changes reach production without passing through this pipeline. Direct commits to `main` are blocked by GitHub branch protection rules.

## 3. Pre-Commit Checks

Every developer workstation runs pre-commit hooks (configured in `.pre-commit-config.yaml`) that enforce quality before code leaves the local machine:

- **trailing-whitespace** and **end-of-file-fixer** -- File hygiene
- **check-yaml** and **check-json** -- Config file validation
- **check-added-large-files** -- Blocks files over 500 KB
- **ruff** -- Python linting with auto-fix (`ruff check --fix`)
- **ruff-format** -- Python code formatting
- **eslint** -- TypeScript/React linting (dashboard)
- **prettier** -- TypeScript/React formatting (dashboard)

## 4. Continuous Integration

GitHub Actions CI (`.github/workflows/ci.yml`) runs on every push to `main` and every pull request. The pipeline has two parallel jobs:

**Python -- Lint & Test:** Ruff linting, Ruff format check, and `pytest -v` against a test database (Python 3.11).

**Dashboard -- Lint, Format & Build:** ESLint, Prettier check, TypeScript type check (`tsc -b --noEmit`), and production build (Node.js 22).

Both jobs must pass before a PR can be merged. Failed CI blocks the merge button.

## 5. Pull Request Review

- All changes require a pull request targeting `main`.
- The PR description must explain what changed and why.
- At minimum, the PR author reviews the diff before merging (solo-founder context). When additional team members are onboarded, a second reviewer will be required.
- PRs that touch authentication, encryption, or billing logic receive extra scrutiny and a more detailed description.

## 6. Deployment

**API and Gateway (Render):**
- Merging to `main` triggers automatic deployment on Render for both `ai-identity-api` and `ai-identity-gateway`.
- Render performs a fresh build using the commands in `render.yaml` and runs a zero-downtime deploy.
- The `/health` endpoint is checked before the new instance receives traffic.

**Dashboard (Vercel):**
- Merging to `main` triggers automatic deployment on Vercel.
- Vercel provides preview deployments on every PR for visual verification before merge.

**Keepalive Cron:**
- The `ai-identity-keepalive` cron job runs every 10 minutes and pings health endpoints to prevent cold starts on Render's Starter tier.

## 7. Database Migrations

- Schema changes are managed with **Alembic** (migration files in `alembic/versions/`).
- Each migration has an `upgrade()` and `downgrade()` function for reversibility.
- Migration PRs include the generated Alembic file and a description of the schema change.
- Migrations run as part of the deployment process against the Neon PostgreSQL database.
- Breaking schema changes (column drops, type changes) require a two-phase migration: deploy the code that handles both schemas first, then deploy the migration.

## 8. Rollback Procedures

**Application rollback (Render):**
1. Open the Render dashboard for the affected service.
2. Navigate to the deploy history and select the last known-good deploy.
3. Click "Rollback" to redeploy the previous build immediately.
4. Verify via `/health` and Sentry error rates.

**Database rollback (Alembic):**
1. Identify the target migration revision.
2. Run `alembic downgrade <revision>` against the Neon database.
3. Deploy the corresponding application code if needed.

**DNS/CDN rollback (Cloudflare):**
- Revert DNS changes in the Cloudflare dashboard. Changes propagate within seconds due to low TTL settings.

## 9. Change Windows

**Current policy (< 50 users, free tier):** No formal change window. All deployments are continuous via CI/CD with zero-downtime deploys. Standard releases, bug fixes, and feature additions deploy on merge to `main` at any time.

**Formal change window trigger — established when ANY of these conditions are met:**
- First paying customer is onboarded
- Monthly active users exceed 100
- Enterprise contract is signed

**Planned future change window:** Tuesdays 6:00-10:00 AM ET for:
- Breaking API changes (response shape changes, endpoint deprecation)
- Destructive database migrations (column drops, type changes)
- Infrastructure changes (scaling, region changes, provider switches)

Standard deploys (bug fixes, new features, additive migrations) remain continuous and are not restricted to the change window.

**Customer notification requirements:**

| Change Type | Notice Period | Channel |
|-------------|--------------|---------|
| Breaking API change | 14 days | Email + dashboard banner + API deprecation header |
| Planned maintenance | 48 hours | Email + status page |
| Emergency hotfix | Best effort | Status page updated in real-time |

## 10. Emergency Hotfix Process

When a P1 or P2 incident requires an immediate fix:

1. Create a branch from `main` with the prefix `hotfix/`.
2. Implement the minimal fix. Pre-commit hooks still run locally.
3. Push and open a PR. CI runs automatically.
4. If CI passes, merge immediately (review can be post-merge for P1).
5. Render auto-deploys the fix.
6. Conduct a post-incident review within 48 hours (see Incident Response Plan).

For P1 incidents where CI is too slow, Render's manual deploy can be triggered from a specific commit. This is logged and reviewed in the postmortem.

## 11. Change Log and Audit Trail

- **Git history** provides a complete, immutable record of every code change, including author, timestamp, and PR reference.
- **Render deploy events** log every deployment with commit SHA, timestamp, and success/failure status.
- **Vercel deploy events** provide the same for dashboard deployments.
- **Alembic migration history** tracks every schema change with a unique revision ID.
- **Audit logs** (HMAC-chained) record runtime events including API key creation, credential changes, and administrative actions.

---

## SOC 2 Mapping

| Trust Services Criteria | How This Policy Addresses It |
|------------------------|------------------------------|
| CC8.1 -- Change management process | Sections 2-6: defined workflow from branch to production with automated gates |
| CC8.2 -- Testing before deployment | Sections 3-4: pre-commit hooks and CI pipeline with lint, type checks, and tests |
| CC8.3 -- Change approval | Section 5: PR review requirement, branch protection on `main` |
| CC8.4 -- Emergency changes | Section 9: hotfix process with post-merge review |
| CC8.5 -- Configuration management | Section 7: Alembic migrations, `render.yaml` as infrastructure-as-code |
| CC7.5 -- Rollback and recovery | Section 8: rollback procedures for application, database, and DNS |
| CC1.1 -- Accountability | Section 10: git history, deploy logs, and HMAC-chained audit trail |
