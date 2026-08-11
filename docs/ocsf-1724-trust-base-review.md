# Review — ocsf-schema#1724: Agent trust-base inventory (Discovery), record_integrity per emission

**Issue:** [ocsf/ocsf-schema#1724](https://github.com/ocsf/ocsf-schema/issues/1724)
· **Author:** @rabbidave (Dave, PayPal) · **Filed:** 2026-08-11 · **Targets:** OCSF v1.10.0
**Our stake:** the issue's chain-of-custody mechanism is the `record_integrity`
profile we landed in OCSF 1.9 (#1661) and run in production. This review backs the
proposal with that production experience.
**Supporting artifacts:** worked sample bundle in
`docs/cosai-ws4-ocsf-mapping/trust-base-inventory-sample/`; paste-ready response in
`docs/ocsf-1724-draft-issue-comment.md`.

---

## What Dave proposes

A new Discovery-category class that snapshots an agent's **trust base** — everything
that determines what actually executes — at well-defined moments:

1. **Declared configuration:** agent identity (`ai_agent`: uid, instance_uid,
   version, charter), model via `ai_model`, adapters, tool/schema sources, policy
   bundles — each element as a content digest.
2. **Executed parameters:** the enforced tool allowlist, applied sampling
   parameters, tools actually invoked, credentials accessible to the process.

Both sides ride in **one event** so consumers compute divergence themselves.
Chain-of-custody comes from applying the existing `record_integrity` profile per
emission (`chain_uid`, `prev_event`, fingerprints covering `prev_event`), with
re-emission timed **before** a newly introduced dependency executes — admission
control, not just forensics. Non-goals: behavioral malware detection,
floating-point runtime state, replacing hardware attestation (reference TEE
quotes instead). Motivated by the Sleeper Agents result (Hubinger et al.):
compromised artifacts survive safety training and may be behaviorally
undetectable, so *which bytes loaded, when* must be a recorded fact.

## Assessment: sound, and complementary to our work

**The gap is real and we feel it from the other side.** Our production export
records what an agent *did* (API Activity 6003, `ai_operation` +
`record_integrity`) but not what the agent *was* — the emitter's own gap list
(`docs/cosai-ws4-ocsf-mapping/ocsf-issues-draft-with-teryl.md`, Issues 1/2/5)
keeps hitting facets of exactly this: tool schemas as injected, framework
context, workload identity binding. Dave's class gives those a coherent home on
the inventory side rather than stuffing them per-activity-event.

**Reusing `record_integrity` instead of inventing chaining is the right call —
and it demonstrably works.** The profile is domain-agnostic by design; we apply
it per emission on a different class (6003) in production: 236-event org chain,
every link verified, per-event ECDSA signatures against a public JWKS. Nothing
about the profile is activity-specific. Practitioner notes that transfer
directly (all learned the hard way, all in the draft comment):

- Every emission needs `metadata.uid`, or `prev_event.uid` (required) cannot
  resolve.
- The genesis emission must **omit** `prev_event`, not carry a sentinel — a
  sentinel string inside a `fingerprint.value` is an anti-pattern we shipped
  once and documented as such.
- The `fingerprint` `algorithm`/`serialization` siblings exist for honesty —
  keyed HMAC is not SHA-256 (`algorithm_id` 99 + sibling), producer
  serialization that isn't JCS shouldn't claim JCS.
- `at_least_one(fingerprint, signatures)` lets an unkeyed-fingerprint producer
  still conform; signature bytes/key-id still lack a schema home (#1709) — that
  gap applies to this class identically.

**Declared + executed in one event is the strongest design choice in the
issue.** The alternative — producer-computed divergence — puts the divergence
verdict inside the component whose compromise is the threat model. Emitting
both sides raw keeps the producer a witness, not a judge; the Sleeper-Agents
argument cuts the same way (don't trust the artifact's behavior; also don't
trust a verdict computed next to it). Our sample shows a consumer catching
both a benign divergence (declared toolset > enforced allowlist: policy
working) and a malignant one (registry digest ≠ loaded digest) from single
events, with `severity_id` 1 and no judgment embedded.

**Admission-control timing is the differentiator.** Emission *before* a newly
introduced dependency executes turns the same record into a prevention
primitive (a PDP can deny on unrecognized digest) and a forensic one. This
matches our gateway's fail-close posture, and it is what separates the class
from "yet another inventory log."

**Non-goals are correctly scoped.** Keeping TEE/workload attestation out
(reference, don't replace) matches the precision trap we documented with
Teryl on Issue 5: *is the environment trustworthy* (workload attestation) vs
*is the record intact* (record integrity) vs — now — *is the loaded
configuration the declared configuration* (this class). Three different
questions; conflating them was the failure mode we were most worried about,
and the issue avoids it cleanly.

## On his two maintainer questions

**Discovery is the right category.** Precedents line up: `inventory_info`,
`device_config_state`, and notably the `config_state` / `device_config_state_change`
split, which suggests activity semantics for this class too (baseline
Collect vs change-triggered emission — our sample proposes `Change` as an
activity, not a separate class).

**New class over extending existing inventory classes.** Three reasons:
(a) existing inventory classes are device/software-shaped and have no seat for
the declared/executed *pairing*, which is the core semantic, not an add-on;
(b) the emission-timing contract (before first execution of a new dependency)
is a semantic guarantee a retrofitted class can't credibly impose;
(c) the identity spine already exists — `ai_agent` (uid, instance_uid,
version, charter, ai_model) merged, so the new class composes existing objects
rather than widening old classes.

## Suggestions to raise (constructive, in the comment)

1. **Digests as `fingerprint` objects** — same object the attestations use;
   one verifier vocabulary across content digests and chain hashes.
2. **Hosted-model honesty** — API-served models have no weights bytes to
   hash; the pinned (`ai_provider`, `name`, `version`) tuple is the trust-base
   element. Don't force fake digests; spec text should say so.
3. **Credentials as references + scopes, never material** — the issue implies
   it; the spec text must require it.
4. **`chain_uid` scoped per agent instance** — makes a chain *gap* the
   detection primitive for "config changed without emission," structurally
   checkable.
5. **Activity enum** — Log / Collect / Change rather than a change-class
   fork.

## Files

| Artifact | Path |
|---|---|
| This review | `docs/ocsf-1724-trust-base-review.md` |
| Paste-ready issue response | `docs/ocsf-1724-draft-issue-comment.md` |
| Worked sample (3 chained events + generator/verifier) | `docs/cosai-ws4-ocsf-mapping/trust-base-inventory-sample/` |

Next step after the comment lands: if Dave wants co-authorship on the class
PR, the sample's attribute sketch is the starting point, and the production
reference bundle is the evidence that the `record_integrity` half is already
proven at class #2.
