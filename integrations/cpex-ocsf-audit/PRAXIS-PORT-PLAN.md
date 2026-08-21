# Praxis port plan — cpex-plugin-ocsf-audit

**Date:** 2026-08-21
**Status:** planning — the port has not run yet; this documents what will be
verified when it does.

Upstream intends to move the CPEX audit seam into **praxis** (the Rust policy
engine, "PPE"), tracked upstream as the praxis audit-seam issue (#11) and the
OCSF integration issue (#12). This crate was the first out-of-tree consumer
verified against the seam on cpex (PR #166 — see `SEAM-PORT-RESULTS.md`), and
the plan is to repeat that role against praxis: same crate, same protocol,
results reported upstream.

## Sequencing rule

**cpex#166 stays the canonical seam until the praxis seam issue (#11) lands.**
Confirmed with the cpex maintainer, 2026-08-21. Until then:

- All new mapping work in this crate targets cpex (`feat/audit-seam`), as
  today.
- Nothing here grows a praxis-only dependency or a compatibility shim early.
  The whole point of the guinea-pig role is measuring the port cost honestly —
  pre-adapting would corrupt the measurement.

## What must survive the port (acceptance criteria)

These are the seam behaviors this crate — and the evidence story built on it —
depends on. Each is already covered by a test against the cpex seam; the port
run re-executes all of them.

1. **The executor step vocabulary keeps its distinctions.**
   `deny_ignored` must stay distinct from `allow`, and `aborted` distinct from
   `error`. The suppressed-deny record ("a policy fired and was overridden")
   is the record SOC analysts actually ask for; collapsing it into a plain
   allow makes the one question the audit stream exists to answer
   unanswerable. Covered by the `deny_ignored` / `aborted` rendering tests.

2. **Stream stamps and the per-request id keep riding every record — inside
   the hashed bytes.** The `(epoch, stream_id, stream_seq, emission_seq)`
   completeness/ordering stamps, and `RequestExtension.request_id` at
   `unmapped."cmf.request.request_id"` — the join key signed draw receipts
   reconcile against (`receipt.correlation_id == event.unmapped."cmf.request.request_id"`,
   see #480). Both must remain part of the fingerprinted bytes so ordering
   and the join are tamper-evident, not advisory.

3. **The decision vocabulary arrives intact.** `Allowed` / `ModifiedPayload` /
   `ModifiedExtensions` / `DenyIgnored` / `Aborted` / `Error`, terminal
   verdicts, and `plugin_panic` distinguishable by code at
   `status_code`/`status_detail`.

4. **The registration contract holds.** No `hooks:` listed → the plugin
   auto-attaches as a decision-audit sink (`AuditHandler`) and sees denials;
   a hook-listed instance stays a post-hook observer and never double-emits.

5. **The opt-in guarantee holds for a real out-of-tree consumer.** The seam
   is additive: an existing consumer builds and passes with zero source
   changes and no behavior change without explicit configuration. This is the
   claim the cpex#166 run proved; the praxis run should prove it transfers.

## Re-verification protocol (the guinea-pig re-run)

Same protocol as `SEAM-PORT-RESULTS.md`, retargeted:

1. Fetch the praxis seam branch (issue #11's implementation head) next to
   this repo; pin the exact commit and toolchain in the results.
2. Swap the `cpex-core` dependency in `Cargo.toml` for its praxis equivalent.
   This is the **only** expected change — dependency wiring, not `src/`.
   Any required change under `src/` is a finding to report upstream, not
   something to silently absorb.
3. `cargo check --all-targets` and the full test suite (33 tests as of #480),
   plus both runnable examples (`emit_sample`, `decision_sink_demo`).
4. Record results as `PRAXIS-PORT-RESULTS.md` in this directory: exact head,
   toolchain, test counts, new transitive dependencies, and the "anything
   that doesn't match intent" list — the same report shape upstream found
   useful last time. Commit the `Cargo.lock` used.

## Demo on praxis

Once the port verifies green, the existing demos are the showable artifact —
no new material needed:

- `decision_sink_demo` — five deterministic decision records: clean allow,
  allow-after-modification, a denial with the violation surfaced (the record
  a post-hook observer structurally cannot produce), the suppressed-deny
  case (`deny_ignored: true` + an `aborted` step), and the delegated-mandate
  record carrying the draw-receipt join key. Committed output:
  `SAMPLE-OUTPUT-DECISIONS.md`.
- `emit_sample` — the dispatch half: attestation chain + DSSE signing with
  the offline-verification lines printed (`// verify`).

Re-running both on praxis and committing the praxis-produced output gives a
side-by-side with the cpex output — ideally byte-identical modulo the engine
name — which *is* the portability demo.

## Open items that carry across the port

- `AuditHandler::on_effect` — effect-lifecycle events want a richer OCSF
  class than 6003 (e.g. Authentication for a token mint).
- OCSF schema validation in CI (the open WS-E item) — structural conformance
  is tested; validation against the published schema is not.
- Token identifiers on CMF's `DelegationExtension` — the upstream ask noted
  in #480, unchanged by the engine move.
