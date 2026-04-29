# Support Ticket System — Deployment Reference

This document describes how the support ticket system reaches production. It
is a *reference for the existing automated pipeline*, not a manual runbook —
the deploy is fully automated on push to `main`.

The system shipped in [PR #193](https://github.com/Levaj2000/AI-Identity/pull/193)
on 2026-04-29.

## Components

| Component | Where it runs | How it deploys |
|---|---|---|
| Alembic migration `v3s4t5u6v7w8_add_support_tickets` | Neon Postgres (prod branch) | One-shot k8s Job, run automatically before API rollout |
| API router `api/app/routers/support_tickets.py` | GKE (`api` deployment) | Rolling deploy via `.github/workflows/deploy-gke.yml` |
| Dashboard pages, modal, sidebar entry | Vercel | Auto-deploy on push to `main` (`dashboard/vercel.json`) |

## The deploy pipeline

`.github/workflows/deploy-gke.yml` triggers on pushes to `main` that touch
`alembic/**`, `api/**`, `gateway/**`, `common/**`, or `k8s/**`. PR #193
matched on multiple paths, so the workflow ran end-to-end.

### Order of operations

1. **Build + sign API image** (Cosign + Binary Authorization)
2. **Run Alembic migration as a k8s Job** — `k8s/migration-job.yaml`
   - Workflow deletes any prior `alembic-migrate` Job
   - Substitutes the freshly-signed API image digest into the manifest
   - `kubectl apply -f k8s/migration-job.yaml`
   - `kubectl wait --for=condition=complete --timeout=300s job/alembic-migrate`
   - On failure: `kubectl describe` + last 500 log lines surfaced in CI; rollout aborts
3. **Roll out API and gateway deployments** — only after the migration Job completes successfully
4. **Vercel** picks up the same `main` push and ships the dashboard independently

This ordering is enforced by the workflow, not by humans. Pods never start
against a stale schema because step 3 is gated on step 2.

### Why a Job, not an initContainer

The migration runs as a one-shot Job (with its own image-signing and CSI
secret mount) rather than an initContainer on the API pods, so:

- migration logs are captured even when no API pods are running yet
- a failed migration blocks the rollout cleanly instead of crash-looping pods
- secrets live in the same Secret Manager CSI pattern used by `api` / `gateway`

See the header comment in `k8s/migration-job.yaml` for the full rationale,
including the 2026-04-16 reconciliation block that handles the orphan
`audit_log_outbox` / `audit_log_sinks` tables.

## What this migration does

`alembic/versions/v3s4t5u6v7w8_add_support_tickets.py` is **additive only**:

- Creates `support_tickets` table
- Creates `ticket_comments` table
- Creates supporting indexes (status, priority, category, user, org, agent)
- Adds foreign keys to `users`, `organizations`, `agents`, `audit_logs`
  with appropriate `ON DELETE` behavior

No existing tables are modified. No data is backfilled. The migration is
forward-compatible — old API pods continue to work against the new schema
while the rollout is in progress.

## Verification after deploy

Post-deploy smoke checks (run automatically by `.github/workflows/qa-smoke-test.yml`):

```bash
# API endpoint reachable
curl -fsSL https://api.ai-identity.co/api/v1/tickets \
  -H "Authorization: Bearer $TOKEN"

# Dashboard route loads
curl -fsSL https://app.ai-identity.co/dashboard/support
```

Manual UI verification:

1. Navigate to `/dashboard/support` — list page renders
2. Click **New Ticket** — modal opens, form submits
3. Click an existing ticket — detail page loads with comments
4. As an admin, change status — update persists

## Rollback

Forward-only schema changes; rollback is a code revert, not a `downgrade`:

1. Revert the offending commit on `main`
2. Workflow redeploys API + gateway against the new (still-extended) schema
3. The `support_tickets` and `ticket_comments` tables remain — empty if no
   tickets were created, otherwise preserved for forensics

A literal `alembic downgrade` against prod is **not** part of the rollback
path; it would require additional review (drops live tables) and is
intentionally not automated.

## What you do *not* need to do

These steps appeared in earlier draft documentation and are **incorrect** for
this codebase:

- Manually running `alembic upgrade head` against the production database
- Manually redeploying the API service
- Manually deploying the dashboard

All three happen automatically on merge to `main`. The pipeline is the source
of truth.

## Related references

- `k8s/migration-job.yaml` — migration Job manifest (with inline rationale)
- `.github/workflows/deploy-gke.yml` — GKE deploy workflow
- `.github/workflows/migration-check.yml` — PR-time migration validation
- `.github/workflows/qa-smoke-test.yml` — post-deploy smoke checks
- `dashboard/vercel.json` — dashboard deploy config
- `docs/support-ticket-system-spec.md` — feature spec
- `docs/support-ticket-architecture.md` — architecture diagrams
- `docs/support-ticket-implementation-plan.md` — implementation plan
