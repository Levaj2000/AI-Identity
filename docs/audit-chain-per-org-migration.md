# Per-Org Audit Chain Migration — Scoping Doc

**Author:** CTO (drafted by Claude) · **Status:** CEO-approved 2026-05-13 · **Date:** 2026-05-13

## TL;DR

The audit log today maintains a single platform-global HMAC chain: every row's `prev_hash` points to whatever row was inserted just before it, regardless of which tenant wrote it. That worked while we were effectively single-tenant, but it leaks cross-tenant cardinality through `/api/v1/audit/verify`, makes Client A's integrity proof dependent on Client B's rows being intact, and blocks the customer-facing offline CLI verifier from proving "no rows were deleted from my history." HMAC *key* isolation is already in place (each org signs with its own `forensic_verify_key`), so no tenant can forge another's row — this migration is about chain *linkage*, not signing keys. **Recommendation:** add `prev_hash_org` + `org_chain_seq` columns, dual-write during transition, backfill historical rows in `(org_id, id ASC)` order, then cut verifier reads over to per-org chains and retain the global chain as an internal-only forensic artifact. Estimated effort: **~10–14 engineer-days** over 4 phases, deployable behind a feature flag with no customer-visible downtime. CEO has approved the plan; global chain is retained as an internal-only forensic tool, Phase 4 soak compressed to 5–7 days given no live customer data.

---

## Current State (Code-Verified)

- [common/audit/writer.py:117-131](common/audit/writer.py:117-131) — `_get_last_hash` walks `AuditLog` ordered by `id DESC`, with `SELECT … FOR UPDATE` on PostgreSQL. No `org_id` filter. Every write serializes against every other write platform-wide.
- [common/audit/writer.py:296-310](common/audit/writer.py:296-310) — Each entry signs with the writing org's `forensic_verify_key` (falling back to the global key for legacy rows). Per-row signing keys are already tenant-isolated.
- [common/audit/writer.py:451-481](common/audit/writer.py:451-481) — `verify_chain` walks `db.query(AuditLog).order_by(AuditLog.id.asc())` with no tenant filter; the optional `agent_id` filter scopes recomputation but the comment at line 520-521 explicitly notes "Check prev_hash linkage (global chain only, not per-agent filter)" — per-agent mode *skips* linkage entirely.
- [common/models/audit_log.py:38-42](common/models/audit_log.py:38-42) — `org_id` is `NOT NULL`, denormalized at write time (since migration `o6l7m8n9o0p1`), and indexed via `ix_audit_log_org_created`. The data we need to partition the chain is already on every row.
- **Callers of `verify_chain`:** 4 in `api/app/routers/audit.py` (lines 603, 675, 868, 982 — reconstruct, report, bundle, /verify), 1 in `api/app/compliance_engine.py:200`, and 3 compliance builders (`soc2.py:600`, `nist_ai_rmf.py:473`, `eu_ai_act.py:321`). The dashboard hits these via [forensics.ts:113](dashboard/src/services/api/forensics.ts:113) `verifyAuditChain()`, used from `ForensicsPage.tsx:231`, `CompliancePage.tsx:149`, `TryDemoButton.tsx:78`.
- **Offline CLI verifier:** [cli/ai_identity_verify.py:342-380](cli/ai_identity_verify.py:342-380) — `_cmd_chain_full` replays `prev_hash = GENESIS → entry.entry_hash → …` over the entries in the exported report. The exported reports are already agent-scoped, so the CLI today *only* verifies hash integrity, not chain completeness — same gap as the server's per-agent path.

## Why This Matters

