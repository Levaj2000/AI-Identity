# Incident Report: Audit Infrastructure Failure

**Incident ID:** INC-2026-04-16-001
**Severity:** P0 — Production data loss (forensic audit chain)
**Date:** April 13–16, 2026
**Duration:** ~72 hours (silent); ~3.5 hours (active remediation)
**Author:** Jeff Leva + Claude Code
**Status:** Resolved

---

## Executive Summary

For approximately 72 hours (2026-04-13 18:19 UTC through 2026-04-16 22:14 UTC), **zero audit log entries were written in production**. The AI Identity forensic audit chain — the core product value proposition for compliance buyers — had a complete gap. The root cause was a missing migration step in the GKE deploy pipeline: code that wrote new database columns shipped to production, but the schema migrations that add those columns never ran.

The incident was detected by a QA Admin Check that returned 4/15 instead of 15/15. The failing step (Create agent → HTTP 500) led to the discovery that `audit_log.org_id` and `audit_log.correlation_id` columns did not exist in the production database, despite being referenced by code deployed 3 days earlier.

**Impact:**
- 138 existing audit log entries retained integrity (no data corruption)
- ~72 hours of new audit events were silently dropped (gateway) or returned HTTP 500 (API agent CRUD)
- Agent create/delete/key-rotate operations returned 500 to any caller
- No customer data was lost or exposed — this was an availability + evidence-integrity incident, not a confidentiality incident

---

## Timeline

All times UTC.

### 2026-04-13 — Silent onset

| Time | Event |
|------|-------|
| ~16:00 | PRs #134, #135, #137, #138 merge. These add `org_id` and `correlation_id` to the `audit_log` model and introduce the audit-forwarding outbox. Three Alembic migrations (`o6`, `p7`, `q8`) are added to the codebase. |
| ~16:05 | GKE deploy workflow triggers. Builds new API + Gateway images with the updated SQLAlchemy models. **Does not run `alembic upgrade head`** — the workflow has no migration step. |
| ~16:10 | New pods roll out. First request hits `create_audit_entry()`, which now passes `org_id` and `correlation_id` to the `AuditLog` constructor. PostgreSQL rejects the INSERT: `column "org_id" of relation "audit_log" does not exist`. |
| 16:10–18:19 | **Gateway path**: every audit write fails silently. The `except Exception: logger.exception(...)` block in `gateway/app/enforce.py:573` swallows the error. Sentry's `LoggingIntegration` deduplicates the `logger.exception` calls into a single event. No Prometheus counter exists for audit-write failures. Enforcement decisions (allow/deny) still function — the gateway just can't record them. |
| 18:19 | Last successful audit log entry in the database (from the pre-deploy image, still draining). From this point forward: **zero writes** for 72 hours. |

### 2026-04-13 through 2026-04-16 — Undetected

