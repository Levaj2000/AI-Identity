# Agent Trust-Base Inventory — Worked Sample for ocsf-schema#1724

Supporting data for [ocsf/ocsf-schema#1724](https://github.com/ocsf/ocsf-schema/issues/1724)
(*Discovery: agent trust-base inventory, applying record_integrity per emission*,
@rabbidave, 2026-08-11). Four worked events showing the proposed class's two-sided
record — **declared configuration** + **executed parameters** — in the
**admission/closure pair shape** (@rabbidave's 2026-08-21 comment on the issue),
chained with the **`record_integrity` profile exactly as merged in OCSF 1.9**
(#1661), which AI Identity ships from a production gateway today (see
`../ocsf-log-reference-bundle/`).

**Rev 2 (2026-08-24)** — the three-event Rev 1 becomes the pair shape: one
record shape, two firing points. The boundary opens with an **admission**
emission, mid-boundary trust-base changes land as further admissions, and the
boundary closes with a **closure** emission carrying the executed half *as
observed*. Divergence is a consumer-computed diff of two records on one chain,
and an admission with no closure is a structurally checkable gap — the same
detection primitive as an unchained trust-base change. Rev 2 also adds the
descriptive **`verification_id`** strength-of-claim vocabulary from the same
comment (1 Locally computed · 2 Provider asserted · 3 Third-party attested ·
4 Not observable).

The point of this sample: the issue's design holds together on real schema shapes.
The `ai_agent` object already carries the identity spine the proposal needs
(`uid` / `instance_uid` / `version` / `charter` / `ai_model` — verified against
ocsf-schema `main`), `fingerprint` objects are the natural carrier for every content
digest, and applying `record_integrity` per emission needs nothing invented.

**PR-shaped class definition** (events/objects/dictionary files this
sample's shape follows): `docs/ocsf-1724-class-draft/`. The pair firing points
and `verification_id` siblings are ahead of that draft — they follow the
2026-08-21 issue discussion and land in the co-drafted class PR.

---

## Files

| File | What it is |
|---|---|
| `agent-trust-base-inventory.sample.ndjson` | 4 chained events (generated — do not hand-edit) |
| `build_sample.py` | Generates the ndjson and verifies it: fingerprints, chain linkage, digest preimages, pair discipline, the adapter divergence |

**Verify with nothing but python3** — no keys, no packages:

```bash
python3 build_sample.py --verify
# ✓ 4 events: fingerprints recompute, chain links, content digests resolve
#   to named preimages, admission/closure discipline holds (admissions omit
#   tools_invoked; closure carries executed-as-observed within the
#   allowlist), declared≠loaded adapter divergence present with
#   verification_id 2 vs 1
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

## Walkthrough — one agent instance, one boundary, four emissions

Same demo org and agent as the production reference bundle (`QA-eae97318`,
uid `32928870…`, org `f3576cf6…`), so these Discovery events read as the
companions to that bundle's API Activity chain: the activity chain records what
the agent **did**; this chain records what the agent **was** when it did it.

| # | `metadata.uid` | firing point | activity *(provisional)* | moment | what it shows |
|---|---|---|---|---|---|
| 1 | `tbi-0001` | **Admission** (genesis) | 2 Collect | boundary opens | Baseline: declared and executed-as-resolved agree. Genesis — no `prev_event`. No `tools_invoked` — nothing has run, and absence is the claim. |
| 2 | `tbi-0002` | **Admission** (mid-boundary) | 3 Change | +5 min, MCP `tools/list` refresh | The remote schema source re-served with a new digest (adds `billing.refund_execute`). Emitted **before** any refreshed tool serves a call — the record a PDP denies on. Declared toolset now exceeds the enforced allowlist. |
| 3 | `tbi-0003` | **Admission** (mid-boundary) | 3 Change | +9 min, adapter init | `refunds-tone-lora` loads mid-task. Registry-declared digest (`verification_id` 2) ≠ digest of the bytes actually mapped (`verification_id` 1). Emitted after load, **before the adapter's first inference**. |
| 4 | `tbi-0004` | **Closure** | 1 Log | +25 min, boundary closes | Same declared half; executed half **as observed**: tools actually invoked (all inside the enforced allowlist — `billing.refund_execute` never ran), sampling as finally applied (stable here — the contrast case to a mid-flight rewrite), adapters as loaded. |

The **activity mapping is provisional**: which of Log / Collect / Change
carries admission vs closure is a class-PR decision — the pair is the
requirement, the mapping is not. This sample picks one and says so.

### Admission/closure discipline (the timing overload, removed)

Admission emissions carry the executed half *as resolved at admission* — the
allowlist as enforced, sampling as accepted, credentials reachable — and
**omit** close-observable fields. `tools_invoked` appears only on the closure:
absent-at-admission is a different claim from empty, and Rev 1's event 2
carrying `tools_invoked` was itself a small instance of the overload the pair
removes (an admission-time record claiming a closure-time observable). The
verifier enforces this structurally. How to mark a close-observable *scalar*
explicitly (`verification_id` 4, "structurally unavailable at this vantage
point") rather than by absence is an open question for the class PR.

The pair also extends the chain's detection semantics: within one instance's
boundary, **an admission with no closure is a gap** — checkable by chain
structure, the same primitive that catches an unchained trust-base change.

### The divergences a consumer computes (no producer judgment needed)

The issue's key design argument — emit declared and executed raw so
*downstream consumers* compute divergence — is exercised twice:

**Events 2→4, benign divergence (policy working as intended):**

| | value |
|---|---|
| `declared_configuration.artifacts[]` (`type_id` 3 Tool Schema), from event 2 on | digest of `tools/list` **v42** — now includes `billing.refund_execute` |
| `executed_parameters.tool_allowlist` (every emission) | unchanged: `billing.get_invoice`, `billing.refund_status`, `kb.search` |
| `executed_parameters.tools_invoked` (closure only) | `kb.search`, `billing.get_invoice`, `billing.refund_status` — the declared-but-never-admitted tool never ran |

A tool appeared upstream; the enforced allowlist did not admit it; the closure
confirms it never executed. The gap is visible as a diff across the pair, and
it is *good news* — but only a consumer holding both sides can say so.

**Events 3+4, the Sleeper-Agents scenario (the reason this class earns its place):**

| | SHA-256 | `verification_id` |
|---|---|---|
| `declared_configuration.artifacts[]` (`type_id` 2 Adapter) | `sha256("…artifact as published in the adapter registry")` | 2 — Provider asserted |
| `executed_parameters.artifacts[]` (`type_id` 2 Adapter) | `sha256("…artifact bytes actually mapped at load time…")` — **differs** | 1 — Locally computed |

Same name, same version string, different bytes — and visibly different
*strengths of claim*: a registry assertion and a local byte-hash are not the
same kind of evidence, and the sibling keeps that from mixing silently.
Behavioral observation cannot reliably catch a conditionally-triggered
artifact (Hubinger et al.); a digest comparison catches the swap
unconditionally — *if* the load was recorded. And because the admission
emission precedes the adapter's first inference, a policy decision point
subscribed to this stream can deny **before** the artifact executes. The same
record is prevention before execution and forensics after it.

The producer stays honest throughout: `severity_id` 1, both sides reported,
no verdict embedded — the closure records what ran, and enforcement outcomes
stay with the gateway/PDP's events, one `metadata.correlation_uid` join away
(where `stop_reason_id` lives once
[#1704](https://github.com/ocsf/ocsf-schema/issues/1704) lands). Detection is
a *finding* produced downstream — matching the issue's stated non-goal of
behavioral malware detection.

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
  / `executed_parameters`, one typed `artifacts` array) plus the pair firing
  points and `verification_id` siblings from the 2026-08-21 issue
  discussion — drafted, not submitted. Final naming, numbering, requirement
  levels, and the activity↔firing-point mapping belong to the working group.
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
  overclaim. The tuple carries `verification_id` 2 (Provider asserted): it
  is a *reference*, not a byte-binding, and the served artifact can change
  beneath a stable version string — the sibling keeps that visible. Digests
  appear exactly where bytes are locally loaded: the `artifacts` array
  (adapters, tool schemas, policy bundles) and the charter's `hashes` on
  `ai_agent.charter` (an existing `file` object — no new attribute needed).
- **`verification_id` is descriptive, not normative.** The record says what
  kind of claim each element is; whether any kind is *sufficient* for a
  given control stays a relying-party policy decision. The spec does not
  rank evidence, and neither does this sample.

---

*Generated for CoSAI WS4 / OCSF AI WG collaboration in support of
ocsf-schema#1724. Profile shapes: `record_integrity` as merged in OCSF 1.9
(#1661); `ai_agent`/`ai_model` as on ocsf-schema `main` 2026-08-11. Pair
firing points and `verification_id` per the issue discussion of 2026-08-21.*
