# CoSAI WS4 — Agent Identity & Governance Interop Map

**A shared capability map for the players building in this space · draft template**

## Purpose

We are converging on the same challenge — trustworthy autonomous agent identity,
authority, and governance — from different architectural layers. This document
provides a shared reference to help us (1) understand where each effort fits,
(2) distinguish capabilities that operate at different layers, and (3) identify
integration points where our work can compose rather than overlap.

The intent is not to converge on a single implementation, but to develop a
shared understanding of how complementary efforts relate and where
interoperability is valuable.

## Guiding principles (so this stays neutral and collaborative)

- **Descriptive, not evaluative.** This maps capabilities and boundaries — it is
  *not* a scorecard or a ranking. No strengths/weaknesses grading.
- **Each player owns their own row.** The rows below are a starting-point read,
  offered in good faith — **please correct your own row.** You know your system;
  we don't.
- **Interface level only.** What you emit / consume / where the boundaries are.
  No roadmaps, internals, or anything competitively sensitive.
- **Feeds WS4, doesn't replace it.** This is an artifact for the work-stream, not
  a parallel process.

## The shared layer model (the part worth aligning on first)

The room sometimes blurs these. They are distinct, and most of us occupy one or
two — not all:

| Layer | Question it answers | Example occupant(s) |
|---|---|---|
| **1. Identity** | Who is this agent / workload? | SPIFFE/SVID, DIDs, agent keys, Agent Manifest (deploy-time declaration) |
| **2. Authority / delegation grant** | Who may act, on whose behalf? | ODIS (Passport), CMF delegation, ca2a |
| **3. Runtime enforcement** | Is this action allowed *right now*? | IBM CPEX / CMF / APL |
| **4. Environment attestation** | Is the runtime itself trustworthy? | EQTY (TEE / hardware) |
| **5. Record / evidence (system-of-record)** | What actually happened, verifiably? | AI Identity / OCSF |

Layer 5 provides a common evidence layer where outputs from the other layers can
be represented as durable, queryable, and independently verifiable records.
That's the natural shared substrate — and it's already a neutral standard (OCSF).

## Capability map

Rows other than AI Identity are a starting-point read — **to be confirmed /
corrected by each owner.**

| Player | Primary layer(s) | Core primitive | Emits (outputs) | Consumes (inputs) | OCSF-boundary seam |
|---|---|---|---|---|---|
| **AI Identity** | 5 — Record/evidence | Signed OCSF events; DSSE envelopes; offline-verifiable; Evidence Anchor (inclusion proofs); `attestation` object + `record_integrity` profile, merged 2026-07-17, shipped in OCSF 1.9.0 (released 2026-08-03) | Signed, queryable OCSF event records | Identity, authority, attestation, policy signals from layers 1–4 | Maps other layers' outputs into the neutral OCSF evidence schema |
| **ODIS** | 2 — Authority grant | Passport / Bridge / Router; "Delegation Chain Record" | Delegation grants / passports | Identity (layer 1) | Grant → recorded as an OCSF delegation event |
| **Verifiable Intent** (Mastercard) | 2, Authority grant | Layered SD-JWT credential chain: L1 binds the user's device key (RFC 7800 `cnf`), L2 delegates to the agent with constraints, L3 splits network- and merchant-facing. Builds only on SD-JWT / JWS / JWK / RFC 7800 | L1/L2/L3 credentials; a verification result (`satisfied`, `violations`, `checked`, `skipped`); a registered constraint vocabulary (`mandate.checkout.*`, `mandate.payment.*`) | User device key; user-authored constraints | Verification result becomes an OCSF event; constraint vocabulary becomes the terms of a delegation. Spec scope excludes any record or audit layer |
| **TrustGraph** (Red Hat) | 1 + 2 — Identity + delegation graph; **also 5** — per the group's 2026-07-02 discussion, its audit-trail / traceability output is itself record-of-evidence, currently in OTel rather than OCSF form | KeyCloak SPI + SPIFFE + AuthBridge sidecar → OTel spans → delegation DAG | OTel spans; runtime delegation graph; audit trail | Workload identity, tokens | OTel ↔ OCSF mapping (spans ↔ event records) |
| **EQTY Lab** | 4 — Environment attestation | TEE (AMD SEV/TDX, NVIDIA CC); DIDs; model signing; RFC 9421 gateway; offline-verifiable | Hardware attestation quotes; integrity graph; signed certs | Workloads, models | Hardware quote → OCSF workload-attestation object |
| **Agent Manifest / TRACE** | 1 + 2 — deploy-time declaration of what the agent *is*; **also 5** via TRACE, its own attestation-record format and append-only registry | Hardware-anchored manifest over deploy-time artifacts (prompt, policy bundle, model identity, tool schemas, delegation chain, provenance); TRACE claims | Signed manifest; TRACE records; registry anchors | Deploy-time artifacts; TEE attestation | Manifest hash as an attested artifact in the runtime record; TRACE claims ↔ OCSF events |
| **IBM CPEX / CMF** | 3 — Runtime enforcement | CPEX (policy engine); CMF (typed policy input: ContentPart + extensions); APL (declarative policy) | Policy decisions; CMF delegation.chain; security labels; tool/framework context | Identity, delegation, attestation | CMF ↔ OCSF cross-map: delegation.chain, security labels, tool/framework context |

