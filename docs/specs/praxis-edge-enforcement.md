# AI Identity Edge on Praxis — In-Cluster Enforcement, SaaS Evidence Plane

| Field              | Value                                                        |
|--------------------|--------------------------------------------------------------|
| **Status**         | Draft — design only; build gated (see §6)                    |
| **Priority**       | P2 — High (after v0.5.0 Enterprise Forensics)                |
| **Author**         | AI Identity Engineering                                      |
| **Created**        | 2026-08-21                                                   |
| **Target Release** | v0.6.0 window (Q4 2026)                                      |
| **Est. Effort**    | ~5–7 engineering weeks across 3 components                   |
| **Depends On**     | PPE initial stable + praxis#11 seam port verified (`integrations/cpex-ocsf-audit/PRAXIS-PORT-PLAN.md`); mandate service settle API; per-org audit chains |
| **Stakeholders**   | Platform Engineering, Compliance, Product                    |

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Architecture Overview](#2-architecture-overview)
3. [Component A: OCSF Ingest Endpoint](#3-component-a-ocsf-ingest-endpoint)
4. [Component B: `cpex-plugin-mandate`](#4-component-b-cpex-plugin-mandate)
5. [Component C: Reference Deployment](#5-component-c-reference-deployment)
6. [Sequencing and Gates](#6-sequencing-and-gates)
7. [Non-Goals](#7-non-goals)
8. [Open Questions](#8-open-questions)
9. [Appendix: Wire Examples](#appendix-wire-examples)

---

## 1. Problem Statement

Today, AI Identity enforcement requires routing traffic through the hosted
gateway. That is the right shape for the SaaS product, but it is the wrong
shape for two audiences the roadmap already names:

- **Data-residency / VPC customers** ("On-premise / VPC deployment", Later
  section of `ROADMAP.md`): regulated buyers who cannot send agent traffic
  through third-party infrastructure at all.
- **Ecosystem deployments**: teams already running the Praxis gateway (the
  CNCF proxy adopting the CPEX core as PPE, its policy engine) who want
  AI Identity's mandate enforcement and evidence trail without adopting a
  second gateway.

The `cpex-ocsf-audit` plugin already proves the pattern: AI Identity code
running *inside* the policy engine, producing signed, chained, OCSF-shaped
evidence, verified against the audit seam with zero source changes. This
spec extends that pattern from *recording* decisions to *enforcing
mandates* — and gives the resulting evidence a first-class path home.

The resulting split: **enforcement runs in the customer's cluster; the
evidence and authority plane stays with AI Identity.** Raw payloads never
leave the cluster — only signed decision records carrying content *hashes*,
and draw-settlement metadata.

## 2. Architecture Overview

```
customer cluster                                 AI Identity SaaS
┌───────────────────────────────────────┐
│  Praxis gateway                       │
│  └─ PPE (CPEX core)                   │        ┌──────────────────────┐
│     ├─ cpex-plugin-mandate ───────────┼───────►│ mandate service      │
│     │    verify Biscuit (offline)     │ settle │  cumulative draws    │
│     │    settle draw / deny over-cap  │◄───────┤  mints draw receipt  │
│     ├─ …other policy plugins…         │receipt │  (Ed25519 root key)  │
│     └─ audit seam                     │        └──────────────────────┘
│         └─ cpex-ocsf-audit ───────────┼───────►┌──────────────────────┐
│              signed OCSF records      │ ingest │ api: /v1/audit/ingest│
│              (chain + DSSE, local     │        │  verify chain + DSSE │
│               chain_uid per edge)     │        │  per-org audit chains│
└───────────────────────────────────────┘        │  exports · forensics │
                                                 │  Evidence Anchor     │
                                                 └──────────────────────┘
```

Key properties:

- **Authority is issued centrally, verified locally.** Biscuit tokens are
  verified at the edge with the published Ed25519 root *public* key — no
  network call to authorize. Only the *draw settlement* (cumulative spend
  accounting) calls home, because spend state must have a single writer
  and receipts must be minted by the root key, which never leaves the SaaS.
- **Evidence is produced locally, anchored centrally.** Each edge
  deployment gets its own `chain_uid`/`authority_uid` and signing key; the
  ingest endpoint verifies chain continuity and signatures on arrival, so
  the platform never has to trust the transport — only the math.
- **Everything composes with the existing seam contract.** The mandate
  plugin appears as an ordinary `mandate-check` step in the executor's
  `DecisionLog`; a denial maps to `status_code: mandate_exceeded`; the
  per-request id at `unmapped."cmf.request.request_id"` joins the draw
  receipt, the OCSF record, and (where deployed) external ledger entries.

## 3. Component A: OCSF Ingest Endpoint

`POST /v1/audit/ingest` on the api service. The inbound twin of the 0.3.0
generic webhook audit sink.

**Auth & scoping.** Org-scoped API key bound to a registered *edge
deployment* (new lightweight registration object: `edge_id`, `chain_uid`,
`authority_uid`, verification public key / JWKS `kid`, created via
dashboard or API). A key may only ingest into its own registered chains.

**Body.** NDJSON batch of OCSF events exactly as `cpex-ocsf-audit` emits
them (dispatch and decision records alike). Batch size capped; senders
retry with at-least-once semantics.

**Verification on arrival (before anything is stored as `verified`):**

1. Canonicalize per RFC 8785 minus the envelope (`attestation_list`,
   `unmapped.signature_b64`, `unmapped.signature_key_id`) — the same
   covered bytes as the emitter's `sign::signing_input`.
2. Recompute the fingerprint; verify the DSSE signature against the edge's
   registered key.
3. Verify `prev_event` continuity against the stored chain head for that
   `chain_uid`; verify `stream_seq` density per `stream_id`.
4. Dedupe on `metadata.uid` (idempotent replays are 200s, not duplicates).

**Failure semantics.** Chain gaps and signature failures are **recorded and
alerted, not silently dropped**: the record is stored quarantined with its
failure reason, the org's audit health surface flags it, and the response
reports per-record status (`202` with a results array). A gap is itself
evidence — an edge that crashed mid-epoch or a stream someone tampered
with — and the platform's job is to surface it, not launder it.

**Storage.** Verified records append to the org-scoped audit chain store
(the per-org chains shipped in the audit-chain-per-org migration), tagged
with `edge_id`, feeding the existing export profiles, forensics views, and
Evidence Anchor checkpoints unchanged.

## 4. Component B: `cpex-plugin-mandate`

A new Rust crate at `integrations/cpex-plugin-mandate`, structured like
`cpex-ocsf-audit` (same factory/registration pattern, built against the
canonical seam per the port plan's sequencing rule).

**Role.** Sequential-phase enforcement plugin, fail-closed. Per dispatch:

1. **Extract** the Biscuit from the request (CMF extension; header fallback
   for plain-HTTP callers), plus the per-request id.
2. **Verify offline** with the configured root public key: signature and
   attenuation chain, TTL, audience, `scope_granted` facts against the
   route's required scopes, and the token's own embedded checks
   (`check if amount($a), $a <= limit or settlement(true)` — the ceiling
   travels inside the token, exactly as `common/biscuit/tokens.py` mints
   it, so a forged or widened cap fails cryptographically, not by lookup).
3. **Settle the draw** for spend-bearing calls: one HTTPS call to the
   mandate service (`amount`, `currency`, `mandate id`, `revocation_id`,
   `correlation_id`). The service performs the atomic cumulative-spend
   check (single writer — no distributed draw accounting at the edge) and
   returns either the **signed draw receipt** or an over-limit refusal.
4. **Enforce**: allow (attaching the receipt to the response context), or
   deny with `mandate_exceeded` and the service's reason string — which the
   audit plugin then records as the deny verdict, steps and all.

**Fail-closed posture.** No token → deny (`mandate_required`). Invalid
token → deny (`mandate_invalid`). Settle call unreachable → deny
(`settlement_unavailable`), with a bounded retry and a configurable
grace window of **zero by default** — an edge that cannot reach the
authority plane does not spend. (An offline settlement mode is explicitly
deferred; see Open Questions.)

**What the edge never holds:** the Ed25519 root private key. Receipts are
minted only by the mandate service; the edge verifies and transports them.
Compromise of an edge cluster therefore cannot forge authority or receipts
— it can at worst deny service, which is the failure direction we choose.

**Non-spend mandates.** Scope/TTL/audience-only enforcement (no draw) is
fully offline — steps 1–2 and enforce. This mode has no availability
dependency on the SaaS at all.

## 5. Component C: Reference Deployment

A worked deployment under `k8s/edge/` (or `deploy/` in the plugin crate):
Praxis + PPE + both plugins, with an APL config wiring `mandate-check`
ahead of the policy plugins and the audit plugin in decision-sink mode
(no `hooks:`), pointed at the SaaS ingest endpoint. Includes the edge
registration flow and key generation. The committed demo assets
(`decision_sink_demo`, the spend-story records) double as its smoke test:
the $100-mandate scenario — three draws allowed, the fourth denied,
records verifying offline — must run end-to-end on a fresh install.

## 6. Sequencing and Gates

| Gate | Condition | Unblocks |
|---|---|---|
| G0 | — (no dependency) | Component A design → build. The ingest endpoint is useful today for the hosted gateway's own records and any cpex#166 deployment. |
| G1 | PPE initial stable **and** praxis#11 port re-verified per `PRAXIS-PORT-PLAN.md` (zero source changes, or findings resolved upstream) | Component B build against the post-port seam |
| G2 | Components A + B green | Component C reference deployment + end-to-end smoke |

Build order: **A → B → C.** September stays committed to v0.5.0
Enterprise Forensics per `ROADMAP.md`; Component A is small enough to land
opportunistically if a demo or integration needs it, Components B and C
belong in the v0.6.0 window — where they pair naturally with the agent
spend-control alpha (same mandate machinery, enforced at a new point).

## 7. Non-Goals

- **Replacing the hosted gateway.** The SaaS data plane is untouched; this
  adds a deployment shape, it does not migrate the existing one.
- **Contributing gateway features to Praxis/PPE.** We consume the seam and
  plugin contracts as published; anything we need changed upstream is an
  upstream conversation, not a fork.
- **Distributed draw accounting.** Cumulative spend keeps a single writer
  (the mandate service). Multi-edge, offline, or locally-settled spend is
  out of scope until a real deployment demands it.
- **Building before the gates.** No praxis-only wiring lands anywhere
  before G1 — the port-plan sequencing rule applies to this work too.

## 8. Open Questions

1. **Revocation latency at the edge.** Offline verification honors TTLs
   but not mid-TTL revocation. For spend calls, settlement naturally
   enforces revocation (the service refuses a revoked `revocation_id`).
   For non-spend scope checks: is short TTL + re-issue sufficient, or do
   edges need a revocation feed? Proposal: short TTLs first; measure.
2. **Receipt delivery.** The settle response carries the receipt; does the
   plugin attach it to the response extensions (delegator-visible), post
   it to a configured callback, or both? Leaning: response extensions by
   default, callback optional.
3. **Ingest transport.** Plain HTTPS batching first; is a streaming
   transport (gRPC, matching the external-ledger sink pattern) worth a
   shared abstraction in the audit plugin, or premature?
4. **Settle-call latency budget.** One HTTPS round-trip per spend-bearing
   call, on the request path. Acceptable for tool-invocation traffic;
   needs a stated budget (p99 target) and a load test before GA.
5. **Edge key custody.** Per-edge signing keys: operator-provided PEM
   (matching the audit plugin's current config) vs. issued at registration
   with rotation epochs. Start operator-provided; revisit with the JWKS
   publication story.

## Appendix: Wire Examples

**Ingest request (abridged):**

```
POST /v1/audit/ingest
Authorization: Bearer <edge-scoped api key>
Content-Type: application/x-ndjson

{"class_uid":6003,...,"attestation_list":[{"fingerprint":...,"prev_event":...}],"unmapped":{"cpex.stream":{"stream_id":"gw-1/boot-7","stream_seq":46,...},...}}
{"class_uid":6003,...}
```

**Ingest response:**

```json
{
  "results": [
    {"uid": "...", "status": "verified", "chain_position": 47},
    {"uid": "...", "status": "quarantined", "reason": "stream_seq gap: expected 47, got 49"}
  ]
}
```

**APL wiring (edge, abridged):**

```yaml
plugins:
  - name: mandate-check
    kind: authz/mandate
    config:
      root_public_key_pem_path: /etc/aiid/keys/biscuit-root.pub
      settle_endpoint: https://api.ai-identity.co/v1/mandates/settle
      fail_mode: closed
  - name: ocsf-audit
    kind: audit/ocsf
    # no `hooks:` -> decision-audit sink mode (sees denials)
    config:
      chain: true
      signing: dsse
      chain_uid: "edge-<edge_id>"
      destination: https://api.ai-identity.co/v1/audit/ingest
```

**Deny record produced by the pair (abridged; matches the committed
spend-story shape):**

```json
{
  "action": "Denied", "disposition": "Blocked",
  "status_code": "mandate_exceeded",
  "status_detail": "mandate-check: draw 15.00 exceeds remaining 5.00 of 100.00 mandate for agent-7",
  "unmapped": {
    "cmf.request.request_id": "corr-d4e55b37",
    "cpex.decision": {"steps": [{"action": "denied", "phase": "sequential", "plugin": "mandate-check"}]}
  }
}
```
