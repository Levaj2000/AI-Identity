# AI Identity

**Cryptographic identity, policy, and audit for AI agents.**

---

## The problem

Enterprises are moving fast into agentic AI. Agents are about to take real actions on real systems — create records, move data, call APIs, spend money on the company's behalf.

But every agent today is running on a shared service account key. There's no way to answer three questions that every security, compliance, and platform leader needs answered:

- **Which agent** took this action?
- **Under whose authority** was it authorized?
- **Against which policy** was it evaluated?

The identity, policy, and audit primitives we built for humans and services over the last 20 years simply don't exist for agents. AI Identity closes that gap.

---

## What AI Identity does

- **Cryptographic agent identity.** Every agent gets a signed, revocable, rotatable identity — not a shared key.
- **Context-aware policy enforcement.** Every agent decision is evaluated against the rules you set, at decision time.
- **Immutable, auditor-ready audit log.** Each decision is chained and signed using the same primitive git uses for commit history — tamper-evident by construction.

---

## Four things a security leader should know

**1. Not in the hot path.**
Agents verify attestations offline. AI Identity signs once; your runtime verifies locally. Zero added latency on agent decisions. Scale your agents to a million calls/sec — we don't care.

**2. Hash-chained at the source, normalized at render — your audit log is immutable, your UI is consistent.**
Every decision is cryptographically linked to the one before it at write time, then rendered through a canonical view layer. The chain holds even when the dashboard layout changes. An auditor can replay the chain a year later and prove it hasn't been tampered with. SOC 2, EU AI Act, and NIST AI RMF export profiles built in.

**3. Least-privilege by default, proven.**
Per-agent, per-decision policy — not per-service-account. The audit trail is the proof you enforced it.

**4. Crypto-agile by design.**
ECDSA-P256 today, ML-DSA-87 slot ready. Your mandates won't need a re-signing event when NIST clocks tick over — the signature envelope already carries an algorithm identifier and a second-signature slot, so hybrid post-quantum signing rolls in without invalidating anything we issued today.

---

## Platform-enforced hardening

*You configure once; we enforce every call.*

The infrastructure controls below are not customer responsibilities to wire up. They are platform guarantees that ship by default to every tenant.

- **Cluster.** Binary Authorization in ENFORCE mode (only attested, digest-pinned images run). Pod Security Admission at restricted. Default-deny NetworkPolicies with explicit allow-lists. Non-root containers with read-only root filesystems.
- **Ingress.** Cloud Armor WAF in ENFORCE with adaptive DDoS protection and per-IP throttling. HTTPS everywhere. No public kubectl endpoint — control plane reached only through Connect Gateway with Master Authorized Networks on.
- **Secrets.** Google Secret Manager via CSI driver — no secrets in manifests. Signing keys held in Cloud KMS HSM, never leave the HSM boundary. Upstream LLM credentials encrypted with Fernet at rest.
- **Database.** PostgreSQL with Row-Level Security in FORCE mode and `sslmode=verify-full`. Application-layer scoping is layered on top of database-layer RLS, so a compromised service cannot read another tenant's data.
- **Application.** ABAC on agent metadata. Offline attestation verification CLI. Real-time SIEM push via signed webhook. Compliance export API mapped to SOC 2 CC6/CC7, ISO 27001 A.12/A.13, and CIS Kubernetes Benchmark.

---

## Fit for a security team

| Capability | Detail |
|---|---|
| Agent identity | Issuance, rotation, revocation, TTL |
| Audit log | Immutable, append-only, cryptographically chained |
| Policy | Context-aware, evaluated at decision time |
| Compliance exports | SOC 2, EU AI Act, NIST AI RMF profiles |
| SIEM integration | Audit export API |
| Deployment | Your cloud or ours |

---

## The design partner ask

- **One agent workflow** you pick. Starts small, expands if it works.
- **30 days, free.** No contract games.
- **Weekly 20-min sync** directly with me.
- **Success criteria** we define together in week 1.
- **In exchange:** honest feedback, and — if it works for you — a reference conversation with one other buyer.

That's it. If it isn't a fit at day 30, we part as friends and I keep buying you coffee.

---

## About the founder

**Jeff Leva** — Founder & CEO, AI Identity.

I spent years inside the kind of production systems that can't fail — cloud banking platforms handling $50B+ in client assets, 99.9% uptime, zero tolerance for ambiguity about who did what and why.

When I started working with agentic AI systems, I kept running into the same problem: agents executing real actions with shared keys, no identity, and no audit trail. The governance primitives we'd built for humans — identity, policy, traceability — simply didn't exist for agents.

AI Identity is my answer to that gap: cryptographic agent identity, immutable audit logs, and policy enforcement built to the standards production systems actually require.

---

**Contact**

Jeff Leva — Founder & CEO

jeff@ai-identity.co

[ai-identity.co](https://www.ai-identity.co)
