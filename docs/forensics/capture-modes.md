# AI Identity forensic capture modes

**Status:** Draft for review, partly implemented. Section 10 items 1, 2 and
4 are live on the platform; the rest is not. Open questions 2 and 4 are
decided (section 11). Section 2 describes behavior before any of this
shipped. Tracked as AI-12 (spec) and AI-66 (build), v0.6.0.
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
caller to submit it (decided, section 11 item 2). The caller sends content,
never digests: the platform salts and digests every item itself (section 6.2),
so a digest in the chain is always the platform's own computation.

The decision row is hashed when the enforce call returns, which is before the
upstream call is made, so content reaches the chain in two places:

- **Request side** (`request`, `tool_args`): sent with the enforce call. The
  platform digests each item before it writes the decision row, so the
  digests are inside that row's hash.
- **Response side** (`response`, `tool_result`): sent after the upstream call
  returns, in a follow-up that names the decision row (section 5.1). The
  platform writes a separate chained row, `action_type: content_recorded`,
  carrying the decision row's id and the response-side digests. The decision
  row is never changed.

Every `deep` decision row lists `content_expected`: the items its mode
requires, fixed when the row is written. An expected item with no digest on
the decision row, and none on a `content_recorded` row for it, is missing.
Missing items are computed when the record is read or exported, never written
back, so a deep decision whose content never arrives still states what it
expected and shows what is absent. It is never silently recorded as
`standard`.

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

- **Org default mode**, stored on the organization and set by an org owner
  or admin (`PUT /api/v1/orgs/me/capture-mode`). Each change is a chained
  `capture_mode_changed` retention-plane event recording the old mode, the new
  mode, who and when, anchored through the org's `retention-service` agent
  like a policy publication. It applies to rows written after the change and
  never to existing rows.
- **Per-agent overrides:** `capture_mode` in the agent's configuration, on the
  same trusted path as `flow_tag`. The effective mode is the higher of the org
  default and the agent override, so an override can only raise the mode,
  never lower it.
- **Availability:** `deep` is offered on the tiers that may hold regulated
  records (business and enterprise). Setting it elsewhere is refused.
- **Flow tags** (`flow_tag`, `risk_tier`) are set in agent or org
  configuration and written into the row by the platform, after the sanitizer,
  as trusted fields (principle 5). This also makes the retention and hold
  selectors of AI-64 match.
- **Regulated flows:** a flow tagged `regulated` requires `deep`, and only on
  tiers where regulated ingestion is allowed. Its effective mode is raised to
  `deep` automatically, so the required mode is met by construction. The tier
  check (`regulated_ingestion_allowed`) runs on the capture path: the agent
  API refuses the tag and the gateway denies the request where it fails
  (principle 6; implemented).

### 5.1 Deep intake

- **With the enforce call:** an optional JSON body,
  `{"content": {"request": "...", "tool_args": "..."}}`. Only those two item
  names; each value a UTF-8 string of at most 256 KiB. On a `standard`
  decision the body is discarded unread: submitting content never raises the
  mode and is never stored.
- **After the upstream call:** `POST /gateway/content`, authenticated with the
  same agent key, naming the decision row's id (returned by the enforce call
  as `audit_id`) with `{"content": {"response": "...", "tool_result": "..."}}`.
  Accepted only for the calling agent's own `deep` decision, only for items in
  that row's `content_expected` not already recorded, and only within 15
  minutes of the decision. Each accepted follow-up writes one
  `content_recorded` row.
- **Rejections are whole:** an oversized item (413), an unknown item name
  (422), a late or repeated follow-up (409), or a decision that is not the
  caller's or not `deep` (404) records nothing, not part of the request.

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
| `content_expected` | `deep` decision rows | List of the item names the mode requires |
| `content_digests` | `deep` decision and `content_recorded` rows with submitted content | Object of item name to digest (section 6.2) |
| `content_source` | Rows carrying `content_digests` | `caller`: the content was reported, not observed (section 9) |
| `decision_audit_id` | `content_recorded` rows | Id of the decision row the content belongs to |
| `model`, `input_tokens`, `output_tokens` | When supplied | As supplied |

None of these keys can come from caller metadata. The sanitizer drops them
like any key off its allowlist, and the writer sets them afterwards from the
platform's own computation, on the same trusted path as `capture_mode` and
`flow_tag`. The writer checks their shape before hashing: `content_digests`
maps known item names to 64-character lowercase hex strings, and
`content_expected` is a list of known item names.

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
- **Encrypted at rest** under a per-org key held by the platform (decided,
  section 11 item 4): envelope encryption, with each org's data key wrapped by
  a platform KMS key and each item encrypted with AES-256-GCM under the org's
  data key. Customer-managed keys are a later enterprise option with their
  own spec.
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
  commitment to each item's exact bytes at the time they were recorded
- that the row was captured as `deep` and which items it expected
  (`content_expected`), so absent content is visible, never inferred from
  silence. In an `org`-scope export, whose completeness Tier P checks, an
  expected item with no digest was never submitted. In an `agent` or
  `incident` slice, its `content_recorded` row may simply lie outside the
  slice

It does not prove:

- **that the submitted content is what the agent actually sent or received.**
  The platform records what the caller reported, and every such row says so
  (`content_source: caller`); the gateway never observes the traffic
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
5. Deep capture intake: request-side content with the enforce call and
   response-side content in a `content_recorded` follow-up (section 5.1);
   platform-computed digests on the trusted path (section 6.1).
6. The content store, with encryption, redaction for `redact_after`, and
   prune and hold integration (section 7).
7. Content-on-request API (section 8).
8. Tests for every rule above, including: a caller cannot set
   `capture_mode` or `flow_tag` through metadata; a regulated flow that cannot
   be captured deep is denied; redaction leaves the chain verifying; a held
   row's content is never redacted.

Items 1, 2 and 4 are implemented. No verifier change is required for items
1 to 7: every new field lives in `request_metadata`, which the verifier
already recomputes.

## 11. Open questions

1. **Summary mode.** Is there a real need that retention cannot meet
   (section 4.3)? Decide after item 1 of section 10 produces numbers.
2. **Caller-submitted content.** Decided 2026-09-30: caller-submitted
   content, labelled `content_source: caller` on every row that carries its
   digests (section 6.1). A proxying integration, where the platform observes
   the traffic itself, can be added later as a separate source value.
3. **Content in bundles.** A v2 bundle role for content, or content always
   delivered separately and matched by digest?
4. **Key custody for the content store.** Decided 2026-09-30: platform-held
   per-org keys to start (section 7). Customer-managed keys, and what they
   mean for redaction and legal holds, are a later enterprise option.
5. **Erasure requests.** Redaction removes content and salt; is a salted
   digest of erased content itself personal data? Our reading is that it is
   not, once the salt is gone, but this needs legal review before regulated
   customers rely on it.
6. **Edge ingest.** Should edge records carry `capture_mode` too, or stay
   verbatim OCSF as today?
