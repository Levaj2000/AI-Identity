# AI Identity forensic capture modes

**Status:** Draft for review. Nothing in this document is implemented yet
except where section 2 describes current behavior. Tracked as AI-12 (v0.6.0).
**Owner:** CTO
**Last reviewed:** 2026-09-30

"Deep capture for regulated flows, summarized capture for dev/test, cost
optimization at scale" is a roadmap line. This document turns it into
something testable. It:

1. States what the audit log captures today, precisely (section 2).
2. Defines the capture modes and exactly what each one records (section 4).
3. Fixes the rules that keep every mode compatible with the evidence chain,
   the retention reaper and the Case File bundle (sections 3, 5 to 8).
4. Names what a capture mode can and cannot prove (section 9).

Companion documents, all in `docs/forensics/`:

- [`export-bundle-format.md`](export-bundle-format.md): the Case File bundle and its verification tiers
- [`trust-model.md`](trust-model.md): what a valid attestation proves and does not prove
- [`retention-tombstones-in-exports.md`](retention-tombstones-in-exports.md): how pruned rows stay accounted for

## 1. Terms

- **Row:** one `audit_log` entry, chained by `entry_hash` (platform key) and
  `entry_hash_org` (org key). The canonical payload each hash covers is
  defined in `export-bundle-format.md` section 6.
- **Decision fields:** the row columns the chain hashes: `agent_id`,
  `endpoint`, `method`, `decision`, `cost_estimate_usd`, `latency_ms`,
  `created_at`, the predecessor hash, and `request_metadata`.
- **Content:** anything the agent sent or received: prompts, completions,
  request and response bodies, tool arguments and tool results.
- **Content digest:** a salted SHA-256 over one content item (section 6.2).
- **Capture mode:** the named depth at which a row is recorded, fixed when the
  row is written.

## 2. What is captured today

The audit log is a **record of decisions, not of content**. This section is a
description of current behavior, verified in the platform source on
2026-09-30.

- **The gateway never sees content.** `POST /gateway/enforce` takes the agent
  id, endpoint, method, key type and, for mandate draws, spend fields. It
  decides allow or deny; it does not proxy the request, so no body, prompt,
  completion, header or tool argument ever reaches it.
- **Every row passes a sanitizer** before it is hashed. `request_metadata`
  keeps only allowlisted keys, drops any key on a body and PII blocklist
  (`body`, `payload`, `content`, `headers`, `token`, `email` and pattern
  matches), truncates strings at 500 characters, keeps at most 20 keys, and
  drops nested lists and objects.
- **What gateway rows carry:** the decision, policy version, deny rule and
  reason, status code, key type, upstream latency, and for mandate-backed
  requests the credential format and spend and limit amounts. The allowlist
  includes `model` and `token_count`, but no caller supplies them today, so
  the cost estimate on gateway rows is empty.
- **Lifecycle rows** (agents, keys, sinks, edges, mandates, retention events)
  carry action type, resource type, a small `diff`, and request context (IP
  address, user agent, request id).
- **Nothing varies per org or per agent.** There is no capture setting of
  any kind; every org gets the same depth.
- **Edge ingest is a separate path.** `POST /api/v1/audit/ingest` stores
  signed OCSF records from off-platform edges verbatim, verified by their own
  signatures and stream continuity, not by the audit chain or the sanitizer.
  This document does not change edge ingest (section 11).

Known gaps found while writing this, tracked separately:

- Retention rules and legal holds can select on `flow_tag`, `risk_tier`,
  `session_id` and `event_type`, but the sanitizer drops all four, so those
  selectors never match (AI-64). Section 5 fixes the capture side.
- Retention rules accept `redact_after`, but nothing redacts. Section 7 gives
  it something to act on.

## 3. Principles (normative)

1. **Depth is fixed at write time.** The chain commits to exactly what was
   captured. A row can never be deepened later, and the only way to make one
   shallower later is retention: pruning with a tombstone, or redacting
   content held outside the chain (section 7). No mode change rewrites a
   written row.
2. **Every row says how it was captured.** The mode is inside the hashed
   payload, so a verifier can tell a `standard` row from a `deep` one, and
   nobody can pass a shallow row off as deep, or the reverse, without breaking
   the chain.
3. **The chain commits to digests, never to content.** Content lives outside
   the chain, so it can be redacted or erased without breaking a hash, while
   the digest in the chain still proves what was there.
4. **The platform records what it was told.** Content the platform never
   observed is recorded as reported by the caller, and every artifact says so
   (section 9). Deep capture raises detail, not assurance.
