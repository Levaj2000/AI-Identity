# LinkedIn Reply Draft — Megan (Cardinal Health, Director of Sales & Marketing)
**Date:** 2026-05-20
**Context:** Megan asked how AI Identity secures and governs AI tasks that bridge legacy patient databases and new AI applications without exposing sensitive patient data.

---

## Recommended reply (≈210 words)

Hi Megan — thank you, I'll pass that along. She'll appreciate it.

Great question, and it's exactly the seam most healthcare teams are grappling with right now. The short version: AI Identity sits between the agent and any downstream system — including a legacy patient database — and enforces three things at runtime.

**1. Identity, not shared keys.** Every agent gets its own cryptographic credential. Nothing in our platform — or the agent itself — ever holds the database password in plaintext. Upstream credentials live in a Fernet-encrypted vault and are injected per request, scoped to that agent.

**2. Fail-closed policy enforcement.** Every query an agent issues passes through our gateway first. If a policy doesn't explicitly permit that action — that dataset, that field, that volume — it doesn't happen. No PHI leaves the legacy system unless the policy says it can.

**3. Tamper-evident audit.** Every decision is written to an HMAC-SHA256 hash-chained log with PII redacted at capture. When your compliance team (or an auditor) asks "which agent touched that record, when, and was it authorized?" — there's a verifiable answer, not a vendor's word.

That's the layer between your governance documentation and your agents actually following it. Happy to walk through a healthcare-specific scenario if useful.

Best,
Jeff

---

## Notes on the draft

- **Tone:** Warm open (acknowledges the regards), then directly technical — Megan asked an expert question and signaled she wants an expert answer.
- **Healthcare hooks used:** "PHI," "legacy patient database," "compliance team / auditor" — maps her vocabulary to our architecture without overclaiming HIPAA certification.
- **Doesn't oversell:** Avoids claiming SOC 2 / HITRUST (we're SOC 2 Type I *in prep* per the roadmap). Says what the architecture does today.
- **Soft CTA:** "Healthcare-specific scenario" leaves the door open without pushing a demo on a first reply.
- **Length:** ~210 words — long enough to be substantive on LinkedIn, short enough to read on mobile without an "…see more" cut on the key claim.

## Alternative shorter version (≈110 words, if you prefer)

Hi Megan — thank you, I'll pass that along.

Short answer: AI Identity sits between the agent and the legacy system and enforces three things at runtime — (1) every agent has its own cryptographic identity, so no shared database credentials; (2) every query passes through a fail-closed gateway that denies anything a policy doesn't explicitly permit; (3) every decision is written to a tamper-evident, HMAC-chained audit log with PHI redacted at capture.

The net effect: your governance documentation and what your agents actually do are the same thing — and provably so. Happy to walk through a healthcare scenario if it's useful.

Best, Jeff
