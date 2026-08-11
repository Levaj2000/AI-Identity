# Draft response for ocsf-schema#1724 — paste as Jeff

> **Posting notes:** paste the body below verbatim as a comment on
> [ocsf/ocsf-schema#1724](https://github.com/ocsf/ocsf-schema/issues/1724).
> The sample link points at `main` — post **after** the supporting-sample PR
> merges, or swap in the PR-branch URL. Personal-voice comment, no company
> boilerplate; it names our production numbers, which are public via the
> reference bundle.

---

Strong +1 to this, and especially to the decision to apply `record_integrity`
per emission rather than inventing class-specific chaining. Some supporting
evidence from the producing side: we ([AI Identity](https://www.ai-identity.co))
run that profile in production today on a different class — API Activity 6003
under `ai_operation`, one event per gateway decision — as merged in 1.9 via
#1661. Current public reference export: a 236-event org chain, every
`prev_event` link verified, per-event ECDSA signatures checkable against a
public JWKS. Nothing in the profile turned out to be activity-specific, so I'd
expect it to sit on a Discovery inventory class with zero schema changes.
Practitioner notes that transfer directly to your per-emission design:

- **`metadata.uid` on every emission** — `prev_event.uid` is required, and it
  resolves against the predecessor's `metadata.uid`. Worth stating as a class
  requirement so producers don't discover it at verify time.
- **Genesis emissions should omit `prev_event`**, not carry a sentinel. We
  shipped a `"GENESIS"` string inside a `fingerprint.value` once; it's an
  anti-pattern (a fingerprint value that isn't a hash), and spec text warning
  about it would save others the round trip.
- **The `fingerprint` siblings are the honesty mechanism** — if a producer's
  canonicalization isn't RFC 8785, `serialization_id` 99 + the sibling naming
  the scheme beats claiming JCS; same for keyed constructions vs plain hashes.
- Signature bytes and key id still have no schema home (#1709) — that gap
  applies to this class identically, so records that actually sign will ride
  `unmapped` for those two fields in the meantime.

On your two questions for maintainers, from where we sit:

- **Discovery looks right.** The `config_state` / `device_config_state_change`
  pair is useful precedent — and suggests handling change-triggered
  re-emission as an **activity** on this one class (Log / Collect / Change)
  rather than a separate change class.
- **New class over extending existing inventory classes.** The
  declared/executed *pairing* is the core semantic and has no seat in the
  device/software-shaped inventory classes; the emission-timing contract
  (record **before** a newly introduced dependency executes) is a guarantee a
  retrofitted class can't credibly impose; and the identity spine already
  exists — `ai_agent` (`uid`, `instance_uid`, `version`, `charter`,
  `ai_model`) composes cleanly, so the class mostly assembles merged objects.

Emitting declared + executed in one event is, I think, the strongest design
choice here, and worth defending if it gets challenged: producer-computed
divergence would place the verdict inside the component whose compromise is
the threat model. Your Sleeper-Agents citation cuts the same way — if the
artifact's behavior can't be trusted, a divergence verdict computed next to
it can't either. Emitting both sides raw keeps the producer a witness rather
than a judge.

To make that concrete we built a worked sample — three chained events for one
agent instance, `record_integrity` applied per emission in the merged 1.9
shape, verifiable end-to-end with stdlib-only python3 (every digest has a
named preimage; the verifier recomputes fingerprints and linkage):

**https://github.com/levaj2000/ai-identity/tree/main/docs/cosai-ws4-ocsf-mapping/trust-base-inventory-sample**

1. **Session-start baseline** (Collect) — declared and executed agree; genesis, no `prev_event`.
2. **Mid-session MCP `tools/list` refresh** (Change) — emitted before any refreshed tool serves a call; declared toolset now exceeds the enforced allowlist. A *benign* divergence — policy working — but only a consumer holding both sides can tell.
3. **Adapter initialization mid-task** (Change) — registry-declared digest ≠ digest of the bytes actually mapped, emitted after load but **before the adapter's first inference**. Your admission-control timing argument made concrete: a PDP subscribed to the stream denies before execution; the same record is forensics afterward.

Suggestions the sample surfaced, offered for the eventual PR:

1. **Content digests as `fingerprint` objects** — the same object the
   attestations use, so one verifier vocabulary covers content digests and
   chain hashes.
2. **Hosted-model honesty** — an API-served model has no local weights to
   hash; the pinned `ai_model` (`ai_provider`/`name`/`version`) tuple *is*
   the trust-base element there. Digests belong exactly where bytes load
   locally (adapters, tool schemas, policy bundles, charter). Spec text
   should bless the tuple form so producers don't invent digests.
3. **Credentials as references + scopes only, never material** — implied by
   the issue; worth making normative.
4. **Scope `chain_uid` to the agent instance** (`ai_agent.instance_uid`).
   Then a trust-base change that executed without a chained emission is a
   *gap in the chain* — structurally checkable, which is the detection
   primitive this class exists for.
5. Keeping TEE/workload attestation as a referenced non-goal is correct and
   worth holding the line on — *is the environment trustworthy*, *is the
   record intact*, and *is the loaded configuration the declared
   configuration* are three different questions, and this class is cleanly
   the third.

Happy to help carry this: co-drafting the class PR for 1.10, contributing the
sample as example events, and bringing the production `record_integrity`
evidence to a WG session if useful.
