# Praxis port results — cpex-ocsf-audit vs. the PPE audit seam (praxis-proxy/policy PR #84)

**Date:** 2026-09-07
**Plugin:** `cpex-plugin-ocsf-audit` v0.0.3 (this directory), built with
`--no-default-features --features ppe`
**Against:** `praxis-proxy/policy` PR #84 ("feat(audit): decision and effect
auditing", closes praxis#11), head `20798ae` — five commits on top of `main`
`9ee972f` (v0.2.0). The PR is a **draft** at the time of this run.
**Toolchain:** rustc 1.96.1 (this crate's `rust-version` pin; PPE's own
`rust-toolchain.toml` says 1.96.0, its MSRV)
**Baseline it is compared with:** the same crate on cpex `feat/audit-seam`
`64c8eba` (the CI pin), run the same day on the same toolchain.

This is the re-run `PRAXIS-PORT-PLAN.md` describes: same crate, same protocol
as `SEAM-PORT-RESULTS.md`, retargeted at the praxis seam. The plan expected
the dependency swap to be the only change. It was not, and the reason is
recorded below as the first finding: **PPE is ahead of the cpex seam**, not
behind it.

## Results

| Check | cpex `64c8eba` | PPE PR #84 `20798ae` |
|---|---|---|
| `cargo check --locked --all-targets`, `RUSTFLAGS=-D warnings` | clean | clean |
| `cargo test --locked` | **33 passed, 0 failed** (emitter 27, sign 6) | **33 passed, 0 failed** |
| `cargo run --example emit_sample` | matches `SAMPLE-OUTPUT.md` | **byte-identical** to the cpex run |
| `cargo run --example decision_sink_demo` | matches `SAMPLE-OUTPUT-DECISIONS.md` | **byte-identical** to the cpex run |
| `cargo run --example panic_drive` (beat 06 through the engine) | deny, `plugin_panic`, `gw-1:decision`, host epoch, `stream_seq` 0 | identical after normalising `time`, span ids and the signature |

So the portability claim the plan set out to test holds: the OCSF record a
verifier sees does not depend on which engine produced it. The five
acceptance criteria in `PRAXIS-PORT-PLAN.md`:

1. **Step vocabulary distinctions** — intact. `deny_ignored` and `aborted`
   render as themselves; the `deny_ignored_never_reads_as_plain_allow` and
   `aborted_step_is_not_an_error` tests pass unchanged.
2. **Stream stamps and the request id inside the hashed bytes** — intact.
   `stream_stamps_are_inside_the_hashed_bytes` passes; `panic_drive` shows
   the executor's `(epoch, stream_id, stream_seq, emission_seq)` under
   `unmapped.cpex.stream` with the host namespace applied.
3. **Decision vocabulary** — intact, and richer (finding 1).
4. **Registration contract** — intact. No `hooks:` → `as_audit_handler()`
   returns the sink; a hook-listed instance stays a post-hook observer.
   PPE's own `audit-logger` reference plugin uses the identical contract.
5. **Opt-in guarantee** — holds in the sense that matters: nothing in the
   plugin's behaviour changed. The source did change, for the reasons below.

## Port cost

One dependency line plus 13 source sites, in three classes. Everything else
— the `AuditHandler` trait, `DecisionLog` and its accessors, the `Extensions`
and CMF types, `PluginFactory`/`PluginInstance`, `TypedHandlerAdapter`,
`parse_config` — has the same path and the same shape on both engines
(`praxis_policy_core::` for `cpex_core::`, module tree unchanged).

1. **`PluginAction::Denied` and `DenyIgnored` carry `Box<PluginViolation>` on
   PPE** (PR #84 commit `7da262d`, "decision provenance") and are unit
   variants on cpex. Three sites in `src/ocsf.rs` (two match arms and the
   flat `deny_ignored` flag) and the test/example fixtures that construct
   those steps. This is the better shape: on a suppressed deny no verdict
   names the violation, so the step is the only place the objection
   survives, and PPE's `audit-logger` renders it as a per-step `detail`.
   This crate now renders it as the step's `detail` on PPE (AID-EMIT-1
   1.1.0, §9.2; landed the same day as the port), and the decision vector
   in `SAMPLE-OUTPUT-DECISIONS.md` is generated on the PPE host with the
   cpex delta shown — records 3 and 4 differ by exactly that member.
