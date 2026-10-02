## What

Adds `reference/plugins/ocsf-audit`, an audit sink that emits each decision
the engine finalizes as an OCSF API Activity event (class 6003, `ai_operation`
and `security_control` profiles), optionally wrapped in a hash-chained,
DSSE-signed attestation (`record_integrity`) that a verifier checks offline
with the public key. It consumes the audit seam from #84 as any sink does:
`AuditHandler::handle` with the finalized `DecisionLog`, including the keyed
content provenance digests, the step vocabulary and the stream stamps.

It joins `pii-scanner` and `audit-logger` as a reference plugin: a workspace
member, built, linted and tested here, `publish = false`, not part of the
builtins umbrella. The manifest says why.

## Shape of the change

Two commits, so the port stays reviewable against its source:

1. `chore(audit): import the OCSF audit sink from AI-Identity`. A verbatim
   copy of `integrations/cpex-ocsf-audit` at Levaj2000/AI-Identity
   `395d64ed8bea695896af1557e530b0065145f593`, placed at
   `reference/plugins/ocsf-audit`. Not yet a workspace member.
2. `feat(audit): add the OCSF audit sink as a reference plugin`. The
   adaptation to this tree: workspace member and workspace dependencies,
   the lint set, edition 2024, file headers and the comment convention,
   plus the README layout note and a second sink block in the auditing
   guide.

The diff of the second commit is the whole port. Nothing in it changes a
hashed byte: the three `SAMPLE-OUTPUT*.md` files next to the crate are the
AID-EMIT-1 conformance vectors, and `emit_sample`, `decision_sink_demo` and
`provenance_demo` reproduce them byte for byte on this tree.

## What the adaptation changed

- **One host.** The source crate selects its engine with a Cargo feature
  (`cpex` or `ppe`) and reaches every engine type through a `host` alias
  module with four shims. Here it depends on `praxis-policy-core` alone, so
  the feature pair, the module and the shims are gone: the denying-step
  violation is read from `PluginAction::Denied` / `DenyIgnored` directly
  and the output digest from `DecisionLog::output_hash`. That drops the
  payload parameter from `ocsf::apply_decision`, which only the removed
  cpex path used.
- **Dependencies from the workspace table.** `p256` joins the table with
  `ecdsa`, `pem` and `pkcs8` (RustCrypto, Apache-2.0 OR MIT; RFC 6979
  signatures, which is what keeps the signed vectors reproducible).
  `base64` follows the major the builtins declare. `sha2` and the rest
  were already there. `cargo deny check` passes; the new duplicate
  versions (`der`, `spki`, `pkcs8`, `signature`, `pem-rfc7468`) are the
  RustCrypto 0.14 line beside the 0.13 line already in the lock, and
  `bans.multiple-versions` is `warn`.
- **Lints.** No `unwrap`, `expect` or `Value` indexing in library code:
  the canonicalizer uses `Display`, the chain state recovers a poisoned
  lock, and attestation members are inserted through the map. Tests and
  examples carry the same scoped allows as the existing reference
  plugins. Every public item is documented.
- **Edition 2024.** `provenance_demo` resolved its demo keys through the
  `env` secret backend with `std::env::set_var`, which is unsafe in this
  edition and the workspace forbids unsafe. It now writes the two keys to
  a scratch directory and resolves them through the `file` backend. Same
  bytes, same digests, same vector.
- **Comments explain the code, not its history.** The source carries its
  review and revision history in comments; those are restated as the
  constraint they describe or dropped. The OCSF schema gap
  (ocsf-schema#1709) stays, since it says why the signature bytes ride in
  `unmapped`.
- `typos.toml` learns the W3C trace-context example span id the vectors
  stamp (`00f067aa0ba9...`) and the COSE acronym.

## Verification

On the pinned toolchain (1.96.0, nightly rustfmt for the format check):

| Gate | Result |
|---|---|
| `make lint` (fmt check, clippy `-D warnings`, both feature sets) | clean |
| `make test` (both feature sets) | green; the crate's own suite is 35 tests |
| `make doc` (both feature sets) | clean |
| `make audit` (`cargo deny check`) | passes |
| `cargo check --workspace --all-targets`, with and without `--all-features` | clean |
| `typos` on the added and touched files | clean |
| `markdownlint` on the added and touched Markdown | clean (one pre-existing MD001 in `auditing.md`, untouched) |
| `emit_sample`, `decision_sink_demo`, `provenance_demo` | byte-identical to their vectors |
| `panic_drive` | the driven panic lands on `gw-1:decision` at `stream_seq` 0 with `status_code` `plugin_panic` |

## Review pointers

- `src/ocsf.rs` is the mapping. Against the import commit, its diff is the
  host-shim removal, let-chain collapses, headers and comments. The
  vectors are the proof that the mapping did not move.
- `src/sign.rs` is the verifier rule as running code: `signing_input`,
  `fingerprint_value`, `dsse_pae`. The README's "Verifying a record
  offline" section states the same rule in four steps.
- `docs/content/auditing.md` gains a second sink block under "Turning it
  on". The README layout note now says three reference plugins.

## Open points for the reviewers

- **History.** This PR is a squash copy with the source commit recorded
  in the import message. If you prefer the convention in
  `docs/dev/port-provenance.md` (filter-repo import with history, merged
  with unrelated histories), the same adaptation commit applies on top of
  that import unchanged; say so and I will land it that way.
- **`base64`.** Declared at the builtins' major. If you would rather it
  sat in the workspace table, that is a one-line move.
- **demos.** The README layout note says the demo registers the first two
  reference plugins; registering this one there is a follow-up in that
  repository, not this PR.
