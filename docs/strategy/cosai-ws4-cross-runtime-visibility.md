# Cross-Runtime Agent Visibility

**When an agent enters a runtime you don't control, how do you still see what it's doing?**

*Companion to the [WS4 Agent Identity & Governance Interop Map](cosai-ws4-interop-map.md) · prompted by the Trust Graph SIG discussion on 2026-07-16 · draft for the work-stream*

## The question

An agent starts in an instrumented environment — your gateway, your policies,
your telemetry. Then it crosses into another runtime: a hosted platform
(Perplexity, a partner's orchestrator, a SaaS agent host), where it keeps
acting. What visibility survives the crossing?

This conversation tends to circle, and the reason is that "visibility" blends
**three separable problems** with different owners, different standards, and —
critically — different limits on what is achievable at all.

## The three problems

| # | Problem | Question it answers | Interop-map layer | Where it's being solved |
|---|---|---|---|---|
| 1 | **Authority continuity** | Is the agent on the far side still the same principal, acting under the same grant, with the same limits? | 2 — Authority / delegation | ODIS (Passport), CMF `delegation.chain`, SPIFFE-anchored identity; mandates with scoped limits |
| 2 | **Correlation continuity** | When records from both sides exist, how do they join into one thread? | Cross-cutting plumbing | OpenTelemetry context propagation (W3C `traceparent` / baggage) |
| 3 | **Emission & evidence** | Do verifiable records of the far side's actions exist at all — and can two runtimes' records be stitched into one tamper-evident narrative? | 5 — Record / evidence | OCSF `record_integrity` profile ([ocsf-schema PR #1661](https://github.com/ocsf/ocsf-schema/pull/1661)) |

Before answering any "can we see into runtime X" question, it is worth asking
which of the three is actually meant. They have very different answers.

## The honest limit first

**You cannot instrument a runtime you do not control.** If the foreign runtime
emits nothing, no schema, trace header, or credential format fixes that.
Problem 3 splits accordingly:

- **Emission is an adoption problem, not a standards problem.** What standards
  *can* do is make cooperation cheap and uniform: a runtime that opts in emits
  OCSF events and the records are immediately joinable with everyone else's.
- **Evidence stitching is a standards problem** — and it now has a concrete
  answer (below).

## What is achievable unilaterally: boundary evidence

Even when the far side is dark, the crossing itself happens on your side of the
boundary, and it can be recorded with full fidelity:

- **At egress:** record the delegation event — which agent, into which runtime,
  under which grant, with which limits attached (scope, spend ceiling,
  expiry). The grant is a signed artifact, so the *terms* of the excursion are
  non-repudiable even if its interior is not observable.
- **On return:** record what came back and reconcile it against the grant.
  Limit enforcement can bind at settlement even where it cannot bind at
  execution (this is the mandate pattern: monetary or scope authority that
  travels with the delegation and is checked when effects materialize).

Boundary evidence is the guaranteed **floor** — the lower bound that holds with
no dependency on the far side's cooperation, with cooperative emission as the
upgrade path above it. It turns "we lost sight of the agent" into "we hold a
verifiable record of exactly what authority left the building, when, and what
returned."

Two bounds on that claim, stated plainly:

- **It covers terms, not conduct.** What is non-repudiable at the floor is the
  *authority* under which the agent left — not what it did once outside. Conduct
  on the far side sits above the floor, and only cooperation puts it there.
- **It covers crossings that traverse your boundary.** An agent reaching a
  foreign runtime by a path the gateway never sees produces no egress record.
  That is an enforcement gap rather than an evidence gap, but it is the honest
  edge of the word "guaranteed."

## Where OCSF PR #1661 closes the stitching gap

The `record_integrity` profile (merged into OCSF 1.9, 2026-07-17) gives
cooperating runtimes a shared, verifiable evidence shape. Three of its
primitives are precisely the cross-runtime seam:

Each event carries an `attestation_list` — an array of `attestation` objects, so
independent attesters (the home gateway, the foreign runtime) each add their own.
Three fields on each attestation are the cross-runtime seam:

| Primitive | What it does across a runtime boundary |
|---|---|
| `chain_uid` | Stable for the lifetime of the chain — it **survives the handoff**, so one query (`attestation_list[].chain_uid = X`) retrieves the full cross-runtime narrative from both stores |
| `authority_uid` | **Each runtime attests its own events** under its own authority identifier — the home gateway signs its records, the foreign runtime signs its records; a verifier checks each credential against the expected authority |
| `prev_event` (`uid`, `type_uid`, `fingerprint`) | The first event emitted on the far side fingerprint-references the last event emitted before the crossing — **the seam itself is tamper-evident**: altering, substituting, or deleting either side of the handoff breaks the link |

Sketch of a two-runtime chain (shape per the merged #1661 schema; a
cross-runtime chain with per-runtime authorities is a usage pattern, not a
prescribed mechanism):

```json
[
  {
    "metadata": { "uid": "aaa-…-001" },
    "attestation_list": [
      {
        "authority_uid": "home-gateway:evidence-anchor:org/…",
        "chain_uid": "89248f7f-…",
        "fingerprint": { "algorithm_id": 3, "serialization_id": 2, "value": "61ea…" },
        "signatures": [ "…home gateway signature…" ]
      }
    ]
  },
  {
    "metadata": { "uid": "bbb-…-002" },
    "attestation_list": [
      {
        "authority_uid": "foreign-runtime:agent-host:tenant/…",
        "chain_uid": "89248f7f-…",
        "fingerprint": { "algorithm_id": 3, "serialization_id": 2, "value": "bb47…" },
        "signatures": [ "…foreign runtime signature…" ],
        "prev_event": {
          "uid": "aaa-…-001",
          "type_uid": 600302,
          "fingerprint": { "algorithm_id": 3, "serialization_id": 2, "value": "61ea…" }
        }
      }
    ]
  }
]
```

Because `prev_event` sits *inside* the fingerprinted and signed content,
deleting or altering an event in the chain breaks the fingerprint and
signatures of the event that references it — on either side of the boundary.

## How the lanes compose (nobody owns all three)

| Lane | Standard / effort | Contribution to the crossing |
|---|---|---|
| Authority | ODIS Passport, CMF `delegation.chain`, SPIFFE | The grant travels with the agent as a signed artifact |
| Correlation | OpenTelemetry (W3C `traceparent`, baggage) | The thread that lets two record sets be joined after the fact |
| Environment trust | Hardware / workload attestation (TEE) | Raises confidence in a *cooperating* foreign runtime's interior claims |
| Enforcement | Runtime policy engines (e.g. CPEX/APL) | Decides at the boundary and, where deployed, on the far side |
| Record / evidence | OCSF `record_integrity` (#1661) | The durable, independently verifiable narrative both sides emit into |

## Where AI Identity fits

AI Identity operates at the record/evidence layer as a **running reference
implementation** of the pattern above — the items below are shipped and
demonstrable, not proposed:

- **Gateway emitter**: produces signed OCSF events at the boundary (the
  "boundary evidence" floor), with write-time hash chaining and export-time
  per-event signatures.
- **Offline verifier CLI**: any third party verifies a chain — including a
  cross-runtime one — with no dependency on the producer's infrastructure
  (current shared bundle: 174/174 signatures verify against the published
  JWKS).
- **Evidence Anchor**: signed Merkle checkpoints with per-event inclusion
  proofs over event sets — the checkpoint construct for summarizing a chain
  (or a cross-runtime excursion) at close.
- **Mandate Service**: scoped monetary authority attached to a delegation,
  enforced at execution or settlement — the concrete form of "limits that
  survive loss of visibility."

The schema seam these implement is the same one contributed upstream in
PR #1661, so the pattern is portable: any runtime can emit it, any verifier
can check it, and no part of it is proprietary to AI Identity.

## Suggested framing for the SIG

1. Split every "visibility into runtime X" question into authority /
   correlation / emission before debating it.
2. Standardize the **seam** (grant format, trace propagation, evidence shape)
   — don't try to standardize the interior of runtimes we don't control.
3. Treat **boundary evidence as the guaranteed floor** and cooperative
   emission as the upgrade path.
