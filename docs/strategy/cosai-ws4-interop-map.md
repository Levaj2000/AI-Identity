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
- All of the above compose on the **layer-5 record** — one verifiable account of
  who was authorized, what ran, in what environment, and what happened.

## How to use this

- Each player **corrects their own row** (1–2 lines is fine).
- Confirm the layer placements to establish a shared architectural understanding.
- We pick **1–2 seams** to prototype against OCSF as the shared evidence
  vocabulary.
