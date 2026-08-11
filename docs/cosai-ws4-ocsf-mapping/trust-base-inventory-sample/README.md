# Agent Trust-Base Inventory — Worked Sample for ocsf-schema#1724

Supporting data for [ocsf/ocsf-schema#1724](https://github.com/ocsf/ocsf-schema/issues/1724)
(*Discovery: agent trust-base inventory, applying record_integrity per emission*,
@rabbidave, 2026-08-11). Three worked events showing the proposed class's two-sided
record — **declared configuration** + **executed parameters** — chained with the
**`record_integrity` profile exactly as merged in OCSF 1.9** (#1661), which AI Identity
ships from a production gateway today (see `../ocsf-log-reference-bundle/`).

The point of this sample: the issue's design holds together on real schema shapes.
The `ai_agent` object already carries the identity spine the proposal needs
(`uid` / `instance_uid` / `version` / `charter` / `ai_model` — verified against
ocsf-schema `main`), `fingerprint` objects are the natural carrier for every content
digest, and applying `record_integrity` per emission needs nothing invented.

Review + assessment: `docs/ocsf-1724-trust-base-review.md`. Paste-ready issue
response: `docs/ocsf-1724-draft-issue-comment.md`. **PR-shaped class
definition** (events/objects/dictionary files this sample's shape follows):
`docs/ocsf-1724-class-draft/`.

---

## Files

| File | What it is |
|---|---|
| `agent-trust-base-inventory.sample.ndjson` | 3 chained events (generated — do not hand-edit) |
| `build_sample.py` | Generates the ndjson and verifies it: fingerprints, chain linkage, digest preimages, the event-3 divergence |

**Verify with nothing but python3** — no keys, no packages:

```bash
python3 build_sample.py --verify
# ✓ 3 events: fingerprints recompute, chain links, content digests resolve
#   to named preimages, event-3 declared≠loaded divergence present
```

Every hash in the sample is computed, not hand-typed: content digests are SHA-256
over the ASCII preimages named in `build_sample.py`'s `DIGEST_PREIMAGES` (standing
in for the artifact bytes a real producer would hash), and event fingerprints are
SHA-256 over the event's sorted-keys compact JSON with the attestation's
`fingerprint`/`signatures` excluded — the merged #1661 semantics, same as our CPEX
plugin v0.0.3 implements them (`uid`/`chain_uid`/`authority_uid`/`prev_event` stay
*inside* the hashed bytes, so linkage and claimed authority can't be swapped
post-hoc).

---

## Walkthrough — one agent instance, three emissions

Same demo org and agent as the production reference bundle (`QA-eae97318`,
uid `32928870…`, org `f3576cf6…`), so these Discovery events read as the
companions to that bundle's API Activity chain: the activity chain records what
the agent **did**; this chain records what the agent **was** when it did it.

| # | `metadata.uid` | activity | moment | what it shows |
|---|---|---|---|---|
| 1 | `tbi-0001` | 2 Collect | session start | Baseline snapshot: declared and executed agree. Genesis — no `prev_event`. |
| 2 | `tbi-0002` | 3 Change *(proposed)* | +5 min, MCP `tools/list` refresh | The remote schema source re-served with a new digest (adds `billing.refund_execute`). Emitted **before** any refreshed tool serves a call. Declared toolset now exceeds the executed allowlist — benign, policy-enforced divergence. |
| 3 | `tbi-0003` | 3 Change *(proposed)* | +9 min, adapter init | `refunds-tone-lora` loads mid-task. Registry-declared digest ≠ digest of the bytes actually mapped. Emitted after load, **before the adapter's first inference**. |

### The divergences a consumer computes (no producer judgment needed)

The issue's key design argument — emit declared and executed together so
*downstream consumers* compute divergence — is exercised twice:

**Event 2, benign divergence (policy working as intended):**

| | value |
|---|---|
| `declared_configuration.artifacts[]` (`type_id` 3 Tool Schema) | digest of `tools/list` **v42** — now includes `billing.refund_execute` |
| `executed_parameters.tool_allowlist` | unchanged: `billing.get_invoice`, `billing.refund_status`, `kb.search` |

A tool appeared upstream; the enforced allowlist did not admit it. The gap is
visible in a single event, and it is *good news* — but only a consumer holding
both sides can say so.

**Event 3, the Sleeper-Agents scenario (the reason this class earns its place):**

| | SHA-256 |
|---|---|
| `declared_configuration.artifacts[]` (`type_id` 2 Adapter) | `sha256("…artifact as published in the adapter registry")` |
| `executed_parameters.artifacts[]` (`type_id` 2 Adapter) | `sha256("…artifact bytes actually mapped at load time…")` — **differs** |

Same name, same version string, different bytes. Behavioral observation cannot
reliably catch a conditionally-triggered artifact (Hubinger et al.); a digest
comparison catches the swap unconditionally — *if* the load was recorded. And
because the emission precedes the adapter's first inference, a policy decision
point subscribed to this stream can deny **before** the artifact executes.
That is the issue's admission-control timing argument, made concrete: the same
record is prevention before execution and forensics after it.

The producer stays honest in both cases: `severity_id` 1, both sides reported,
no verdict embedded. Detection is a *finding* produced downstream — matching the
issue's stated non-goal of behavioral malware detection.

### Why `chain_uid` = the agent's `instance_uid`

The integrity chain is scoped to the agent **instance** (`0c9b8f2e…`), not the
org. That gives the chain itself a detection semantic: within one instance's
lifetime, a trust-base change that executed without a corresponding chained
emission is a **gap in the chain** — checkable structurally, without trusting
the producer's completeness claims event-by-event. `prev_event.uid` resolves
against `metadata.uid` per the merged shape; the genesis emission omits
`prev_event` entirely (the lesson from our production bundle: sentinel values
inside `fingerprint` are an anti-pattern).

---

## Honest limitations (no overclaim)

- **The proposed class does not exist.** `class_uid` 1000005 is a
  vendor-namespace placeholder (1000000+ range, per OCSF convention) and
  `metadata.version` says `1.10.0-dev`. The event shape follows the
  PR-shaped draft in `docs/ocsf-1724-class-draft/` (`declared_configuration`
  / `executed_parameters`, one typed `artifacts` array, activity `Change`) —
  drafted, not submitted. Final naming, numbering, and requirement levels
  belong to the working group.
- **Synthetic preimages.** Content digests hash *descriptions* of artifacts,
  not artifacts — the sample optimizes for end-to-end recomputability with
  stdlib only. The production reference bundle next door is the
  real-export counterpart (for the activity chain).
- **Unsigned by choice.** Events carry `fingerprint` without `signatures`
  (the schema's `at_least_one` constraint holds). Per-event ECDSA signing is
  demonstrated with production keys in `../ocsf-log-reference-bundle/`; the
  signature-bytes/key-id gap ([#1709](https://github.com/ocsf/ocsf-schema/pull/1709))
  applies to this class the same way.
- **Hosted-model nuance.** `declared_configuration.ai_model` carries the
  pinned `ai_model` tuple, not a weights digest — for an API-served model
  there are no local artifact bytes to hash, and inventing a digest would
  overclaim. Digests appear exactly where bytes are locally loaded: the
  `artifacts` array (adapters, tool schemas, policy bundles) and the
  charter's `hashes` on `ai_agent.charter` (an existing `file` object — no
  new attribute needed).

---

*Generated for CoSAI WS4 / OCSF AI WG collaboration in support of
ocsf-schema#1724. Profile shapes: `record_integrity` as merged in OCSF 1.9
(#1661); `ai_agent`/`ai_model` as on ocsf-schema `main` 2026-08-11.*
