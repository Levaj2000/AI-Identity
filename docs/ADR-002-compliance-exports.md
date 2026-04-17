# ADR-002: Compliance export API + bundle architecture

**Status:** Accepted — sprint 10 item #273. Implementation in a follow-on sprint.
**Date:** 2026-04-17
**Deciders:** Jeff Leva (CEO/CTO)
**Feeds:** Milestone #34 (compliance export profiles, due 2026-06-20).
**Consumes:** [`compliance/export-profiles.md`](compliance/export-profiles.md) (#272 scoping).

## Context

#272 locked what goes *into* an export (artifact lists, retention, per-framework mapping). This ADR locks **how** customers request one and **how it comes back**:

- Synchronous vs async response model
- Container format + integrity model
- Tenancy + authorization
- Persistence model
- Size / cost guardrails

An API stub ships with this ADR (returns `501 Not Implemented` with the real response shape) so downstream consumers — the dashboard, the CLI, any early-access customer — can write against a stable contract while the actual export builder is implemented in a later sprint.

## Decision summary

1. **Async, job-based API.** `POST /api/v1/exports` creates a job and returns immediately with an export id. `GET /api/v1/exports/{id}` polls; once `status == "ready"`, a signed download URL appears.
2. **ZIP archive + DSSE-signed manifest** using the same KMS ECDSA-P256 key as the forensic signer from Milestone #33. One signing root for *all* evidence AI Identity produces.
3. **Org-scoped, admin-only.** Same authZ surface as the attestation sign endpoint (#263). Cross-org exports are not permitted.
4. **Persist metadata, not archives.** The `compliance_exports` table holds the job record + manifest envelope + signed URL. The archive itself lives in object storage with a TTL; we can always re-export on demand from the source-of-truth tables.
5. **Hard size cap** to protect the worker tier and customer patience — see Cost guardrails below.

Stub scope: endpoints + schemas + OpenAPI + a 501 response on POST. No build logic, no table migration, no worker. That's the next sprint.

## Considered alternatives

### Synchronous export (rejected)

We briefly considered synchronous build-on-request. Rejected for three reasons:

- A 12-month SOC 2 access-log export for a large tenant can reasonably be hundreds of MB. HTTP timeouts will be hit.
- The gateway's 500 ms policy eval budget doesn't apply here, but the API's Cloud Run request timeout does.
- Large archives don't want to live in process memory — streaming them directly would couple the API to object storage in a way that complicates auth.

Async with polling is the industry-standard shape for this class of endpoint (AWS S3 inventory exports, GCS bucket inventory, Stripe bulk exports, Salesforce bulk API — all async).

### Streaming CSV response (rejected)

Streaming a single CSV has the right performance profile but loses:

- Multi-file bundles (we need ZIP with ≥ 6 artifacts per profile)
- Per-artifact integrity (DSSE manifest commits to each file's hash)
- Idempotency (client-side retries on partial download are ugly)

Reserving streaming for a possible future "live tail" log-forwarding API, not for audit-grade evidence.

### Embed archive bytes in the JSON response (rejected)

Base64-encoding the archive in the GET response would remove the object-storage dependency, but multi-hundred-MB base64 payloads break every intermediate proxy/CDN and make the API look like an abuse vector. Object storage with a signed URL is the right tool.

### Pre-signed bucket URL at `POST` time (rejected)

Returning a pre-signed URL immediately on POST would let the client "pull" during build — but the URL would be valid before the archive exists, and the semantics of "GET this file, maybe it's there" are hostile to clients. Explicit polling loop wins.

## API shape

Base path: `/api/v1/exports`. Tag: `compliance.exports`.

### `POST /api/v1/exports`

Create an export job.

**Request body:**

```json
{
  "profile": "soc2_tsc_2017",
  "audit_period_start": "2025-04-17T00:00:00Z",
  "audit_period_end": "2026-04-17T00:00:00Z",
  "agent_ids": null
}
```

Field rules:

- `profile` — required, one of `"soc2_tsc_2017"`, `"eu_ai_act_2024"`, `"nist_ai_rmf_1_0"`. Enum enforced at schema level so a typo fails fast rather than after a 10-minute build.
- `audit_period_start` / `audit_period_end` — required, both UTC with `Z` suffix (we reject naive datetimes). `end > start`. Max period: 18 months (covers a 12-month SOC 2 window + reasonable buffer).
- `agent_ids` — optional list of UUIDs for targeted sampling-plan exports. Null / absent → whole org. Each id must belong to the caller's org; cross-org ids are rejected at 400 before any build.
- `org_id` is **not** in the body — it's resolved from the caller's identity + admin check, not self-declared. Preserves the "caller cannot attest/export across orgs" invariant from #263.

**Responses:**

- `202 Accepted` — job created, build queued. Body is the full `ExportResponse` with `status: "queued"`.
- `400 Bad Request` — validation failure (bad profile, bad date range, period > 18 months, cross-org agent id, past retention horizon).
- `403 Forbidden` — caller is not an org admin.
- `409 Conflict` — an export for the same (profile, audit_period, agent_ids) is already in-flight for this org. Idempotency guardrail; return the existing job id.
- `429 Too Many Requests` — rate limit: max 5 concurrent builds per org, 20 exports per org per 24 hours.
- `501 Not Implemented` — **stub response until the builder lands.** Response body includes a stable `error.code == "export_builder_not_implemented"` and the shape below. Stub lets clients write against the contract now.

### `GET /api/v1/exports/{id}`

Poll or retrieve a job.

**Responses:**

- `200 OK` — body is `ExportResponse` with current status:
  - `status: "queued"` — accepted, not yet picked up by a worker
  - `status: "building"` — worker in progress, `progress_pct` populated if known
  - `status: "ready"` — `archive_url` (signed, 1-hour TTL), `archive_sha256`, `manifest_envelope` populated
  - `status: "failed"` — `error.code` + `error.message` populated
- `403 Forbidden` — id exists but belongs to a different org.
- `404 Not Found` — no such id (or belongs to a different org — we return 404 not 403 to avoid leaking tenancy, same discipline as #264).

### `GET /api/v1/exports`

List the caller's org's exports, newest first.

- Query params: `profile`, `status`, `limit` (default 20, max 100), `before` (cursor).
- Response: `{"items": [ExportResponse, ...], "next_cursor": str | null}`.

## Response schema (`ExportResponse`)

```json
{
  "id": "3f2c1b0a-4e6d-4e2a-9f1a-3c2b0d4e8f7a",
  "org_id": "f1e2d3c4-b5a6-4798-8877-66554433abcd",
  "requested_by": "a1b2c3d4-...",
  "profile": "soc2_tsc_2017",
  "audit_period_start": "2025-04-17T00:00:00Z",
  "audit_period_end": "2026-04-17T00:00:00Z",
  "agent_ids": null,
  "status": "ready",
  "progress_pct": 100,
  "archive_url": "https://storage.googleapis.com/...signed...",
  "archive_url_expires_at": "2026-04-17T14:00:00Z",
  "archive_sha256": "3b7e0a6f...",
  "archive_bytes": 24580192,
  "manifest_envelope": { "payloadType": "...", "payload": "...", "signatures": [...] },
  "created_at": "2026-04-17T13:00:00Z",
  "completed_at": "2026-04-17T13:06:14Z",
  "error": null
}
```

Fields populated conditionally by status — see API shape above. `manifest_envelope` is a full DSSE envelope whose payload commits to each artifact's SHA-256.

## Bundle structure

ZIP archive. Top level:

```
export-<id>.zip
├── manifest.json                    # signed over; see below
├── attestations/
│   ├── <session_id>.dsse.json       # one file per attestation in the period
│   └── ...
├── access_log.csv                   # audit_log rows
├── change_log.csv                   # agent/policy/key lifecycle events
├── control_results.csv              # compliance check results for the period
├── chain_integrity.json             # verify_chain() result at export time
├── policy_snapshots/                # SOC 2 recommended; optional per profile
│   └── <timestamp>.json
├── agent_inventory.csv              # SOC 2 recommended + EU AI Act + NIST core
└── README.md                        # human-readable summary + verify instructions
```

Per-profile artifacts layer on top of this core: `human_oversight_log.csv` for EU AI Act, `manage_approvals.csv` / `manage_revocations.csv` for NIST, etc. See #272 for the full per-profile artifact list.

### `manifest.json` (canonical payload)

```json
{
  "schema_version": 1,
  "export_id": "<uuid>",
  "org_id": "<uuid>",
  "profile": "soc2_tsc_2017",
  "audit_period_start": "2025-04-17T00:00:00Z",
  "audit_period_end": "2026-04-17T00:00:00Z",
  "built_at": "2026-04-17T13:06:14Z",
  "signer_key_id": "projects/.../cryptoKeyVersions/1",
  "artifacts": [
    { "path": "access_log.csv",         "sha256": "...", "bytes": 1024768,  "controls": ["SOC2-CC6.1","SOC2-CC7.2"] },
    { "path": "attestations/...json",   "sha256": "...", "bytes": 982,      "controls": ["SOC2-CC7.2"] },
    { "path": "chain_integrity.json",   "sha256": "...", "bytes": 412,      "controls": ["SOC2-CC7.2"] },
    ...
  ]
}
```

Delivered as a DSSE envelope:

```json
{
  "payloadType": "application/vnd.ai-identity.export-manifest+json",
  "payload": "<base64(canonical-json-of-manifest)>",
  "signatures": [
    { "keyid": "<key-version-path>", "sig": "<base64(DER ECDSA-P256-SHA256)>" }
  ]
}
```

**Why a new payloadType and not the attestation MIME type?** An attestation commits to an audit chain tail; an export manifest commits to a multi-file archive. Conflating them would let an attestation verify against a manifest and vice versa — domain separation is cheap and the right call.

**Canonicalization:** JCS (RFC 8785), matching the attestation format (`../forensics/attestation-format.md`). Same rationale, same implementation, probably same helper.

## Verification

An auditor receiving `export-<id>.zip` runs:

1. Extract the archive.
2. Read `manifest.json` (inside the DSSE envelope — payload is base64-encoded canonical JSON).
3. Fetch the public key from AI Identity's JWKS (`/.well-known/ai-identity-public-keys.json`) using `signer_key_id`.
4. Verify the DSSE signature over the manifest.
5. For each `artifacts[i]`, compute SHA-256 of the extracted file and compare to the manifest entry.

On any mismatch → reject the whole export. This is binary, offline, and doesn't require contacting AI Identity.

`cli/ai_identity_verify.py` gets a new `export` subcommand in the implementation sprint — not in scope for this ADR.

## Data model

New table `compliance_exports`. Matches the sketch in the #272 scoping doc:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID pk | returned to client |
| `org_id` | UUID FK organizations | always org-scoped |
| `requested_by` | UUID FK users | for audit purposes |
| `profile` | String(40) | enum enforced at app layer |
| `audit_period_start` | DateTime tz | |
| `audit_period_end` | DateTime tz | |
| `agent_ids` | UUID[] nullable | null = whole org |
| `status` | String(16) | enum: `queued`/`building`/`ready`/`failed` |
| `progress_pct` | Integer nullable | 0-100 or null |
| `archive_url` | String(2048) nullable | signed GCS URL, TTL 1 hour |
| `archive_url_expires_at` | DateTime tz nullable | so client can re-request without hitting a 403 |
| `archive_sha256` | String(64) nullable | hex |
| `archive_bytes` | BigInteger nullable | for the cost-guard trigger |
| `manifest_envelope` | JSONB nullable | the DSSE envelope, same shape as `forensic_attestations.envelope` |
| `error_code` | String(64) nullable | e.g. `"period_too_long"`, `"storage_write_failed"` |
| `error_message` | Text nullable | human-readable |
| `created_at` | DateTime tz | default now() |
| `completed_at` | DateTime tz nullable | set on terminal state (`ready` or `failed`) |

Indexes: `(org_id, created_at DESC)` for list; `(org_id, status)` for worker polling.

**Unique constraint:** `(org_id, profile, audit_period_start, audit_period_end, agent_ids_hash)` where `agent_ids_hash` is a deterministic hash of the sorted ids list (or `NULL` for whole-org). Drives the 409 idempotency behavior. Implementation note: Postgres won't let you unique-index an `ARRAY` directly in a way that treats `[a,b]` and `[b,a]` as equal — we compute the hash at write time.

**Migration defers to implementation sprint.** The stub never reads or writes this table.

## Build pipeline (sketch, not in stub scope)

```
POST /exports
      │
      ▼
  validate + insert queued row ──┐
      │                          │
      ▼                          ▼
 return 202                 (worker picks up)
                                 │
                                 ▼
                            build artifacts
                          (streams from DB →
                           CSV/JSON files in
                           a temp dir)
                                 │
                                 ▼
                       compute SHA-256 per file
                                 │
                                 ▼
                           build manifest.json
                                 │
                                 ▼
                     DSSE-sign manifest via KMS
                                 │
                                 ▼
                       zip everything, upload GCS
                                 │
                                 ▼
                   update row → status=ready,
                   archive_url, archive_sha256,
                   manifest_envelope
```

- **Worker:** Cloud Run job triggered via Pub/Sub, or a dedicated container. Decision deferred to implementation sprint; the API stub is worker-agnostic.
- **Streaming:** artifacts are built streaming from DB to file — a 12-month access log is non-trivial memory otherwise.
- **Timeouts:** single build capped at 30 minutes. Beyond that, status transitions to `failed` with `error_code == "build_timeout"`.

## AuthZ

- **Caller must be an org owner or admin** (same predicate as `_assert_org_admin` in `api/app/routers/attestations.py`).
- **Platform admins** (`user.role == "admin"`) can export any org's data. Same treatment as the retrieval API (#264). Used sparingly — ops flows, customer-support assists.
- **Cross-org protection on agent_ids:** every agent id in the request is verified to belong to the caller's org before the job is queued. Mixed-tenant requests are rejected at 400 with a precise message, matching the attestation sign endpoint's treatment.

## Cost guardrails

Export builds consume worker CPU and object-storage egress; a naive implementation is abuse-vector-friendly. Defaults:

- **Max 5 concurrent builds per org** — additional requests get 429 with `Retry-After`.
- **Max 20 exports per org per 24 hours** — same 429 path.
- **Max audit period: 18 months** — validation error at POST.
- **Archive size cap: 10 GB** — if a build exceeds this (huge tenant, maxed period), the worker fails the job with `error_code == "archive_too_large"` and points the user at the `agent_ids` parameter for sampling-plan narrowing.
- **Signed URL TTL: 1 hour** — matches GCS defaults; re-requesting a completed export mints a fresh URL (no rebuild).
- **Archive retention: 30 days** — after which `archive_url` 404s and clients must re-request a build. The underlying source data retention (audit log, attestations) is the long-term contract; archives are a convenience.

These are defaults — enterprise tier raises them. Values are settings, not hardcoded, so per-customer overrides don't need code changes.

## Observability

Prometheus metrics added in the implementation sprint; named now so downstream work has stable identifiers:

- `ai_identity_compliance_export_builds_total{profile, outcome}` — counter
- `ai_identity_compliance_export_build_duration_seconds{profile}` — histogram
- `ai_identity_compliance_export_archive_bytes{profile}` — histogram
- `ai_identity_compliance_export_queue_depth{org_tier}` — gauge (worker-reported)

Sentry: any `error_code` starting with `infrastructure_` pages the on-call (storage write failures, KMS sign failures). `user_error`-class codes do not page.

## Open items (deferred, not blocking this ADR)

- **Archive format for very small exports.** Single-artifact exports (e.g. a manifest-only "no activity in period" result) still ship as ZIP for consistency. Could optimize later; not in v1.
- **Export differencing.** "Give me what changed since export X" would be valuable for quarterly refreshes. Post-v1.
- **Customer-uploaded artifacts** (impact-assessment PDFs for NIST MP-5.1, vendor SOC 2 reports). Flagged as a future feature; the manifest schema has `artifacts[].source` anticipating this — values `"generated"` | `"customer_upload"`.
- **ISO 42001 / UK AI framework profiles.** Adding a profile is additive — enum value + per-profile artifact set in the builder, no schema change. Follow design-partner demand.

## Acceptance

- [x] ADR written, decisions justified against alternatives
- [x] API shape locked (POST + GET by id + list)
- [x] Response schema documented with every field's shape
- [x] Bundle + manifest format locked (new `payloadType`, JCS, DSSE)
- [x] AuthZ model matches existing admin-only patterns (#263/#264)
- [x] Tenancy invariants restated (no cross-org, agent_ids verified)
- [x] Cost guardrails quantified
- [x] API stub ships: endpoints return 501 with the correct response shape, visible in OpenAPI

Full implementation (builder, migration, worker, `compliance_exports` table, tests) is a follow-on sprint item.

## References

- #272 scoping: [`compliance/export-profiles.md`](compliance/export-profiles.md)
- #33 trust model: [`forensics/trust-model.md`](forensics/trust-model.md)
- #33 signed format: [`forensics/attestation-format.md`](forensics/attestation-format.md)
- Existing admin-only pattern: `api/app/routers/attestations.py` (`_assert_org_admin`)
- Existing 404-not-403 pattern: `api/app/routers/attestations.py::get_attestation_by_session`