> **On AI Identity's scope:** *AI Identity is a working reference implementation
> that also operates at the identity (agent keys) and authority/delegation
> (Mandate Service) layers — our primary contribution to this shared map is the
> record/evidence substrate, where the other layers' outputs become durable,
> verifiable evidence.*

> **A note on "evidence" (added 2026-07-02, revised 2026-07-31):** several layers
> here produce audit-relevant output — logs, spans, traces, audit trails, TRACE
> claims — and more than one is fairly described as evidence. Rather than police
> the word, it seems more useful to name the properties that let a record be
> checked later by someone who wasn't there: durable, neutral-schema,
> cryptographically verifiable, tamper-evident. Different layers supply different
> subsets of those today, and serializing across an OCSF seam is one way — not the
> only way — to reach the full set. Noting the properties, not a threshold, so the
> map stays precise as each layer describes its own outputs.

## Interop seams worth building (the positive-sum payoff)

The map makes the interop work concrete — each seam is a natural OCSF-track
convergence point:

- **TrustGraph OTel spans ↔ OCSF** event records (telemetry ↔ record mapping)
- **ODIS delegation grant → OCSF** delegation record (converging on the `delegation` object from Ania's PR #1665, merged 2026-07-24 — not a parallel shape)
- **EQTY hardware quote → OCSF** workload-attestation object
- **CMF delegation.chain / security labels / tool context → OCSF**
- **Agent Manifest hash → an attested artifact** in the runtime record; **TRACE claims ↔ OCSF** events
- **VI verification result, into an OCSF** event record. Every VI verification produces a verdict and then nothing durable: the spec rules a record layer out of scope, so the result has no interoperable shape to land in
- All of the above compose on the **layer-5 record** — one verifiable account of
  who was authorized, what ran, in what environment, and what happened.

### A note on carrying one layer-2 credential through another (added 2026-09-11)

Layer 2 now has several occupants, and a credential issued in one
representation will sometimes be carried in another: a VI L2 mandate recorded
as a CMF `delegation.chain` element, an ODIS passport recorded as an OCSF
`delegation`. Reading VI's credential format against a delegation-chain shape
surfaced two questions that are not specific to either pair and are worth
settling once rather than per-integration. Both are for the owners of the
representations involved to answer, not for this document to assert.

- **Does the carrying representation hold the key the credential is bound to?**
  VI's chain integrity rests on key confirmation at each layer. A hop that
  records who delegated to whom, without the key, preserves the assertion and
  drops the proof. Whether that matters depends on whether the consumer
  re-verifies or trusts the carrier.
- **How do an absolute expiry and a relative one reconcile?** VI carries `exp`
  as an absolute timestamp with a hard reject rule. A representation carrying
  a duration instead needs a defined anchor: the credential's own issued-at, or
  the moment the carrier observed it. Those differ by the ingestion delay, so
  two identical grants can expire at different moments depending on when they
  were seen.

The second is the more general one. Any layer that timestamps an artifact it
received rather than the artifact's own claim inherits it.

### Where the terms of a grant live (added 2026-09-11)

Every layer-2 occupant here expresses bounds on the authority it grants, and
layer 5 currently has nowhere to put them. OCSF's `delegation` object carries
four attributes and all four are correlation identifiers, so a record can say a
grant existed, who issued it and its ancestry, but not what it permitted. That
is filed as [ocsf#1756](https://github.com/ocsf/ocsf-schema/issues/1756),
proposing a `constraint` object covering both a grant's terms and the
consumption against them, and citing VI's constraint vocabulary as prior art.

Named here because it is a seam rather than one player's gap: it is the field
an ODIS passport, a CMF delegation chain and a VI mandate would all serialize
into.

## How to use this

- Each player **corrects their own row** (1–2 lines is fine).
- Confirm the layer placements to establish a shared architectural understanding.
- We pick **1–2 seams** to prototype against OCSF as the shared evidence
  vocabulary.