2. **Host config model.** `plugin_settings:` is `engine_settings:` on PPE and
   the old key is rejected at load. PPE also defaults to
   `engine_settings.dispatch: policy`, under which a hook-listed plugin with
   a `priority:` is refused; the hook-dispatch model this crate's wiring
   assumes needs `dispatch: hooks` declared. Both are host config, not seam.
3. **Names.** `cpex_core` → `praxis_policy_core`; `manager::PluginManager` →
   `engine::PolicyEngine` (same `register_factory` / `load_config` /
   `initialize` / `invoke_named` / `shutdown` surface).

The crate now absorbs all three behind a `host` feature pair (`cpex`, the
default, and `ppe`) with one alias module, `crate::host`, so the source has a
single import root and the variant-shape difference lives in four helpers
(`host::denied`, `host::deny_ignored`, `host::is_deny_ignored`,
`host::step_violation`). The PPE
dependency is a git dep pinned to the PR head by full SHA, so a checkout
with only cpex beside it still resolves.

## Observations for upstream (the "anything that doesn't match intent" list)

1. **The documented `engine_settings` audit keys are rejected at load.**
   `ENGINE_SETTINGS_KEYS` in `crates/ppe-core/src/config.rs` lists
   `dispatch`, `plugin_timeout`, `short_circuit_on_deny` and
   `route_cache_max_entries` only, so `reject_unknown_document_keys` refuses
   every key `docs/auditing.md` introduces. `parse_config()` on the exact
   YAML block from the doc's "Turning it on" section, with
   `audit_stream_namespace: gw-1` added:

   ```
   configuration error: `engine_settings` has unknown keys `effect_log_path`, `effect_log_compaction_threshold`, `capture_content_provenance`, `audit_stream_namespace`; engine_settings accepts dispatch, plugin_timeout, short_circuit_on_deny, route_cache_max_entries
   ```

   The test that exists to catch this, `the_documented_auditing_config_loads`,
   passes because it calls `serde_yaml::from_str` directly and never goes
   through `parse_config`. Suggested fix: four `structural_key(..., KeyOwner::Core)`
   entries, and route that test through `parse_config`. Until it lands,
   `examples/panic_drive.rs` sets `audit_stream_namespace` in code on PPE
   (the epoch already is, on both hosts) rather than in the YAML.
2. **The seams have diverged, in PPE's favour** (finding 1 above). cpex#166
   and PR #84 no longer expose the same `PluginAction`. A consumer targeting
   both needs the shape split this crate now carries; a consumer targeting
   only one should target PPE.
3. **`plugin_settings:` is a load error, not a warning**, on PPE — the
   rename is enforced. Good for operators; worth a line in the PR
   description's breaking-changes list alongside the `Clone` removals.
4. **New transitive dependencies** on the PPE build: `http` (via
   `praxis-policy-orchestration`), plus the two praxis crates. Dropped
   relative to the cpex build: `generic-array`, `version_check`. Net package
   count in the lock: 113 → 112 for a PPE-only resolution; this crate's
   committed lock carries both hosts.
5. **Nothing else broke.** The seam is additive for this consumer on PPE
   exactly as it was on cpex: no behaviour changes without configuration.

## Reproducing

```sh
# cpex host (default): clone cpex beside AI-Identity at the CI pin
git clone https://github.com/contextforge-org/cpex ../../../cpex
git -C ../../../cpex checkout 64c8eba85fac28fa7e73b6c83d32aca7356ca23d

# both hosts, from this directory (rustup toolchain 1.96.1)
cargo +1.96.1 test --locked
cargo +1.96.1 test --locked --no-default-features --features ppe

# the vectors
cargo +1.96.1 run --locked --example emit_sample
cargo +1.96.1 run --locked --no-default-features --features ppe --example emit_sample
```

The PPE dependency needs no sibling checkout: Cargo fetches
`praxis-proxy/policy` at the pinned rev. The committed `Cargo.lock` records
the exact resolution for both hosts.