5. **Policy-bearing fields come from a trusted source.** A field that decides
   retention, holds or mode (`flow_tag`, `risk_tier`, `capture_mode`) is set by
   the platform from org or agent configuration, never taken from
   caller-supplied metadata. Otherwise a caller could tag itself out of a
   legal hold.
6. **Regulated flows fail closed.** A flow tagged `regulated` is never
   captured below its required mode. If the required mode cannot be met, the
   request is denied, not recorded shallow.
7. **No sampling at capture.** Dropping rows at write time would break the
   gap-free org chain that Tier P checks for org-scope exports. Volume is
   reduced by retention (sampling and `retain_for`), which leaves a tombstone
   for every row it removes.

## 4. The modes

| Mode | Intended for | Rows written | Content recorded | Content digests in chain |
|---|---|---|---|---|
| `standard` | Default for every org; today's behavior | Every decision | None | None |
| `deep` | Regulated flows, incident response | Every decision | As submitted by the caller, held outside the chain | Yes, one per item |

### 4.1 `standard`

Exactly the capture described in section 2, plus the fields section 5 adds.
Existing rows are `standard` rows: a row without a `capture_mode` key is
read as `standard`.

### 4.2 `deep`

Everything `standard` records, plus:

- `content_digests`: an object whose keys name the item (`request`,
  `response`, `tool_args`, `tool_result`) and whose values are content digests
  (section 6.2). Only the items the caller submitted appear.
- `model` and token counts (`input_tokens`, `output_tokens`), when supplied.
- The content itself, stored outside the chain in the content store (section
  7), keyed by row id and item.

Because the gateway never sees content (section 2), a `deep` row needs the
caller to submit it: the SDK or proxy integration sends the content, or its
digests, with the enforce call or in a follow-up tied to the decision's
correlation id. A decision whose content never arrives stays a `deep` row
with its digests absent, and the row says so (section 6.1). It is never
silently recorded as `standard`.

### 4.3 Why there is no `summary` mode

The roadmap line asks for "summarized capture for dev/test". This draft
proposes not building it as a capture mode:

- Rows are already small. The sanitizer bounds `request_metadata` at 20 keys
  of at most 500 characters each, and no content is stored. There is little
  to summarize.
- The cost of a dev/test org is row *count*, not row size, and reducing count
  at capture would break chain completeness (principle 7).
- Retention already does the job safely. A dev/test policy with a short
  `retain_for` and deterministic sampling reduces stored rows, and every
  removed row leaves a tombstone.

If measurement (section 10, item 1) shows a real storage cost that retention
cannot address, a summary mode can be added later as a new mode without
changing this document's principles. Open question 1.

## 5. Configuration

- **Org default mode**, set by an org owner or admin. Changing it is a chained
  audit event recording the old mode, the new mode, who and when, like a
  retention policy change. It applies to rows written after the change and
  never to existing rows.
- **Per-agent and per-flow overrides** may only raise the mode, never lower it
  below the org default.
- **Flow tags** (`flow_tag`, `risk_tier`) are set in agent or org
  configuration and written into the row by the platform, after the sanitizer,
  as trusted fields (principle 5). This also makes the retention and hold
  selectors of AI-64 match.
- **Regulated flows:** a flow tagged `regulated` requires `deep`, and only on
  tiers where regulated ingestion is allowed. The existing tier check
  (`regulated_ingestion_allowed`) is called on the capture path; a flow that
  fails it is denied (principle 6).

## 6. What the chain covers

### 6.1 New fields in `request_metadata`

All new fields live inside `request_metadata`, which the chain already
hashes. The canonical payload and its serialization rules
(`export-bundle-format.md` section 6) do not change, so existing verifiers
recompute new rows with no change.

| Key | Present | Value |
|---|---|---|
| `capture_mode` | Every row written after this ships | `standard` or `deep` |
| `flow_tag`, `risk_tier` | When configured | Short strings from configuration (section 5) |
| `content_digests` | `deep` rows with submitted content | Object of item name to digest (section 6.2) |
| `content_missing` | `deep` rows where expected content never arrived | List of item names |
| `model`, `input_tokens`, `output_tokens` | When supplied | As supplied |

The sanitizer currently drops nested objects and lists. It gains a narrow,
typed exception for exactly these keys: `content_digests` is an object of
known item names to 64-character lowercase hex strings, and `content_missing`
is a list of known item names. Anything else in those keys drops the row's
content fields and records `content_missing`, rather than letting arbitrary
structure into the chain.

### 6.2 Content digests

