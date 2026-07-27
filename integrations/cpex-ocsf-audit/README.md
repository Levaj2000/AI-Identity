# cpex-plugin-ocsf-audit

A CPEX CMF plugin that emits each dispatched request as an **OCSF AI Operation event**, off
the `run(audit-log)` seam — optionally wrapped in a tamper-evident **attestation chain** and
DSSE-signed.

It is a near-twin of the upstream [`audit-logger`](https://github.com/contextforge-org/cpex/tree/dev/builtins/plugins/audit-logger)
builtin (same observation-only, always-allow contract; same factory + hook wiring). The only
difference is the record shape:

| | `audit-logger` (upstream) | `ocsf-audit` (this crate) |
|---|---|---|
| Output | free-form JSON line | OCSF AI Operation event |
| Verifiability | none | hash chain (`entry_hash`→`prev_entry_hash`), DSSE-ready |
| Schema | ad hoc | OCSF — interoperable across tools |

**Why:** it makes CPEX's enforcement record *interoperable* (OCSF) and *independently
verifiable* (signed attestation chain) **without CPEX having to own a schema**. CPEX produces
the event; this plugin makes it portable and verifiable offline. That is the AI Identity lane
in the interop map: the record/evidence layer.

## The mapping

The executable CMF `Message` + `Extensions` → OCSF field mapping is [`src/ocsf.rs`](src/ocsf.rs).
(The prose field-map table is maintained privately — it quotes unreleased CPEX branch internals —
so the source is the public reference.)
Five fields have no native OCSF home yet (`completion.stop_reason`, `mcp.*`, `framework.*`,
monotonic security labels, full workload attestation); the plugin emits them under OCSF
`unmapped` (config `include_gap_fields`, default on). That preserves evidence **and** makes the
open OCSF/WS4 gaps self-documenting in the wire output.

## Wiring (APL)

```yaml
routes:
  - tool: get_compensation
    policy:
      - "require(role.hr)"
      - "delegate(workday-oauth, target: workday-api, permissions: [read_compensation])"
      - "run(audit-log)"        # existing enforcement steps unchanged
plugins:
  - name: ocsf-audit
    kind: audit/ocsf
    hooks:                       # POST hooks: result/taint/delegation resolved
      - cmf.tool_post_invoke
      - cmf.llm_output
      - cmf.resource_post_fetch
      - cmf.prompt_post_invoke   # NOT cmf.prompt_post_fetch — see hook-name note below
    config:
      destination: stderr        # or: tracing
      chain: true                # tamper-evident entry_hash chain
      signing: none              # or: dsse (production)
      chain_uid: "org-f3576cf6"  # stable chain id across the deployment
```

> **Prompt hook name (review C6, fixed 2026-07-06).** Earlier revisions registered on
> `cmf.prompt_post_fetch` and prompt events **silently never fired**: cpex-core ships two
> contradictory prompt-hook constants — `hooks/types.rs` has `cmf.prompt_pre/post_fetch`
> (the Python plugins-adapter vocabulary), but the Rust CMF/APL runtime dispatches the
> `cmf/constants.rs` names `cmf.prompt_pre_invoke` / `cmf.prompt_post_invoke` (see
> `apl-cpex/visitor.rs`, `hooks/metadata.rs`, the `pii-scanner` builtin). A Rust CMF plugin
> must register on the `_invoke` names. With this fix, prompt events now actually fire.
> (The resource hooks agree across both files — only prompt diverges.)

## Status

Built **green** against `contextforge-org/cpex@feat/hil_apl` commit `ad666ba` — Teryl's
review baseline (`cargo build` clean, `cargo test` 13/13 passing, 2026-07-20). Every CMF
accessor path and `ContentPart` variant shape was confirmed against that commit.
Re-verified against the **public `dev` branch** at `baa9e17` (2026-07-27): build, all 13
tests, and the `emit_sample` example pass unchanged — no API drift between the two.

**Revision 0.0.2 (2026-07-20) — P0 + review §4-B**, per the production-readiness plan
(2026-07-17) and the decisions closed on the 2026-07-18 thread:

- **Host class applied: API Activity (6003)** — the `6010` placeholder and bespoke
  activity enum are gone. Activity ids follow API Activity's real enum with conformant
  OCSF captions: resources/prompts and `readOnlyHint: true` tools → `2 (Read)`;
  other tool invocations → `99 (Other)` + `activity_name: "Invoke Tool"`; completions →
  `99` + `"Completion"`. `destructiveHint` stays security context, never a Delete claim.
- **Profiles declared:** `metadata.profiles = ["ai_operation", "security_control"]`
  (+ `"record_integrity"` when chaining is on). The passive post-hook stream carries
  `action_id: 3 (Observed)` / `disposition_id: 17 (Logged)`; deny/modify mappings
  (`action_id` 2/4) wait on the cpex-core decision event (WS-A / P1).
- **Predecessor binding fixed (review §4-B):** `entry_hash` is now SHA-256 over the JCS
  canonical bytes of `{"chain_uid", "event", "prev_entry_hash"}` — the predecessor hash
  and chain id are part of the hashed input, so chain order is cryptographically bound
  and records can't be spliced across chains. The signer consumes the same binding
  bytes, committing any future DSSE signature to the record's chain position.

**Review corrections applied 2026-07-06** (from Teryl Taylor's review of the mapping):

- **C6 — prompt hooks now actually fire.** Earlier revisions registered on
  `cmf.prompt_post_fetch`, which the Rust CMF/APL runtime never dispatches — prompt events
  were silently dropped. Registration moved to `cmf.prompt_pre/post_invoke` (see the
  hook-name note above).
- **C1 — `correlation_uid` now correlates.** It mirrors the run id
  (`AgentExtension.conversation_id`), the same value on every event of a run; the per-call
  `tool_call_id` moved to `api.request.uid`.
- **C2 caveat — canonicalization implemented.** Events are JCS-style canonically serialized
  (sorted keys; set-derived arrays sorted at build time), so an independent verifier can
  recompute the `entry_hash` chain from the emitted JSON. See below.

Honest inventory of what's solid vs. open:

- **Solid + tested:** plugin/factory/hook structure (modeled on `audit-logger`), the OCSF
  event builder, the hash-chain logic, the gap-field mapping (`stop_reason`, `mcp`,
  `framework`, monotonic labels, workload identity), and the mapped objects (`ai_agent`,
  `delegation`, `message_context`). See the test module in `src/emitter.rs` and the runnable
  `examples/emit_sample.rs` / `SAMPLE-OUTPUT.md`.
- **RESOLVED 2026-07-20 (was: needs a standards call):** `ai_operation` is an OCSF
  **profile**, not a class — the host class is now **API Activity (6003)**, agreed on the
  2026-07-18 thread (matching AOS's host-class choice and AI Identity's production
  gateway). Remaining conformance caveat: the `emits_required_ocsf_base_fields` test
  checks structural conformance only, **not** full schema validation — validating against
  the published OCSF schema in CI is the open WS-E item.
- **Stub:** `sign::DsseSigner` returns `None` (chained-but-unsigned) until wired to AI
  Identity's existing DSSE/key machinery (the gateway's `this_workload` identity is the
  natural signer). This is the remaining gate on the *identity* half of the
  "verifies offline" claim; the *integrity* half (recomputable hash chain) is delivered.
- **Canonicalization (review C2 caveat — FIXED 2026-07-06):** `entry_hash` and the signer
  now consume `sign::canonical_bytes`, an explicit JCS-style serializer (sorted keys,
  compact output, independent of serde_json feature flags). Set-derived arrays —
  `cmf.security.labels`, `actor.roles`, `actor.user.groups`, previously randomized
  `HashSet`/`MonotonicSet` iteration order — are sorted at build time in `ocsf.rs`, so the
  same logical event always canonicalizes to the same bytes and an independent verifier
  recomputing `entry_hash` gets our value. Covered by the `canonical_form_is_sorted_and_compact`
  and `set_derived_arrays_are_sorted_for_canonical_hashing` tests.

## Building

```bash
# Cargo.toml defaults to a local cpex checkout (recommended while the
# API moves). Clone contextforge-org/cpex next to the AI-Identity repo:
#   git clone https://github.com/contextforge-org/cpex ../../../cpex
#
# `dev` is the public default and carries crates/cpex-core. The crate is
# verified green against BOTH baselines: feat/hil_apl `ad666ba` (2026-07-06,
# not a public branch) and public dev `baa9e17` (2026-07-27) — build, all
# 13 tests, and the example pass on each.
#
# To build without a local checkout, swap the dep for the git form pinned
# to a rev (see the comment in Cargo.toml).
cargo build
cargo test
```
