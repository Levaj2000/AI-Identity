# Praxis in-tree plan: `praxis-policy-plugin-ocsf-audit` under `reference/plugins/`

**Date:** 2026-09-08
**Status:** plan. Gated on praxis-proxy/policy PR #84 merging to `main`.
Nothing here starts before that; the sequencing rule in
`PRAXIS-PORT-PLAN.md` still holds.
**Tracks:** praxis-proxy/policy issue #12 (feat: tamper evident OCSF
auditing, milestone 0.3.0).

## Decisions recorded

Settled with Teryl on Slack, 2026-09-08, after he talked to Fred:

- **Placement:** `reference/plugins/ocsf-audit`, next to `audit-logger` and
  `pii-scanner`. Workspace member, `publish = false`, "not supported" in the
  manifest comment, the same shape as `audit-logger`. Move to
  `builtins/plugins/` after feedback; that move is a later PR and not
  planned here.
- **Source of the port:** AI-Identity `main`, this directory, v0.0.3, 34
  tests, AID-EMIT-1 1.1.0. Not cpex#128. Teryl will swap the link on #12.
- **Mechanics:** Jeff opens the PR into praxis the day #84 merges, against
  the head Teryl names. Teryl did not object to the default, so it stands.

## Gates before the PR opens

1. PR #84 is merged to `main`. Confirm with `git merge-base --is-ancestor`
   of the #84 head against `origin/main`; do not stack on the draft.
2. Teryl has named the head to measure against. Default to `main` at the
   merge commit if he does not.
3. The AI-Identity crate is on that head under `--features ppe` with 34
   green and `emit_sample` byte-identical. That is the baseline the in-tree
   copy is measured against.

**Status 2026-09-09.** Fred requested changes on #84 with five findings.
Two touch the sink seam this crate consumes; three are inside the effect
log and the delegator, which the crate does not observe (`on_effect` is
the default no-op).

- *Emit once after routing and assertions.* Today `emit_audit` runs inside
  `execute` and `apply_assertions` runs on its result (`engine.rs`), so a
  sink can record allow for a request an assertion then denies, and a
  route-resolution failure returns a denial with no record at all. The
  fix is the order AID-EMIT-1 assumes, the record is the verdict the
  caller got; it changes nothing in this crate. Route denials gaining a
  record adds records to the decision stream and keeps it dense.
- *Sinks get a filtered view of `Extensions`.* `emit_audit` and the effect
  sink pass the unfiltered extensions, transport and effect slot included.
  This crate reads only the typed fields (`request`, `mcp`, `security`,
  `agent`, `completion`, `delegation`), so a filtered view costs nothing,
  unless the view arrives as a new type rather than `&Extensions` with the
  slots detached, in which case `AuditHandler::handle` changes shape and
  the `ppe` build of this crate follows it.

Either way, Teryl's next push moves the head: re-pin, re-run the bar, and
re-read the sink signature before gate 3 is called met.

## PPE rules the copy must satisfy

Read from `praxis-proxy/policy` at `3e7734e`, dependencies re-read at
`499ee91`: `CONTRIBUTING.md`, `AGENTS.md`, `Cargo.toml` (workspace lints),
`clippy.toml`, `.markdownlint.yaml`, `deny.toml`, `docs/port-provenance.md`.
The auditing guide moved from `docs/auditing.md` to `docs/content/auditing.md`
when #84 took the #82 docs reorganisation (`a1e8621`, `499ee91`).

- **Commits.** Human-authored, `Signed-off-by` the human, no AI co-author or
  session trailers (`AGENTS.md`, first paragraph). Same rule as this repo's
  CLAUDE.md for CoSAI and OCSF. The commit step is
  `git commit -s --author='Jeff Leva <120221487+Levaj2000@users.noreply.github.com>'`.
- **File headers.** Every source file starts with exactly two lines,
  `// SPDX-License-Identifier: Apache-2.0` and
  `// Copyright (c) 2026 Praxis Contributors`, `#` in TOML, YAML and shell.
  No `Authors:` line, no path line. This crate's files carry neither header
  today and `demo/run-demo.sh` carries a path line; both change.
