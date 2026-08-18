# Guinea-pig port results — cpex-ocsf-audit vs. the audit seam (cpex PR #166)

**Date:** 2026-08-18
**Plugin:** `cpex-plugin-ocsf-audit` v0.0.3 (this directory, unmodified)
**Against:** `contextforge-org/cpex` branch `feat/audit-seam`, PR #166 head
`386710a` (includes the 2026-08-18 hardening round `eda9821`, the h2 bump
`1660773`, and the clock-assumptions doc `82b92c3`)
**Toolchain:** rustc 1.96.1 (the repo's `rust-toolchain.toml` pin / MSRV)

This is the follow-through on the offer made on the PR thread (2026-08-14):
be the first outside consumer to port against the seam and report anything
that doesn't match intent.

## Results

| Check | Result |
|---|---|
| `cargo check --all-targets` (lib, tests, examples) | **Clean** — no errors, no warnings |
| `cargo test` | **21 passed, 0 failed** (emitter 14, sign 7, doc-tests 0) |

The plugin required **zero source changes** to build and pass its full suite
against the seam branch. Every behavior we assert — OCSF 6003 shaping,
`ai_operation` mapping, readOnlyHint→activity derivation, fingerprint
chaining/predecessor binding, JCS canonicalization, DSSE signing and offline
verification, observation-only handler contract — is intact.

## What this does and does not verify

**Verified:** the seam is additive for an existing CMF post-hook observer.
The PR's claim that "all changes are opt-in; no behavior changes without
explicit configuration" holds for a real out-of-tree consumer, not just the
in-tree `audit-logger`.

**Not yet exercised (next step of the port):** registering as a
decision-audit sink (`AuditHandler` / `DecisionLog`) and mapping the
finalized decision vocabulary — `Allowed` / `ModifiedPayload` /
`ModifiedExtensions` / `DenyIgnored` / `Aborted` / `Error`, terminal
verdicts, `plugin_panic` coding, and the `(epoch, stream_seq, emission_seq)`
stamps — into OCSF records (deny/modify records, action_id 2/4). That is the
WS-A / P1 work item already tracked in `src/lib.rs`; the vocabulary review
on the PR thread (2026-08-18) confirmed the contract carries everything the
mapping needs.

## Observations for upstream (the "anything that doesn't match intent" list)

1. **Nothing broke.** No API drift against `cpex-core` 0.2.2 on the seam
   branch; the port was a lockfile refresh, not a code change.
2. **New transitive dependencies:** `cpex-core` now pulls `futures` (serial
   panic containment via `catch_unwind`) and `sha2` (content provenance
   hashing). Both small and justified; embedders doing dependency review
   will want to know.
3. **MSRV is enforced in practice:** building against the branch under
   rustc 1.94 fails fast with a clear `requires rustc 1.96` error — good,
   the pin does its job (not a seam regression; noted for reproducibility).

## Reproducing

```sh
# clone cpex next to AI-Identity and fetch the PR head
git clone https://github.com/contextforge-org/cpex ../../../cpex
git -C ../../../cpex fetch origin pull/166/head:pr-166
git -C ../../../cpex checkout pr-166

# from this directory (rustup picks up cpex's 1.96 pin via override or default)
cargo check --all-targets && cargo test
```

The committed `Cargo.lock` in this directory records the exact resolution
used for this run.
