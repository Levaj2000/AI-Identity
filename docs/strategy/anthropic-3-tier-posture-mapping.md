# AI Identity vs. Anthropic's Agent-Security Model — Posture Map

**Sprint 16 · board item #416 · 2026-06-23**
Canonical source for the positioning artifact. Internal reference + basis for the executive PDF
(`marketing/sales/ai-identity-anthropic-tier-posture-2026-06-23.pdf`). Pairs with Insight #101 / briefing #215.

---

## Thesis (one line)

> **Anthropic is raising the bar on agent *credentials*. AI Identity already operates at the layer
> *above* — the portable record of authority and action — and has now closed the one credential gap
> that mattered.**

## The model (our synthesis — not an Anthropic-branded framework)

Anthropic publishes zero-trust agent-security *principles*, not an official numbered tier ladder. We
synthesize them into a 3-tier maturity model so we can map ourselves honestly. Anthropic's own
published controls (Claude Code security docs): "multiple short-lived, narrowly scoped credentials,
each limited to a specific purpose and expiring independently"; **fail-closed** ("unmatched commands
default to requiring manual approval"); least-privilege permissioning; secure credential storage.

| Tier | What it requires | Source basis |
|------|------------------|--------------|
| **Tier 1 — Identity hygiene** | Unique cryptographic identity per agent; short-lived, narrowly-scoped credentials; deny-by-default authorization. *Static API keys are unsuitable even here.* | Claude Code security docs (short-lived/scoped/expiring creds; fail-closed) |
| **Tier 2 — Transport & key custody** | Mutual TLS; keys held in hardware (HSM/TPM); credentials issued via federation (WIF/OIDC) rather than stored secrets. | Anthropic Workload Identity Federation for the Claude API |
| **Tier 3 — Hardware-rooted attestation** | Remote attestation of the agent's runtime (TPM/enclave/confidential compute); signing identity bound to attested hardware. | Anthropic confidential inference (TPM root of trust) |

## AI Identity posture map (honest current state)

| Tier | AI Identity status | Evidence |
|------|--------------------|----------|
| **Tier 1** | **Largely met — just advanced.** | Each agent has its own `aid_sk_` cryptographic identity; runtime keys now **expire by default** with a refresh flow (PR #349, in review); gateway is **fail-closed / deny-by-default**. |
| **Tier 2** | **Partial — our *root* is already Tier-2-grade.** | Signing/attestation root is **GCP Cloud KMS / HSM-backed** (ECDSA P-256, JWKS published). Federated issuance for *customer agent creds* is roadmap (WIF/OIDC, #414); mTLS for agent creds not yet. |
| **Tier 3** | **Roadmap.** | Consume + record TPM/enclave/mTLS attestation at agent registration and bind it into the OCSF evidence chain (#415). |

## Above the tiers — the part Anthropic doesn't occupy

Tiers 1–3 secure *how an agent authenticates*. AI Identity adds the layer above: a **portable,
cross-vendor, offline-verifiable record of what authority an agent held and what it did** — OCSF-native
audit events plus DSSE/ECDSA-signed evidence a third party can verify with **only our published public
key** (no shared secret). Hardware attestation makes this layer *more* valuable, not less: recorded
properly, we become the record layer **on top of** hardware roots — which feeds the OCSF
workload-attestation gap we agreed to co-author with IBM/Fred.

## The "are you obsolete?" pre-empt

Hardware-bound credentials are a **complementary lower layer, not a competitor**. They raise industry
demand for a portable record that can *incorporate* attestations — precisely our differentiated layer.
The one genuine catch-up — the static agent key Anthropic calls unsuitable at Tier 1 — is **closed**
(PR #349). Our signing root is already HSM-backed. We are not behind the trend; we sit on top of it.

## Roadmap (Sprint 16, board items)

- **#413 — short-lived runtime tokens by default** → **DONE**, PR #349 (in review).
- **#414 — OIDC / Workload Identity Federation** for customer agent credentials (Tier 2).
- **#415 — consume + record hardware attestation** (Tier 3) → the moat / OCSF workload-attestation gap.
- **#416 — this posture map** (positioning).

## What to watch for (reviewer's note)

- **The "3 tiers" are AI Identity's synthesis**, not an Anthropic-labeled framework. The principles are
  sourced (Claude Code security docs; WIF; confidential inference), but verify against Anthropic's
  primary docs before any external/customer use.
- **Tier 1 "largely met" is contingent** on PR #349 *merging and deploying*. Until then say
  "in review," not "shipped."
- **Tier 2 "HSM-backed" refers to our signing/attestation root**, not customer agent-credential custody
  (those keys are still classical, hashed-at-rest).
- **mTLS-for-agent-creds and WIF are roadmap, not shipped** — don't imply otherwise.
- **The "Anthropic doesn't occupy the record layer" claim is our assessment** as of 2026-06; revisit if
  they ship a provenance/attestation-record product.

## Sources

- Anthropic — Claude Code Security (short-lived/scoped/expiring credentials; fail-closed; least
  privilege; secure credential storage): https://code.claude.com/docs/en/security
- Anthropic — Workload Identity Federation for the Claude API (referenced in Insight #101)
- Anthropic — Confidential inference / TPM root of trust (referenced in Insight #101)
- Internal — Insight #101, briefing #215; PR #349
