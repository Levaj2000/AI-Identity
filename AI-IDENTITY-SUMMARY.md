# AI Identity — Company Summary

## What We Do

AI Identity is the identity and access management layer for AI agents. We give each agent its own cryptographic API key, scoped permissions, and tamper-proof audit trail. Think Okta, but for agents instead of humans.

Teams running multiple AI agents today share a single API key across all of them. One compromised agent exposes everything. There's no way to answer "which agent made this $400 API call?" or enforce least-privilege per agent. AI Identity fixes this with a 15-minute deploy, not a 15-week procurement cycle.

## Market Space

**Category:** Non-Human Identity (NHI) Management for AI Agents — a subcategory we're defining between legacy workload IAM and developer-focused agent tooling.

**Target Customers:** Seed to Series B startups (10-200 employees) in DevTools, AI/ML, FinTech, SaaS, and Healthcare IT running 3+ AI agents in production using LangChain, CrewAI, AutoGen, or custom orchestration.

**Primary Buyers:** Platform CTOs / VP Engineering managing agent infrastructure, Security Engineers ensuring compliance, and Framework Builders seeking ecosystem integrations.

**Competitive Landscape:** Enterprise NHI platforms (Aembit, Oasis Security, Astrix) target Fortune 500 with 6-month sales cycles and 7-figure contracts. "Build it yourself" costs 2-3 months of platform engineering. AI Identity is purpose-built for startups — deploy today, not next quarter.

## Products

### Identity Service (API)
Agent CRUD, API key lifecycle (issue, rotate with 24-hour grace, revoke), upstream credential vault (Fernet-encrypted storage for OpenAI/Anthropic/Azure keys), and read-only audit log access with HMAC chain verification for compliance.

### Proxy Gateway
Runtime request routing with fail-closed policy enforcement. Every agent request passes through the gateway before reaching the upstream API. Denies by default — only an explicit policy ALLOW permits forwarding. Includes circuit breaker pattern, per-IP and per-agent rate limiting, and key-type enforcement (runtime keys vs. admin keys).

### Dashboard (SPA)
Agent management UI, policy editor, live traffic feed, spend charts, and key rotation controls. React 19, TypeScript, dark-mode-first.

## Vision

Become the default identity layer that every AI agent framework integrates. When an engineering team spins up their first production agent, AI Identity is how they manage its keys, permissions, and audit trail — the same way Stripe is how they handle payments and Auth0 is how they handle user auth.

## Plans

**Near-Term (Q1 2026):**
Launch publicly, acquire 5+ design partners, validate pricing, and gather feedback on the policy DSL and dashboard UX. Target 100+ GitHub stars and 50+ API signups in the first month.

**Mid-Term (Q2-Q3 2026):**
SDK integrations for LangChain, CrewAI, and AutoGen. Agent-to-agent auth (mutual TLS or token exchange). Cost attribution and budget enforcement per agent. SOC 2 Type I preparation leveraging the existing HMAC audit chain.

**Long-Term:**
Become the compliance and governance backbone for multi-agent systems at scale. Expand into agent observability (trace, debug, replay), cross-org agent federation, and enterprise features (SSO, SCIM provisioning, custom policy DSL).

## Charter

**Mission:** Secure the AI agent layer by giving every agent a verifiable identity, least-privilege permissions, and a tamper-proof record of every action it takes.

**Principles:**

1. **Fail closed.** When the system is uncertain, deny. Policy engine timeout, circuit breaker open, missing policy — all result in DENY. Security is never optional.

2. **Defense in depth.** Application-layer query scoping AND database-layer Row Level Security. Fernet encryption at rest AND key prefix extraction instead of plaintext exposure. No single point of trust.

3. **Developer-first.** API-first design, 15-minute deploy, no SDK required. Show code in docs, not marketing screenshots. Earn trust through technical substance.

4. **Audit everything.** Every gateway decision is an immutable, HMAC-chained log entry. Compliance isn't a feature we'll add later — it's baked into the architecture from day one.

5. **Startup speed, enterprise security.** Move fast without cutting security corners. The architecture supports SOC 2 compliance today, not "after we raise our Series A."

## Technical Architecture

```
Client → [Gateway :8002] → Policy Eval → [Upstream API]
              ↕                  ↕
         Rate Limiter      Circuit Breaker
              ↕                  ↕
         [Identity API :8001] ← → [PostgreSQL + RLS]
              ↕
         Audit Log (HMAC chain)
```

**Stack:** Python/FastAPI, PostgreSQL (Neon), SQLAlchemy, React 19/TypeScript/Vite, deployed on GKE Autopilot (API + Gateway) + Vercel (Dashboard). CI/CD via GitHub Actions + Cloud Build.

**Security layers:** SHA-256 key hashing, Fernet credential encryption, HMAC-SHA256 audit integrity chain, PostgreSQL Row Level Security with FORCE, fail-closed gateway enforcement, request sanitization, PII-redacted debug logging.