1. **Information leak.** Any authenticated user calling `/api/v1/audit/verify` (no `agent_id`) gets `total_entries` and `entries_verified` for the entire platform. That's a count of competitor activity disclosed to every customer.
2. **Entangled integrity.** A bad row written by Tenant B (or, worse, a row deleted from B's history by an attacker who breaks into B's tenancy) makes Tenant A's `valid=False`. We cannot honestly tell Customer A "your chain is intact" without speaking to every other customer's chain.
3. **No per-tenant completeness proof.** Customers asking "prove no rows were deleted from *my* history" cannot be answered without verifying the *entire platform's* chain. The CLI verifier was designed to be the offline answer to this question and it can't deliver in a multi-tenant world.
4. **Global SELECT … FOR UPDATE bottleneck.** Every audit write serializes on the last row of the whole table — fine at our current volume, but at Cisco-scale (>100 agents × multiple orgs) this becomes a write-throughput ceiling. Per-org locking shrinks the lock domain by N tenants.

HMAC *key* isolation (the part that prevents forgery) is already correct and is **not** in scope. We are not re-litigating signing keys.

---

## Recommended Approach

**Add per-org chain columns alongside the existing global chain, dual-write through a transition period, then cut readers over.** Specifically:

| Column | Type | Purpose |
|---|---|---|
| `prev_hash_org` | `String(64) NOT NULL` | HMAC of the previous row written by *this* org. `GENESIS` for an org's first row. |
| `org_chain_seq` | `BigInteger NOT NULL` | Monotonically increasing sequence within `org_id`, 1-based. Lets the verifier prove "no gaps in my chain" independent of the global `id` sequence. |

Also store a new `entry_hash_org` (HMAC computed over the canonical payload with `prev_hash_org` substituted) so the per-org chain is end-to-end verifiable without recomputing against `prev_hash`. The original `entry_hash` and `prev_hash` columns stay populated for the global chain we keep for internal forensics (see "Open Questions").

### Why this shape, not the alternatives

- **Why not replace the global chain entirely?** Cleaner end-state, but the migration becomes irreversible from the moment we drop `prev_hash`. Keeping both during transition lets us roll back without data loss and gives us a Phase-4 decision point (drop global vs. keep it) once we have operational confidence.
- **Why a sequence number, not just `prev_hash_org`?** With only `prev_hash_org`, the verifier can prove "what's here is internally consistent" but not "all entries 1..N are here." A sequence number turns deletion into a *detectable* gap rather than an undetectable truncation from the tail. SOC 2 auditors care about this; the offline CLI verifier needs it to answer the completeness question.
- **Why not partition the table by `org_id`?** Tempting, but the operational cost (per-org Alembic, per-org backup/restore, per-org index management) is high and the integrity guarantee is the same. Partitioning is a separate decision driven by query performance, not by chain isolation.

### What about the global chain?

Keep computing and storing `prev_hash` / `entry_hash` indefinitely. It costs ~64 bytes per row and gives us:
- An internal forensic view ("show me everything that happened across the platform between 03:14 and 03:16") that no per-org chain can reconstruct.
- A safety net during the migration: if the per-org logic has a bug, we still have the old chain to fall back on.

If we want to retire it later, that's a one-line change in the writer plus a column drop. Decision can wait.

---

## Phased Plan

### Phase 1 — Schema + dual-write (3–4 days)

1. Alembic migration: add nullable `prev_hash_org`, `entry_hash_org`, `org_chain_seq`. Add a `UNIQUE(org_id, org_chain_seq)` index — this is our completeness guard.
2. Update `create_audit_entry` to:
   - Acquire a **per-org PostgreSQL advisory lock** keyed on `hashtext(org_id::text)` instead of the global row-level `FOR UPDATE`. Two orgs writing concurrently never block each other.
   - Read the org's last row (`SELECT entry_hash_org, org_chain_seq FROM audit_log WHERE org_id = $1 ORDER BY org_chain_seq DESC LIMIT 1 FOR UPDATE`), compute `prev_hash_org` and the next sequence number.
   - Continue writing `prev_hash` / `entry_hash` against the global chain (still under the existing global lock, or migrated to a separate global advisory lock — see Risks).
3. Ship behind feature flag `AUDIT_DUAL_WRITE_ENABLED`. Default off in prod, on in CI and staging.