`digest = hex(SHA-256(salt || content_bytes))`, where `salt` is 16 random
bytes generated per row and item. The salt is stored with the content, never
in the chain.

The salt is required. Many content items are short and guessable (a yes or no
answer, a fixed tool argument), and an unsalted digest in a published record
can be reversed by trying candidates. This is the same reasoning as
`export-bundle-format.md` section 11 item 1. Without the salt, a digest
proves nothing to anyone; with it, anyone given the content and its salt can
confirm the digest in the signed chain.

## 7. The content store

- **Separate from `audit_log`.** One record per row and item: row id, item
  name, salt, content bytes, and a `redacted_at` timestamp.
- **Encrypted at rest** under a per-org key. Open question 4.
- **Redaction.** A retention rule's `redact_after` deletes the content bytes
  and salt and sets `redacted_at`. The row, its digests and the chain are
  untouched. After redaction the digest still proves that content existed and
  was committed, but the content can no longer be produced or confirmed.
  Redaction is recorded as a chained retention event, like a prune.
- **Pruning a row** (the existing reaper) deletes its content records too.
- **Legal holds** freeze content as well as rows: held content is never
  redacted.

## 8. Exports

- **Case File bundles (v1).** Deep rows export exactly as today. Their new
  `request_metadata` fields, digests included, are part of each event in the
  case file, and the existing verifier recomputes them unchanged. Content is
  **not** included in v1 bundles: a v1 verifier rejects any file not in the
  signed inventory's known roles. Shipping content in a bundle needs a
  bundle-format change with its own verifier support. Open question 3.
- **Content on request.** An authorized org user can fetch a row's content
  and salts from the API and check each digest against the row in a verified
  bundle. That check needs no platform key.
- **OCSF export and sinks.** Digests and `capture_mode` map into the OCSF
  record, under `unmapped` until a native home is agreed. Content is never
  sent to a sink.

## 9. What a mode proves, and does not prove

A verified `deep` row proves, under the tiers of
`export-bundle-format.md` section 9:

- which content items the caller submitted for that decision, and a
  commitment to each item's exact bytes at write time
- that the row was captured as `deep`, so the absence of content is recorded
  (`content_missing`), never inferred from silence

It does not prove:

- **that the submitted content is what the agent actually sent or received.**
  The platform records what the caller reported; the gateway never observes
  the traffic
- that content deleted by redaction ever matched its digest, once the
  content and salt are gone
- anything about a `standard` row's content, which was never captured

Stated plainly for relying parties: deep capture raises the detail of the
record, not the assurance of the decision fields.

## 10. Implementation delta

1. **Measure first.** Add bytes-per-org and rows-per-org metrics for
   `audit_log`. There is no volume metric today, so any cost claim for a mode
   would be a guess.
2. Trusted-field path: `capture_mode`, `flow_tag` and `risk_tier` written by
   the platform after sanitizing (sections 5 and 6.1). This closes the capture
   side of AI-64.
3. Org and agent mode configuration, with changes chained (section 5).
4. Regulated-flow enforcement on the capture path (principle 6).
5. Deep capture intake: content or digests with the enforce call or a
   correlated follow-up; the sanitizer's typed exception (section 6.1).
6. The content store, with encryption, redaction for `redact_after`, and
   prune and hold integration (section 7).
7. Content-on-request API (section 8).
8. Tests for every rule above, including: a caller cannot set
   `capture_mode` or `flow_tag` through metadata; a regulated flow that cannot
   be captured deep is denied; redaction leaves the chain verifying; a held
   row's content is never redacted.

No verifier change is required for items 1 to 7: every new field lives in
`request_metadata`, which the verifier already recomputes.

## 11. Open questions

1. **Summary mode.** Is there a real need that retention cannot meet
   (section 4.3)? Decide after item 1 of section 10 produces numbers.
2. **Caller-submitted content.** Is caller-reported content, clearly labelled
   as such, useful enough for regulated customers, or does deep capture need a
   proxying integration where the platform observes the traffic itself?
3. **Content in bundles.** A v2 bundle role for content, or content always
   delivered separately and matched by digest?
4. **Key custody for the content store.** Platform-held per-org keys, or
   customer-managed keys, and what that means for redaction and legal holds.
5. **Erasure requests.** Redaction removes content and salt; is a salted
   digest of erased content itself personal data? Our reading is that it is
   not, once the salt is gone, but this needs legal review before regulated
   customers rely on it.
6. **Edge ingest.** Should edge records carry `capture_mode` too, or stay
   verbatim OCSF as today?
