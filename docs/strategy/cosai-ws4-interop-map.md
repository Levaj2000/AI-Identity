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
| **1. Identity** | Who is this agent / workload? | SPIFFE/SVID, DIDs, agent keys |
| **2. Authority / delegation grant** | Who may act, on whose behalf? | ODIS (Passport), CMF delegation |
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
| **AI Identity** | 5 — Record/evidence | Signed OCSF events; DSSE envelopes; offline-verifiable; Evidence Anchor (inclusion proofs); attestation / record_integrity profiles | Signed, queryable OCSF event records | Identity, authority, attestation, policy signals from layers 1–4 | Is the boundary — maps everyone's outputs into one neutral evidence schema |
| **ODIS** | 2 — Authority grant | Passport / Bridge / Router; "Delegation Chain Record" | Delegation grants / passports | Identity (layer 1) | Grant → recorded as an OCSF delegation event |
| **TrustGraph** (Red Hat) | 1 + 2 — Identity + delegation graph (raw telemetry; becomes durable evidence via the OCSF seam below) | KeyCloak SPI + SPIFFE + AuthBridge sidecar → OTel spans → delegation DAG | OTel spans; runtime delegation graph | Workload identity, tokens | OTel → OCSF mapping (telemetry spans → evidence records) |
| **EQTY Lab** | 4 — Environment attestation | TEE (AMD SEV/TDX, NVIDIA CC); DIDs; model signing; RFC 9421 gateway; offline-verifiable | Hardware attestation quotes; integrity graph; signed certs | Workloads, models | Hardware quote → OCSF workload-attestation object |
| **IBM CPEX / CMF** | 3 — Runtime enforcement | CPEX (policy engine); CMF (typed policy input: ContentPart + extensions); APL (declarative policy) | Policy decisions; CMF delegation.chain; security labels; tool/framework context | Identity, delegation, attestation | CMF ↔ OCSF cross-map: delegation.chain, security labels, tool/framework context |

> **On AI Identity's scope:** *AI Identity is a working reference implementation
> that also operates at the identity (agent keys) and authority/delegation
> (Mandate Service) layers — our primary contribution to this shared map is the
> record/evidence substrate, where the other layers' outputs become durable,
> verifiable evidence.*

> **A note on "evidence" (added 2026-07-02):** several layers naturally produce
> audit-relevant output — logs, spans, traces — that reasonably *feels* like
> evidence. To keep layer 5 useful as a shared reference, we're using a specific
> bar for what counts: durable, neutral-schema, cryptographically verifiable,
> tamper-evident. Raw telemetry becomes that kind of evidence once it crosses an
> OCSF-boundary seam (see below) — not before. Flagging this so the map stays
> precise as more layers describe their outputs as "evidence" in conversation.

## Interop seams worth building (the positive-sum payoff)

The map makes the interop work concrete — each seam is a natural OCSF-track
convergence point:

- **TrustGraph OTel spans → OCSF** evidence records (telemetry → record mapping)
- **ODIS delegation grant → OCSF** delegation record (converging on Ania's open delegation PR #1665, not a parallel shape)
- **EQTY hardware quote → OCSF** workload-attestation object
- **CMF delegation.chain / security labels / tool context → OCSF**
- All of the above compose on the **layer-5 record** — one verifiable account of
  who was authorized, what ran, in what environment, and what happened.

## How to use this

- Each player **corrects their own row** (1–2 lines is fine).
- Confirm the layer placements to establish a shared architectural understanding.
- We pick **1–2 seams** to prototype against OCSF as the shared evidence
  vocabulary.