- No alerts fire. Better Stack monitors point at retired Render URLs (`ai-identity-api.onrender.com`), not the live GKE endpoints. Both monitors are paused.
- No Prometheus metric tracks audit-write failures (the counter didn't exist yet).
- Sentry captures one deduplicated event from the gateway but it's not noticed in the inbox.
- The API path (`POST /api/v1/agents`, `DELETE /api/v1/agents`, key rotation) returns HTTP 500 on every call, but no one triggers these endpoints during the 72-hour window.

### 2026-04-16 — Detection and remediation

| Time (UTC) | Event |
|------|-------|
| 20:48 | QA Admin Check triggered from the dashboard. Step 5 (Create agent) returns HTTP 500. Sentry captures `ProgrammingError: column "org_id" of relation "audit_log" does not exist` (event `042beeeb81ab41c1acd6f8487984d369`). |
| 20:50 | Investigation begins. DB query confirms `audit_log` has zero entries since Apr 13. `alembic_version` is stuck at `n5j6k7l8m9n0` — three migrations behind HEAD. |
| 20:55 | Root cause identified: `deploy-gke.yml` triggers on `alembic/**` changes but never runs `alembic upgrade head`. Additionally, `audit_log_outbox` and `audit_log_sinks` tables exist in the DB despite `alembic_version` not tracking them (partial prior apply). |
| 21:00 | Neon snapshot branch `incident-audit-infra-2026-04-16` created as rollback safety net. |
| 21:15 | **PR #142** merges — adds a k8s migration Job to the deploy workflow + one-time reconciliation for orphan tables. Deploy fails: NetworkPolicy default-deny blocks the Job pod's egress to Neon. |
| 21:33 | **PR #145** merges — adds `alembic-migrate` to `allow-egress-postgres` NetworkPolicy + applies netpols on deploy. Deploy fails: migration o6's sentinel INSERT omits `requests_this_month` (NOT NULL, no DEFAULT on `organizations` table). |
| 21:46 | **PR #146** merges — adds quota columns to sentinel INSERT. Deploy fails: `users.org_id` is VARCHAR, `agents.org_id` is UUID, Postgres rejects implicit cast in backfill UPDATE. |
| 21:57 | **PR #147** merges — adds `::uuid` cast to backfill SQL. Deploy fails: `audit_log` has append-only trigger (`audit_log_no_update`) blocking the backfill UPDATEs. |
| 22:08 | **PR #148** merges — disables append-only trigger during backfill, re-enables after. |
| 22:14 | **Deploy succeeds.** All three migrations apply. API + Gateway pods roll out on fixed schema. First post-fix audit entry written at 22:14:03 UTC. |
| 22:14 | QA Admin Check re-run: **15/15 ALL PASSED.** |

---

## Root Cause

**Primary:** The GKE deploy workflow (`deploy-gke.yml`) did not include a migration step. It triggered on `alembic/**` path changes (so a migration PR would start a deploy), built and deployed new container images with updated SQLAlchemy models, but never applied the corresponding `alembic upgrade head` against the database. The new code expected columns that didn't exist.

**Contributing factors:**

1. **No migration step in CI/CD.** The workflow was ported from Render (which ran migrations as part of its build command) to GKE without adding an equivalent step. The Render-era migration path was implicit; the GKE path required an explicit Job or initContainer, and nobody added one.

2. **Silent audit-write failure in the gateway.** The `try/except` block in `gateway/app/enforce.py` around `create_audit_entry()` swallowed exceptions with only a `logger.exception()` call. Sentry's `LoggingIntegration` deduplicated repeated tracebacks into a single event. No Prometheus counter tracked audit-write failures. The failure was invisible to monitoring for 72 hours.

3. **Stale uptime monitors.** Better Stack monitors still pointed at the retired Render URLs (`ai-identity-api.onrender.com`). Both were paused. Even if the monitors had been active, they were checking dead endpoints — the production GKE endpoints (`api.ai-identity.co`, `gateway.ai-identity.co`) had no external uptime check.

4. **Partial prior migration state.** `audit_log_outbox` and `audit_log_sinks` tables existed in the database despite `alembic_version` not recording their creation. This inconsistency (likely from a prior aborted migration attempt) meant a naive `alembic upgrade head` would fail on `CREATE TABLE ... already exists`. The reconciliation block in the migration Job handled this, but it added complexity to the remediation.

5. **Migration not tested against production schema.** The migration was written and tested against a local/CI database that had different column defaults, types, and triggers than production. Three separate schema mismatches were discovered only during the production deploy attempt:
   - `organizations.requests_this_month` NOT NULL with no DEFAULT (PR #146)
   - `users.org_id` is VARCHAR vs `agents.org_id` is UUID (PR #147)
   - `audit_log` append-only trigger blocks UPDATE (PR #148)

---

## Impact Assessment

### What was affected

| System | Impact | Duration |
|--------|--------|----------|
| Audit log writes (gateway hot path) | Silently dropped — every enforcement decision (allow/deny) went unrecorded | 72 hours |
| Audit log writes (API path) | HTTP 500 on agent create/delete/key-rotate | 72 hours |
| Forensic audit chain integrity | Gap in the HMAC chain — 72 hours of events missing. Chain resumes from the last valid entry; no corruption of existing entries | 72 hours |
| Gateway enforcement decisions | Unaffected — policy evaluation and allow/deny still functioned correctly | None |
| Agent runtime (chat completions via gateway) | Unaffected — requests still proxied based on policy | None |
| Customer data | No exposure, no loss, no corruption | None |

### What was NOT affected

- **Enforcement was never compromised.** The gateway continued to evaluate policies and allow/deny requests correctly. Only the recording of those decisions failed.
- **Existing audit entries were not corrupted.** The 138 pre-incident entries retain their HMAC integrity chain. The chain has a gap (no entries for 72 hours), then resumes.
- **No customer data was exposed or lost.** This was an evidence-integrity incident, not a confidentiality or data-loss incident.

---

## Remediation

### Immediate fixes (deployed 2026-04-16)

| PR | What | Status |
|----|------|--------|
| [#142](https://github.com/Levaj2000/AI-Identity/pull/142) | Migration Job in deploy workflow — runs `alembic upgrade head` before pod rollout, blocks on failure | Merged |
| [#145](https://github.com/Levaj2000/AI-Identity/pull/145) | NetworkPolicy: add `alembic-migrate` to Postgres egress allow-list + apply netpols on deploy | Merged |
| [#146](https://github.com/Levaj2000/AI-Identity/pull/146) | Migration fix: include NOT-NULL quota columns in sentinel INSERT | Merged |
| [#147](https://github.com/Levaj2000/AI-Identity/pull/147) | Migration fix: cast VARCHAR→UUID in backfill SQL | Merged |
| [#148](https://github.com/Levaj2000/AI-Identity/pull/148) | Migration fix: disable append-only trigger during backfill | Merged |

### Observability improvements (deployed 2026-04-16)

| PR | What | Status |
|----|------|--------|
| [#143](https://github.com/Levaj2000/AI-Identity/pull/143) | `audit_write_failures_total` Prometheus counter + Sentry tags on gateway audit-write exceptions. Non-zero rate = page. | Merged |
| [#144](https://github.com/Levaj2000/AI-Identity/pull/144) | Uptime monitor runbook + Better Stack repointing checklist | Merged |

### Outstanding action items

| Item | Owner | Priority | Status |
|------|-------|----------|--------|
| Repoint Better Stack monitors to GKE endpoints per [docs/ops/uptime-monitors.md](../ops/uptime-monitors.md) | Jeff | High | TODO |
| Add Prometheus alert rule: `rate(ai_identity_audit_write_failures_total[5m]) > 0` → page | Jeff | High | TODO |
| Add migration dry-run to CI (run `alembic upgrade --sql head` against a Neon branch in the PR check, not just on deploy) | Jeff | Medium | TODO |
| Design decision: fail-closed on audit-write failure (reject requests vs. proceed without evidence) | Jeff | Medium | TODO |
| Delete Neon snapshot branch `br-silent-scene-adrhmpjm` after 7 days of green | Jeff | Low | TODO |
| Investigate adding DB-level DEFAULT to `organizations.requests_this_month` and `usage_reset_day` | Jeff | Low | TODO |

---

## Lessons Learned

### What went well

1. **QA checklist caught the incident.** The 15-step E2E Admin Check detected the failure on the first run after the deploy gap. The investment in the QA runner paid off — without it, the 72-hour gap could have extended indefinitely.

2. **Fail-closed enforcement was not compromised.** The gateway continued to correctly allow/deny requests throughout the incident. The separation between "make a decision" and "record the decision" meant that the security posture was maintained even when recording failed.

3. **The deploy guardrail worked.** The migration Job's `kubectl wait --timeout=300s` blocked the pod rollout on every failure. No stale code reached production during the 4 fix iterations — old pods kept serving the old schema while we iterated on the migration.

4. **Neon branching provided a safe rollback.** The snapshot branch taken at the start of remediation meant we could revert the database state instantly if any fix attempt corrupted data. (It wasn't needed, but having it removed pressure from the fix iterations.)

5. **Transactional DDL prevented partial state.** PostgreSQL's transactional DDL meant every failed migration attempt rolled back cleanly. Despite 4 failed runs of migration o6, the database was in a consistent state every time — no half-applied columns, no orphan rows.

### What went wrong

1. **The deploy pipeline had no migration step.** This is the simplest possible failure mode — the equivalent of deploying a Rails app without running `rake db:migrate`. The Render-to-GKE migration dropped the implicit migration path and nobody noticed.

2. **72 hours of silent failure.** The gateway's `try/except` block around audit writes was designed for resilience (don't let audit failures break enforcement) but became a hiding place for a systemic failure. The right design is resilience + visibility: swallow the exception for availability, but make the failure impossible to miss via metrics and alerts.

3. **Monitors pointed at dead infrastructure.** The Better Stack monitors were still configured for Render URLs that had been decommissioned weeks earlier. Infrastructure migration checklists should include "repoint all external monitors" as a gate.

4. **Migration never tested against production schema.** The migration was authored and CI-tested against a local database with different column constraints, types, and triggers than production. Four distinct schema mismatches were discovered only during production deploy attempts. A pre-merge dry-run against a Neon branch clone of production would have caught all four.

5. **Incident took 4 fix iterations.** Each iteration required a merge → deploy → wait for CI → check logs cycle (~15 min each). The fixes were individually small (one-liners), but the iteration cost was high because we could only test the migration against the real production schema during an actual deploy. A staging environment with a production-schema clone would have collapsed the 4 iterations into 1.

---

## Appendix

### Sentry event

- Event ID: `042beeeb81ab41c1acd6f8487984d369`
- First seen: 2026-04-16 20:48:20 MDT
- Error: `ProgrammingError: (psycopg2.errors.UndefinedColumn) column "org_id" of relation "audit_log" does not exist`
- URL: `http://api.ai-identity.co/api/v1/agents`
- Method: POST

### Database state at detection

```
alembic_version:    n5j6k7l8m9n0 (3 migrations behind HEAD)
audit_log rows:     138 (last entry: 2026-04-13 18:19:11 UTC)
audit_log.org_id:   column did not exist
audit_log.correlation_id: column did not exist
audit_log_outbox:   table existed (0 rows, orphan from partial prior apply)
audit_log_sinks:    table existed (0 rows, orphan from partial prior apply)
```

### Database state after remediation

```
alembic_version:    q8n9o0p1q2r3 (at HEAD)
audit_log rows:     145 (7 new entries from QA run)
audit_log.org_id:   UUID, NOT NULL, FK → organizations, indexed
audit_log.correlation_id: VARCHAR, nullable, indexed
audit_log_outbox:   table exists (0 rows, properly tracked by alembic)
audit_log_sinks:    table exists (0 rows, properly tracked by alembic)
audit_log triggers: audit_log_no_update (BEFORE UPDATE), audit_log_no_delete (BEFORE DELETE) — both re-enabled
```

### Neon safety artifacts

- Snapshot branch: `incident-audit-infra-2026-04-16` (ID `br-silent-scene-adrhmpjm`)
- Project: `steep-surf-83629306` (AI Identity)
- Created: 2026-04-16 ~21:00 UTC (before any remediation)
- Safe to delete: 2026-04-23 (7 days post-incident)