- **Comments explain the code, not the work.** No progress notes, no
  history ("merged #1661 semantics", "fixed 2026-07-20", "PR #166 audit
  path"), no milestone names. 93 comment lines in `src/` cite a PR number,
  a date or "merged"; each is restated in the present tense as the
  constraint it describes, or deleted. The OCSF schema gaps
  (ocsf-schema#1709) stay as constraints with the issue link, since they
  tell a reader why a field is where it is.
- **Toolchain.** Rust 1.96.0 pinned in `rust-toolchain.toml`, edition 2024
  inherited from `[workspace.package]`. This crate is edition 2021; expect
  the 2024 changes (`if let` temporary scopes, RPIT capture, `gen` as a
  keyword) to surface a handful of edits.
- **Lints.** `[lints] workspace = true` is mandatory and the workspace set
  denies, among others: `missing_docs`, `unreachable_pub`, `dead_code`,
  `unexpected_cfgs`, `clippy::unwrap_used`, `clippy::panic`,
  `clippy::print_stdout`, `clippy::missing_assert_message`,
  `clippy::doc_markdown`, `clippy::disallowed_methods` (no
  `std::thread::sleep`). Sizing against this crate today:

  | Lint | Sites | Fix |
  |---|---|---|
  | `missing_assert_message` | 154 in tests, 5 in `panic_drive` | add a message to every `assert*!` |
  | `unwrap_used` | 49 in `emitter.rs`, 13 in `sign.rs`, 19 in examples | `#[allow(clippy::unwrap_used, reason = "tests")]` on test modules, as `identity-jwt` does; examples handle errors or carry the same allow with a reason |
  | `print_stdout` | 9 in `emit_sample`, 4 in `decision_sink_demo`, 1 each in `emitter.rs` and `panic_drive` | write through a locked `std::io::stdout()` with `writeln!`, or allow with reason on the example |
  | `panic` | 1 in `sign.rs`, 1 in `demo_stream`, 2 in `panic_drive` | `panic_drive` panics on purpose, allow with reason; the other two become errors |
  | `disallowed_methods` | `demo_stream.rs` `std::thread::sleep` | `tokio::time::sleep` or drop the hold |
  | `missing_docs` / `unreachable_pub` | 41 `pub` items in `src/` | doc every public item; anything without an in-tree caller becomes `pub(crate)` or is deleted (`dead_code` is deny) |
  | `doc_markdown` | doc comments naming OCSF, DSSE, PAE, ECDSA, AID-EMIT-1 | backticks, or add them to `doc-valid-idents` in `clippy.toml` |
  | `unexpected_cfgs` | 26 `cfg(feature = ...)` sites | all removed with the host feature pair (below) |

  Clippy runs `--all-targets`, so tests and examples are linted at the same
  bar as the library.
- **Dependencies.** `deny.toml` has `allow-git = []`: no git dependencies,
  so the pinned `praxis-policy-core` git dep becomes
  `praxis-policy-core = { workspace = true }`. `serde`, `serde_json`,
  `chrono`, `async-trait`, `tracing`, `tokio` and, since `ef20d8f`, `sha2`
  are in `[workspace.dependencies]` and are taken with `{ workspace = true }`.
  `p256` is the one genuinely new dependency in the tree and joins the
  table in this PR with `ecdsa`, `pem`, `pkcs8`. All are Apache-2.0 OR MIT,
  inside the `deny.toml` allow-list. `make audit` (`cargo deny check`) is a
  CI gate.

  How the other two resolved, read from the manifests at `499ee91`:

  - `sha2`. praxis-bot flagged four crates each declaring `sha2 = "0.11"`
    directly on #84 (2026-09-09). Teryl answered with `ef20d8f`, "make sha
    0.11 a workspace dependency": `sha2 = "0.11"` is in the table and the
    four crates take it from there. The port does the same and adds
    nothing.
  - `base64`. This crate was on `0.23`; `identity-jwt`, `delegator-oauth`
    and `elicitation-ciba` declare `0.22` directly. Teryl settled it on the
    same day: the tree stays on `0.22` because `jsonwebtoken` 11, which
    `identity-jwt` depends on, requires base64 `0.22`, so `0.23` would put
    two majors in the build (verified against the PPE lock: `jsonwebtoken
    11.0.0` lists `base64 0.22.1`). This crate is pinned down to `0.22`
    ahead of the port. The cost was the manifest line, confirmed by the
    build: base64 is reached only through `Engine::encode` and
    `Engine::decode` on `general_purpose::STANDARD` (`src/sign.rs`,
    `src/emitter.rs`), 34 tests green on both hosts, `emit_sample` and
    `decision_sink_demo` byte-identical. `base64` is not in the workspace
    table at `499ee91`; the port declares `base64 = "0.22"` directly, the
    way the three builtins do, unless Teryl prefers a table entry.

  On the version spec itself, follow the table and not the bot. The #84
  review also asked for a patch component (`sha2 = "0.11.0"`), and
  `ef20d8f` wrote `sha2 = "0.11"`, matching the rest of
  `[workspace.dependencies]`: `tokio = "1"`, `thiserror = "2"`,
  `hashbrown = "0.17"`, `serde_yaml = "0.9"`. Expect the same comment on
  this PR and answer it the same way.
- **Markdown.** 80-column prose, 120 in code blocks, tables exempt
  (MD013); every fence declares a language (MD040); no bare URLs (MD034);
  asterisk emphasis (MD049). Long prose lines today: `README.md` 89,
  `SAMPLE-OUTPUT.md` 44, `SAMPLE-OUTPUT-DECISIONS.md` 26. `lychee` checks
  links, `typos` checks spelling.
- **CI.** `make lint` (nightly rustfmt check, clippy `-D warnings`),
  `make test` (`--workspace` and `--workspace --all-features`), `make doc`
  (rustdoc `-D warnings`, so intra-doc links must resolve after the
  rename), `make audit`, and an MSRV job running `cargo check --workspace
  --all-targets` on 1.96.0. `make ci` is `lint` plus `test`; run all five
  before pushing.

## Target layout

```text
reference/plugins/ocsf-audit/
  Cargo.toml          praxis-policy-plugin-ocsf-audit, publish = false
  README.md           mapping, wiring, status, conformance vectors
  SAMPLE-OUTPUT.md    AID-EMIT-1 section 12 vector, emit_sample
  SAMPLE-OUTPUT-DECISIONS.md   decision vector, PPE records only
  src/{lib,config,emitter,ocsf,sign,factory}.rs
  examples/{emit_sample,decision_sink_demo,demo_stream,panic_drive}.rs
```

Workspace edits in the same PR: add the path to `members` and
`default-members` in the root `Cargo.toml` under the existing reference
comment; add `p256` to `[workspace.dependencies]`;
`docs/content/auditing.md` "PPE ships one, `audit-logger`" becomes two, with a
`kind: audit/ocsf` YAML block after the `audit-logger` one; `README.md`
line 52 "two worked examples" becomes three. `kind` stays `audit/ocsf`.

Not carried: `demo/run-demo.sh` (the joint demo runner is cpex-coupled
through `CPEX_DIR` and the cpex#166 banner, and it belongs with the ledger
side of the demo, which lives here); `PRAXIS-PORT-PLAN.md`,
`PRAXIS-PORT-RESULTS.md`, `SEAM-PORT-RESULTS.md` (measurement records of
this repo); `Cargo.lock` (the workspace lock covers it).

## Source changes

1. **Drop the host feature pair.** The in-tree copy is PPE-only. Remove the
   `cpex` and `ppe` features, the `cpex-core` path dependency, and the
   `crate::host` alias module. Its four helpers collapse:
   `denied(v)` is `PluginAction::Denied(Box::new(v))`, `deny_ignored(v)`
   likewise, `is_deny_ignored` is a `matches!`, `step_violation` is the
   PPE match arm alone. Keep them as thin functions where they name the
   intent at the call site; inline where they do not. 26 `cfg` sites go,
   12 of them in `lib.rs`, 6 in `panic_drive.rs`.
2. **Rename.** `cpex_plugin_ocsf_audit` becomes
   `praxis_policy_plugin_ocsf_audit` in every `use` in the examples;
   `ENGINE` is a constant `"praxis-policy-core"` or is removed with its one
   log line.
3. **Config model.** `panic_drive` uses `engine_settings:` with
   `dispatch: hooks` declared, and sets `audit_epoch` in code through the
   PPE path only. The cpex `config_yaml` variant goes.
4. **Lint pass** per the table above. Mechanical but large; the
   assert-message pass alone touches 159 lines.
5. **Comment pass** per the CONTRIBUTING rule, 93 lines.
6. **Headers** on every file, `Cargo.toml` included.
7. **Edition 2024** compile fixes, whatever the compiler reports.

Nothing in this list changes a hashed byte. The acceptance check below is
what proves that.

## Acceptance

- `make lint`, `make test`, `make doc`, `make audit` clean on 1.96.0;
  `cargo check --workspace --all-targets` clean for the MSRV job.
- 34 tests green (28 `emitter.rs`, 6 `sign.rs`).
- `cargo run -p praxis-policy-plugin-ocsf-audit --example emit_sample`
  produces records byte-identical to `SAMPLE-OUTPUT.md` here, which is the
  AID-EMIT-1 section 12 conformance vector. Same for the PPE records in
  `SAMPLE-OUTPUT-DECISIONS.md` via `decision_sink_demo`.
- `panic_drive` lands the driven panic on `gw-1:decision` with the
  namespace read from YAML and `status_code` `plugin_panic`.
- Zero diff between the in-tree `src/ocsf.rs` mapping and this repo's,
  ignoring the host module removal, headers and comments. A mapping change
  is a spec change and does not ride along with a port.

## History: two ways to land it

`docs/port-provenance.md` records PPE's own convention: import with history
via `git-filter-repo` in a single pass with path renames, then merge with
unrelated histories allowed, so `git blame` reaches back to the source.
Two imports have been done that way.

- **Option A, history-preserving.** Filter this repo to
  `integrations/cpex-ocsf-audit/` renamed to `reference/plugins/ocsf-audit/`,
  merge into a branch off the post-#84 `main`, then land the source changes
  above as ordinary commits on top. Adds a "Third import" section to
  `docs/port-provenance.md` with the source commit as the anchor. Fits the
  documented convention; the PR is a merge of unrelated histories, which
  Teryl has accepted twice.
- **Option B, squash copy.** One commit adding the adapted tree. Simpler
  review; blame starts at the import.

Recommend A, and ask Teryl which he wants in the same message that names
the head. The source commit anchor is `main` here at the time of the
filter, recorded in the PR body.

## What stays in this repository

The dual-host crate here remains the conformance reference for AID-EMIT-1
until the in-tree crate ships in a PPE release. Until then CI keeps both
hosts. Once PPE carries the plugin on a tagged release, the options are to
drop the `ppe` feature here and point at the release, or to keep both and
diff the in-tree copy against this one on each PPE release. Decide when the
first PPE release with the plugin exists, not before.

## Effort

The earlier estimate of about an hour of cleanup covered the rename and the
host module. PPE's lint bar adds the assert-message, unwrap, docs and
comment passes, roughly 300 lines of mechanical edits, plus the markdown
reflow. Plan a day, verified against the acceptance list, not an hour.

## Open questions for the PR thread

- *(Settled 2026-09-09.)* `base64` stays at `0.22` in the tree, held there
  by `jsonwebtoken` 11; this crate is pinned down to match. Still open is
  only whether the port declares it directly, as the three builtins do, or
  adds a workspace table entry.
- `doc-valid-idents` additions in `clippy.toml` for OCSF, DSSE, PAE, ECDSA,
  AID-EMIT-1, or backticks throughout; Teryl's preference.
- Whether the praxis `demos` repository, which registers the reference
  plugins as host plugins, should register this one in the same PR series.
- Where the AID-EMIT-1 spec is linked from the in-tree README: this repo's
  `docs/specs/aid-emit-1.md` pinned to a commit, since PPE has no spec
  directory for it.
