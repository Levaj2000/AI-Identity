# Product Hunt Launch Copy

## Tagline (60 chars max)
Identity, audit trails, and governance for AI agents

## Description (260 chars max)
AI agents are making decisions with shared credentials and zero audit trails. AI Identity gives every agent its own identity, tamper-proof audit logs, and policy enforcement — so you can prove compliance to regulators, not just hope for it. Free to start.

## Topics/Categories
- Artificial Intelligence
- Developer Tools
- Security
- Compliance

## Maker Comment (post immediately after launch)

Hey Product Hunt!

I'm Jeff, founder of AI Identity. I built this because I kept seeing the same pattern: companies deploying AI agents with shared API keys, no audit trails, and no way to answer the question every auditor will eventually ask — "What did this agent do, when, and why?"

That's a ticking time bomb for regulated industries. HIPAA, EU AI Act, SOC 2 — they all require attributable, auditable actions. Shared credentials make that impossible.

AI Identity solves this with three things:

1. **Per-agent identity** — Every agent gets its own credentials with scoped permissions. No more shared keys.
2. **Tamper-proof audit trails** — HMAC-SHA256 cryptographically chained logs that auditors can verify independently.
3. **Policy enforcement** — Deny-by-default gateway that blocks unauthorized actions before they reach your LLM provider.

You can deploy it in about 15 minutes. We have an interactive API playground where you can run real API calls against our production backend — no signup needed.

The free tier includes 5 agents, 2K requests/month, and 30-day audit retention. More than enough to evaluate whether this fits your stack.

I'd love your feedback — especially if you're in healthcare, finance, or any regulated space dealing with AI agent governance. Happy to answer any questions here!

## First Comment (post right after maker comment)

For anyone evaluating this for a regulated environment, here's what the compliance mapping looks like today:

- **SOC 2 Type II** — Logical access controls, tamper-evident audit trail, encryption at rest/transit, tenant isolation
- **EU AI Act** — Human oversight gates, traceability, transparent enforcement, audit export
- **HIPAA** — Minimum necessary access via per-agent credentials, activity logging, access controls
- **NIST AI RMF** — Agent observability, policy governance, cryptographic integrity, fail-closed design

We're not certified yet (that comes with scale), but the architecture is designed to be audit-ready from day one. Happy to walk through any specific framework requirements.

## Gallery Images (suggestions for screenshots/graphics)

1. **Hero image** — Dashboard overview showing agents, audit logs, and system health
2. **Audit trail** — Forensics view showing HMAC-chained log entries with chain verification
3. **Policy enforcement** — Gateway deny/allow decision flow
4. **15-minute setup** — Interactive API playground showing the 6-step onboarding
5. **Compliance mapping** — Visual of which frameworks are covered

## Suggested Launch Day Schedule

- **12:01 AM PT** — Launch goes live (Product Hunt resets at midnight PT)
- **6:00 AM PT** — Send launch email to your list
- **7:00 AM PT** — Post on LinkedIn and Twitter
- **Throughout the day** — Respond to every PH comment within 30 minutes
- **End of day** — Post a "Day 1 recap" on LinkedIn with metrics

## Hunter Outreach Template

Subject: Would you hunt our AI agent governance tool on Product Hunt?

Hi [Name],

I'm building AI Identity — governance infrastructure for AI agents (per-agent identity, tamper-proof audit trails, policy enforcement).

With the EU AI Act hitting enforcement this year and every regulated industry scrambling to prove their AI is compliant, the timing feels right for a PH launch.

Would you be interested in hunting it? Happy to give you a full walkthrough beforehand.

[Link to product / demo]

Thanks,
Jeff