### Phase 2 — Backfill (2–3 days)

1. Idempotent backfill script that walks rows in `(org_id ASC, id ASC)` and fills in `prev_hash_org`, `entry_hash_org`, `org_chain_seq`. Runs in batches of 1k, can resume on failure.
2. Disable the `audit_log_no_update` trigger only for the backfill (precedent: [k2g3h4i5j6k7_add_agent_name_to_audit_log.py:29](alembic/versions/k2g3h4i5j6k7_add_agent_name_to_audit_log.py:29)), re-enable on completion. The recently-added hourly health check ([commit 43c4d5c5](https://github.com/)) means a mistakenly-left-disabled trigger gets paged on within an hour.
3. After backfill, add a one-shot validation pass that recomputes `entry_hash_org` for every row and confirms it matches. Output goes to ops dashboard.
4. Alter columns to `NOT NULL` once backfill is verified.

### Phase 3 — Verifier + API cutover (4–5 days)

1. New `verify_chain(db, *, org_id, agent_id=None)` signature. `org_id` becomes the primary partition; `agent_id` filters within the org (still without linkage, since per-agent chains aren't a thing). Old call sites in `soc2.py`, `nist_ai_rmf.py`, `eu_ai_act.py`, `compliance_engine.py` are updated to pass `org_id`.
2. `/api/v1/audit/verify` (the public endpoint) becomes org-scoped: caller's `user.org_id` is used by default. Platform admins may pass `?org_id=…` to scope to another org. **No-org-context global verification is removed from this endpoint** — moved to a new admin-only `/api/v1/audit/verify/global` that returns 403 for non-platform-admins. This closes the cross-tenant cardinality leak.
3. Offline CLI verifier (`cli/ai_identity_verify.py`) gets a new flag `--per-org` (default true). Exported reports include `org_chain_seq` per event so the verifier checks 1..N continuity, not just hash linkage.
4. Forensics report bundle (`/api/v1/audit/report/bundle`) updated to emit per-org chain metadata and continuity proof.

### Phase 4 — Stabilization (1–2 days)

1. Run dual chains in parallel for a **5–7 day soak** (compressed from the original 30-day proposal — see CEO decision below). Watch ops dashboard for divergence between the two chain verifiers; with only test data, any drift surfaces on the first sample query.
2. **Global chain is retained indefinitely as an internal-only forensic tool** (CEO decision). No column drops, no writer changes. Once the soak passes, the migration is done.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Backfill computes a different `entry_hash_org` than the writer for fresh rows (canonical-form drift). | Phase 1 lands a new `compute_entry_hash_org()` helper used by *both* writer and backfill. Single source of truth, contract-tested. |
| Dropping the global `FOR UPDATE` for per-org locking races against concurrent writers from the same org. | PostgreSQL advisory locks (`pg_advisory_xact_lock(hashtext(org_id::text))`) are well-tested and release on commit. The unique index on `(org_id, org_chain_seq)` is the belt-and-suspenders guarantee: even if locking is wrong, duplicate sequence numbers fail the insert. |
| Customer's existing exported reports (signed under old chain semantics) become unverifiable post-cutover. | The signing key for `report_signature` doesn't change. Pre-migration reports continue to verify with the existing CLI. The `--per-org` flag is a *new* feature for *new* reports; we don't break old ones. |
| Backfill discovers an existing global chain break in production data. | Backfill is *forward-only* — it writes per-org chains computed from current row content, not by replaying the global chain. A pre-existing global break does not block backfill. We log it and address separately. |
| Compliance builders (SOC 2 / NIST / EU AI Act) reference the global chain in their narrative. | Phase 3 updates the builders to render per-org chain results for customer-bound reports. Internal exports can opt into the global view. |
| The system org sentinel ([writer.py:134-178](common/audit/writer.py:134-178)) accumulates orphan rows from every tenant — its per-org chain becomes a noisy catch-all. | Acceptable. The system org is platform-admin-only; mixing orphans there is the correct partition (they have no real tenant). |

---

## Test Coverage Changes

Existing tests to update:

- **[api/tests/test_audit.py:154](api/tests/test_audit.py:154)** — `test_verify_chain_with_agent_id` asserts the per-agent path skips linkage. Replace with assertions that per-org verification *does* enforce linkage and per-agent within an org enforces hash recomputation only.
- **[api/tests/test_audit.py:94-142](api/tests/test_audit.py:94-142)** — full-chain verify tests need an `org_id` parameter and should be parameterized over (single-org / multi-org / cross-org tampering) scenarios.
- **[api/tests/test_audit_org_scoping.py:132](api/tests/test_audit_org_scoping.py:132)** — likely the most affected test file. Expand to cover: org A's chain is intact when org B's chain is broken, deleting a row from org A's middle is detected via sequence gap, deleting a row from org A's tail is detected via the next-row `prev_hash_org` mismatch.
- **[api/tests/test_isolation.py](api/tests/test_isolation.py)** — add a test that `/api/v1/audit/verify` from org A returns no information about org B's row count.
- **[api/tests/test_audit_metadata_v1.py:237](api/tests/test_audit_metadata_v1.py:237)** — verify the v1 metadata schema doesn't accidentally include chain fields that would break verification across releases.

New tests to add:

- **Concurrent writer test (single org)** — spawn N goroutines/threads writing simultaneously from agents in the same org, assert `org_chain_seq` is monotonic with no gaps and no duplicates.
- **Concurrent writer test (cross-org)** — assert two orgs writing in parallel don't block each other (timing-sensitive, but worth a soft assertion).
- **Backfill replay test** — load a fixture of N rows across M orgs, run backfill, then run per-org verify; assert all chains valid.
- **CLI verifier (per-org)** — given an exported report with `org_chain_seq`, the CLI detects a deleted middle row and reports the gap with the offending sequence number.

---

## Effort Estimate

| Phase | Engineer-Days | Notes |
|---|---|---|
| 1 — Schema + dual-write | 3–4 | Includes Alembic migration, writer changes, advisory-lock plumbing, feature flag, unit tests. |
| 2 — Backfill | 2–3 | Script + idempotency + validation pass. Most risk is in compute-parity with writer. No live-traffic coordination needed (CEO confirmed no live customers — run anytime). |
| 3 — Verifier + API cutover | 4–5 | Touches 8 call sites of `verify_chain`, the public endpoint contract, the CLI verifier, and dashboard wiring. |
| 4 — Stabilization | 1–2 | 5–7 day soak (calendar) + dashboard verification. Compressed from original plan per CEO decision. |
| **Total** | **10–14 days** | Single engineer, mostly contiguous. Could compress with paired work in Phase 3. |

---

## Decisions (CEO, 2026-05-13)

1. **Global chain: KEEP indefinitely as internal-only forensic tool.** No customer-facing endpoint exposes its result. Phase 4 does *not* drop `prev_hash` / `entry_hash`.

2. **`/api/v1/audit/verify` with no `org_id`: defaults to caller's org.** Non-admins implicitly scoped to their own org. Platform admins may pass `?org_id=` to scope elsewhere; non-admins passing a foreign `?org_id=` get 403.

3. **Phase 4 soak: 5–7 days, not 30.** No live customer data on the system today, so divergence between dual chains surfaces immediately under test traffic. If we need polished demo material, export representative samples *before* cutover so we have a clean reference set.

4. **Backfill window: run anytime.** No live customers, no coordination required. Treat as a routine deploy.

5. **SOC 2 auditor notification: skipped for now.** No customer data on the chain today and no active auditor engagement — re-evaluate as a one-line CHANGES note in the SOC 2 control narrative once a real audit engagement is on the calendar.

## Remaining Open Items

None blocking. Greenlight pending sign-off.
