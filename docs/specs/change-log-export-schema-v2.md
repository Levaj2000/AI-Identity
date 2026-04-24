# Change Log Export Schema v2

| Field              | Value                                                       |
|--------------------|-------------------------------------------------------------|
| **Status**         | Draft                                                       |
| **Priority**       | P0 — ships before any prospect/auditor sample is shared     |
| **Author**         | AI Identity Engineering                                     |
| **Created**        | 2026-04-24                                                  |
| **Target Release** | v0.9.0                                                      |
| **Depends On**     | Audit log HMAC chain, Ed25519 forensic signer, v1 export    |
| **Supersedes**     | Current `change_log.csv` shape in [export-profiles.md](../compliance/export-profiles.md#required-artifacts-v1-export) |
| **Stakeholders**   | Platform Engineering, Compliance, Sales, CTO                |

---

## Why v2

A sample `change_log` export reviewed on 2026-04-24 shipped nine columns
(`audit_log_id`, `created_at`, `action_type`, `resource_type`, `agent_id`,
`agent_name`, `actor_user_id`, `decision`, `details_json`). That shape
satisfies the current SOC 2 builder contract, but fails three readings:

1. **Positioning.** AI Identity's differentiation is the HMAC-SHA256
   hash chain on every audit_log row plus ECDSA-P256-SHA256 forensic
   signatures on each export artifact. The change_log export exposes
   none of that today. A buyer comparing our export to a log-based
   competitor's export cannot distinguish them on the wire.
2. **Compliance readability.** Auditors scan spreadsheets left-to-right.
   UUID-only actor identity and raw JSON in `details_json` force them
   into the payload for basic questions.
3. **Investigative completeness.** Source context (`ip_address`,
   `request_id`, `session_id`) is standard for SOC 2 CC7.2 and HIPAA
   §164.312(b) audit logs. Before/after diff on `agent_updated` is
   table-stakes for change management evidence.

v2 adds cryptographic columns, source context, flattened high-signal
fields, denial semantics, and a diff field for update events. It does
not remove any v1 column — existing integrations stay valid.

## Goals / non-goals

**Goals**
- Every exported row carries the cryptographic proof needed to verify
  it independently of AI Identity's systems.
- An auditor can answer "who did what, when, from where, and what
  changed" from the CSV alone — without opening `details_json`.
- Denials are represented with machine-readable reason codes.
- The schema is stable enough to publish as a reference spec for
  prospects and auditors.

**Non-goals**
- Not redesigning `access_log.csv` (separate spec — that artifact
  already carries `entry_hash` / `prev_hash`).
- Not adding new lifecycle event types. v2 is a schema change over the
  existing event set (`agent_created`, `agent_updated`, `agent_revoked`,
  `key_rotated`, plus denial variants).
- Not changing retention defaults (13 months for audit_log rows).

## v2 column set

Columns are grouped by concern. All columns are **required** in v2
unless flagged *(optional)*. Empty values are the empty string, not
`null`, per RFC 4180.

### Identity + timing (unchanged from v1)

| Column           | Type        | Notes |
|------------------|-------------|-------|
| `audit_log_id`   | int64       | Primary key in `audit_log` table. |
| `created_at`     | ISO 8601 UTC | `YYYY-MM-DDTHH:MM:SSZ`. Second precision — matches `access_log.csv` and the cross-cutting format in [export-profiles.md](../compliance/export-profiles.md#format). |
| `action_type`    | enum        | See action taxonomy below. |
| `resource_type`  | enum        | `agent` \| `api_key` \| `policy` \| `organization`. |
| `agent_id`       | uuid        | Empty for org-scoped actions. |
| `agent_name`     | string      | Display name at time of event. Immutable copy. |

### Actor (expanded)

| Column              | Type   | Notes |
|---------------------|--------|-------|
| `actor_user_id`     | uuid   | DB identifier. Unchanged from v1. |
| `actor_email`       | string | **New.** Email at time of event. Empty for system/automation actors. |
| `actor_principal`   | string | **New.** Human-readable principal: `user:jeff@ai-identity.co`, `service:compliance-cron`, `api_key:aid_sk_Kjmny`. |
| `actor_type`        | enum   | **New.** `user` \| `service` \| `api_key` \| `system`. Distinguishes automation from human action. |

### Decision (expanded)

| Column               | Type   | Notes |
|----------------------|--------|-------|
| `decision`           | enum   | `allowed` \| `denied`. Unchanged from v1. |
| `decision_reason`    | string | **New.** Machine-readable code. Empty when `decision=allowed`. See reason codes below. |
| `policy_version`     | string | **New.** SHA-256 prefix (12 chars) of policy doc active at decision time. Empty when not applicable. |

### Source context (new block)

All fields *(optional)* at row level — populated when the originating
request has them. Server-to-server calls may legitimately have empty
`ip_address`/`user_agent`; console actions must have both.

| Column          | Type   | Notes |
|-----------------|--------|-------|
| `ip_address`    | string | IPv4 or IPv6. Redacted to /24 or /48 if org has `privacy.redact_ip=true`. |
| `user_agent`    | string | Truncated to 256 chars. |
| `session_id`    | uuid   | Dashboard session ID, if applicable. |
| `request_id`    | string | Server-assigned per-request ID. Joins to `access_log`. |
| `correlation_id`| string | Client-supplied trace ID. Joins across services. |

### Change payload (new block, replaces opaque `details_json` for common cases)

`details_json` remains as a catchall. These columns pre-flatten the
high-signal keys so auditors don't open JSON for standard questions.

| Column          | Type   | Applies to | Notes |
|-----------------|--------|------------|-------|
| `key_prefix`    | string | `key_rotated`, `agent_revoked` | e.g., `aid_sk_Kjmny`. First 12 chars after the scheme prefix. |
| `key_type`      | enum   | `key_rotated` | `runtime` \| `bootstrap` \| `admin`. |
| `grace_hours`   | int    | `key_rotated`, `agent_revoked` | Grace window on old credential. `0` for immediate. |
| `old_status`    | string | `agent_revoked`, `agent_updated` | Prior status value. |
| `new_status`    | string | `agent_revoked`, `agent_updated` | New status value. |
| `diff_json`     | JSON   | `agent_updated`, `policy_changed` | **New.** Structured before/after: `{"field": {"before": X, "after": Y}}`. Replaces the weak v1 behavior where `agent_updated` rows had no diff. |
| `details_json`  | JSON   | all        | Catchall for any metadata key not covered above. Pre-flattened keys are removed to avoid duplication. |

### Cryptographic proof (new block — the core v2 change)

Every row carries the proof an auditor needs to verify it against the
existing HMAC chain and the ECDSA-P256-SHA256 forensic signer,
offline, without calling AI Identity.

| Column           | Type     | Notes |
|------------------|----------|-------|
| `entry_hash`     | hex-64   | HMAC-SHA256 chain hash already stored on the audit_log row. Not recomputed at export — exported verbatim so it matches `access_log.csv` and the live DB. |
| `prev_hash`      | hex-64   | `entry_hash` of the preceding audit_log row in the per-org chain. `"GENESIS"` only for the first row ever written to the org. |
| `signature`      | base64   | DER-encoded ECDSA-P256-SHA256 signature from the forensic signer over the signing input (see below). Typically ~96 base64 chars. |
| `signing_key_id` | string   | Forensic signer key identifier at export time. KMS resource path (`projects/.../cryptoKeyVersions/N`) or `local:<sha256>` for dev. Rotates per [`key-rotation.md`](../forensics/key-rotation.md). |
| `chain_segment`  | string   | **Optional.** Merkle root reference if the row's epoch has been sealed. Empty for rows within the current open segment. Reserved — no rows emit this in v2.0. |

### Canonicalization (verification contract)

The signature covers a DSSE-style pre-authentication encoding (PAE) of
the row's canonical JSON form. That keeps the verification path
identical to how manifests and attestations are already verified,
reusing `common.schemas.forensic_attestation.pae`.

The canonical payload for a single row is RFC 8785 JCS of:

```json
{
  "audit_log_id": <int>,
  "created_at": "<RFC 3339 UTC>",
  "action_type": "<string>",
  "resource_type": "<string>",
  "agent_id": "<uuid-or-empty>",
  "actor_user_id": "<uuid-or-empty>",
  "decision": "<allowed|denied>",
  "decision_reason": "<string-or-empty>",
  "policy_version": "<string-or-empty>",
  "entry_hash": "<hex-64>",
  "prev_hash": "<hex-64-or-GENESIS>",
  "diff_json": <object>,
  "details_json": <object>
}
```

Signing input = `PAE("application/vnd.ai-identity.change-log-row+json", canonical_payload_bytes)`.

Display-only and source-context fields (`agent_name`, `actor_email`,
`actor_principal`, `actor_type`, `ip_address`, `user_agent`,
`session_id`, `request_id`, `correlation_id`, plus the flattened
payload columns `key_prefix`, `key_type`, `grace_hours`, `old_status`,
`new_status`) are **not** part of the signature. They can be redacted
or reformatted for export without invalidating signatures — the
signed payload already pins the decision via `entry_hash` and the
canonical fields above.

The `scripts/verify_change_log.py` helper (new) takes the CSV plus
the signer's public key bundle (or the manifest DSSE envelope, which
pins the signer_key_id) and re-verifies every row.

## Action type taxonomy

v2 locks the canonical set. Builders reject unknown `action_type`
values from metadata rather than silently passing them through.

| `action_type`       | `resource_type` | `decision` domain | Emitted by |
|---------------------|-----------------|-------------------|------------|
| `agent_created`     | `agent`         | allowed           | `POST /agents` |
| `agent_updated`     | `agent`         | allowed, denied   | `PATCH /agents/:id` |
| `agent_revoked`     | `agent`         | allowed           | `POST /agents/:id/revoke` |
| `key_created`       | `api_key`       | allowed           | `POST /agents/:id/keys` |
| `key_rotated`       | `api_key`       | allowed           | `POST /agents/:id/keys/rotate` |
| `key_revoked`       | `api_key`       | allowed           | `DELETE /keys/:id` |
| `policy_created`    | `policy`        | allowed           | `POST /orgs/:id/policy` |
| `policy_updated`    | `policy`        | allowed           | `PUT /orgs/:id/policy` |
| `policy_deleted`    | `policy`        | allowed           | `DELETE /orgs/:id/policy` |

The set matches `_LIFECYCLE_ACTIONS` in
[`common/compliance/builders/soc2.py`](../../common/compliance/builders/soc2.py).
Organization membership events are tracked as a v2.1 follow-up.

## Denial reason codes

`decision_reason` uses a dotted namespace. The set is closed per
release; unknown codes fail the builder.

| Code                          | Meaning |
|-------------------------------|---------|
| `policy.tool_not_allowed`     | Tool call outside agent's policy scope. |
| `policy.resource_out_of_scope`| Target resource not in agent's allowed set. |
| `policy.rate_limit`           | Agent exceeded per-policy rate limit. |
| `key.expired`                 | Presented key past expiry. |
| `key.revoked`                 | Presented key is revoked. |
| `key.grace_exceeded`          | Revoked key used past grace window. |
| `key.signature_invalid`       | Client signature did not verify. |
| `actor.not_authorized`        | User/service lacks role for the action. |
| `actor.mfa_required`          | High-sensitivity action without MFA. |
| `target.not_found`            | Resource referenced does not exist. |
| `target.state_conflict`       | Resource in a state incompatible with the action (e.g., revoke-already-revoked). |
| `system.maintenance_mode`     | Org in maintenance — writes frozen. |

## Sample rows

Two rows — one allowed rotation, one denied revoke — in the v2 shape.
Truncated for readability; real values are full-length.

```
audit_log_id,created_at,action_type,resource_type,agent_id,agent_name,
actor_user_id,actor_email,actor_principal,actor_type,
decision,decision_reason,policy_version,
ip_address,user_agent,session_id,request_id,correlation_id,
key_prefix,key_type,grace_hours,old_status,new_status,diff_json,details_json,
entry_hash,prev_hash,signature,signing_key_id,chain_segment

108,2026-04-13T16:00:05.214Z,key_rotated,api_key,3b45c2e2-...,QA-29f384ce,
a33fb1e9-...,jeff@ai-identity.co,user:jeff@ai-identity.co,user,
allowed,,a7f3c91d2e44,
192.0.2.14,Mozilla/5.0 (Macintosh; ...),4c1e...,req_01HWR...,corr_6ab...,
aid_sk_yQjRs,runtime,24,,,{},{},
9f3b...e2a1,4d71...c0ff,MEUCIQD...==,fsk_2026q2_01,

912,2026-04-22T09:14:11.002Z,agent_revoked,agent,712af9e9-...,QA-ffe4347b,
b82a0f11-...,svc-compliance@ai-identity.co,service:compliance-cron,service,
denied,target.state_conflict,a7f3c91d2e44,
,,,req_01HXP...,,
,,,,revoked,{"status":{"before":"revoked","after":"revoked"}},{"attempted_by_job":"weekly-cleanup"},
c1d8...77ef,9f3b...e2a1,MEQCIH...==,fsk_2026q2_01,merkle_2026w16
```

## Builder changes

File: `common/compliance/builders/soc2.py`, function `_write_change_log`
(today at [soc2.py:311](../../common/compliance/builders/soc2.py#L311)).

1. Expand the `rows.append({...})` construction to emit the full v2
   column set. Pull source context from `entry.request_metadata` (the
   audit_log row already captures IP/UA via middleware; today they're
   dropped in this builder).
2. Call the canonicalizer + signer (new helper `common/forensics/
   change_log_signer.py`) per row, using the org's active forensic
   signer key. Today this logic exists for `access_log`; factor it to
   a shared module.
3. Populate `diff_json` from `entry.request_metadata["diff"]` when
   present; request that the API emit `diff` on `agent_updated` and
   `policy_changed` paths (API change tracked separately).
4. Update `fieldnames` list to the v2 column order shown in "Sample
   rows" above. Order is part of the contract — do not reorder without
   a schema version bump.

## Versioning + back-compat

- `manifest.json` gains a `change_log_schema_version: "2.0"` field.
  Auditors parsing v1 exports see `"1.0"` (new manifest field defaults
  to `"1.0"` for pre-v2 exports).
- A v1-compatibility export flag (`?schema=1`) stays available for 90
  days after v2 GA for customers with pinned ingestion.
- No v1 column is removed. v1 consumers reading v2 exports ignore new
  columns per standard CSV consumer behavior.

## Verification tool

`scripts/verify_change_log.py` (new):

```
usage: verify_change_log.py [--pubkey-bundle PATH] CHANGE_LOG_CSV

Exit codes:
  0  every row verifies
  1  one or more rows failed signature verification
  2  chain integrity broken (prev_hash mismatch)
  3  unknown action_type or decision_reason (schema violation)
```

Bundle this with every export so auditors can run verification without
network access to AI Identity.

## Acceptance criteria

1. Every row in a v2 export passes `verify_change_log.py` against the
   bundled public key set.
2. `action_type` and `decision_reason` values are all drawn from the
   closed sets above.
3. For every `agent_updated` row, `diff_json` is non-empty.
4. For every `denied` row, `decision_reason` is non-empty.
5. `change_log_schema_version` field present in `manifest.json`.
6. A prospect-facing sample export, redacted for PII, lives at
   `docs/compliance/samples/change-log-v2-sample.csv` and is linked
   from the landing page trust section.

## Open questions

- **Q1:** Should `ip_address` redaction be per-org (current
  `privacy.redact_ip` flag) or default-on? SOC 2 doesn't require full
  IP; some customers will want /24 by default.
- **Q2:** Does `diff_json` need a max size? Policy docs can be large —
  propose capping at 64 KB and emitting `"diff_truncated": true` with
  pointer to the `policy_snapshots/` artifact.
- **Q3:** Should denials without an agent (e.g., login failures) appear
  in `change_log` at all, or stay isolated to `access_log`? Current
  leaning: keep change_log agent-centric; `actor.not_authorized` at
  login goes to `access_log` only.

## References

- [export-profiles.md](../compliance/export-profiles.md) — v1 artifact
  shape this spec updates.
- [attestation-format.md](../forensics/attestation-format.md) — signer
  envelope format and retention.
- [key-rotation.md](../forensics/key-rotation.md) — forensic signer
  key lifecycle (`signing_key_id` derivation).
- [trust-model.md](../forensics/trust-model.md) — threat model the
  cryptographic columns defend against.
- [ADR-002-compliance-exports.md](../ADR-002-compliance-exports.md) —
  original decision record for the export profile system.
