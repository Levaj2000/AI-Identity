# AI Identity — Ideal Customer Profile (ICP)

## Product Positioning

**AI Identity** = Identity, permissions, and guardrails for AI agents.
An API proxy that sits between AI agents and external APIs. Each agent gets its own identity (aid_sk_ keys), permissions (policy engine), and guardrails (spend limits, rate controls, audit logging).

**One-liner for outreach:** "We're building the Okta for AI agents — identity, permissions, and audit trails so your agents can call APIs safely."

---

## ICP: Who We Sell To

### Company Profile

| Attribute | Ideal Fit |
|-----------|-----------|
| **Stage** | Seed → Series B (10-200 employees) |
| **Industry** | DevTools, AI/ML platforms, Fintech, SaaS, Healthcare IT |
| **Technical signal** | Running 3+ AI agents in production or late-stage development |
| **Framework signal** | Uses LangChain/LangGraph, CrewAI, AutoGen, or custom agent orchestration |
| **Pain signal** | Managing API keys across agents manually, no audit trail, compliance pressure |
| **Revenue model** | B2B SaaS or platform (agents interact with customer data or external APIs) |
| **Geography** | US, EU, remote-first (English-speaking) |

### Why This Profile?

- **Seed–Series B:** Small enough to adopt new infra quickly, big enough to have real agent usage. Enterprise (Series C+) has longer sales cycles and build-vs-buy committees.
- **DevTools/AI platforms:** Already building agent tooling — they understand the problem natively.
- **3+ agents:** Single-agent teams don't feel the identity/permissions pain. Multi-agent = key sprawl, permission confusion, audit gaps.

---

## Buyer Personas

### Persona 1: The Platform CTO (Primary Buyer)

- **Title:** CTO, VP Engineering, Head of Platform
- **Company:** Series A–B AI/DevTool startup (30-150 people)
- **Day-to-day:** Architecting agent infrastructure, managing API integrations, handling security reviews
- **Pain:**
  - Agents share API keys → one compromised agent exposes everything
  - No audit trail → can't answer "which agent made this API call?"
  - Building auth/permissions in-house → burns engineering time on undifferentiated work
- **Trigger events:**
  - Security audit or SOC 2 prep surfaces agent key management gaps
  - New customer asks "how do you manage agent credentials?"
  - Agent-related incident (unexpected API call, cost spike, data leak)
- **Objections:** "We can build this ourselves" → Counter: "You can, but it'll take 2-3 months of platform eng time. We ship it in a day."
- **Channels:** GitHub, Hacker News, Twitter/X, LangChain/CrewAI Discord

### Persona 2: The Security-Conscious Engineering Lead

- **Title:** Security Engineer, DevSecOps Lead, Staff Engineer
- **Company:** Fintech or Healthcare SaaS running agents (20-100 people)
- **Day-to-day:** Ensuring compliance (SOC 2, HIPAA), managing secrets, reviewing access controls
- **Pain:**
  - Agents have overly broad API permissions
  - No way to enforce least-privilege per agent
  - Audit logs don't capture agent-level identity (just "the app")
- **Trigger events:**
  - Compliance audit asks about non-human identity management
  - Agent makes unauthorized API call → "who did this?"
  - Scaling from 1 agent to 5+ and realizing key management doesn't scale
- **Channels:** Security-focused Slack communities, OWASP, Cloud Security Alliance

### Persona 3: The Agent Framework Builder

- **Title:** Developer Advocate, Framework Maintainer, Open-Source Lead
- **Company:** Agent framework company (CrewAI, LangChain ecosystem, Composio)
- **Day-to-day:** Building integrations, helping developers deploy agents
- **Pain:**
  - Users ask "how do I manage keys for multi-agent setups?"
  - No standard answer — everyone rolls their own
  - Framework doesn't handle identity/auth natively
- **Trigger events:**
  - GitHub issue about key management in multi-agent deployments
  - Enterprise customer asks about agent-level audit trails
  - Looking for integration partners to expand ecosystem
- **Channels:** GitHub, Discord, framework-specific communities

---

## Purchase Triggers (When They Buy)

| Trigger | Urgency | Signal to Look For |
|---------|---------|-------------------|
| **Security incident** — agent calls wrong API, leaks data | 🔴 High | Blog post about incident, hiring security eng |
| **SOC 2 / compliance audit** — auditor asks about NHI management | 🔴 High | Job posting for compliance role, SOC 2 badge pursuit |
| **Scaling agents** — going from 1 to 5+ agents in production | 🟡 Medium | GitHub repos with multiple agent configs, blog about scaling |
| **Enterprise customer request** — customer asks about agent governance | 🟡 Medium | New enterprise tier launch, security page updates |
| **Cost overrun** — agent makes unexpected expensive API calls | 🟡 Medium | Tweets about surprise API bills, blog about cost controls |
| **Build fatigue** — team realizes internal auth system is a maintenance burden | 🟢 Normal | Engineering blog about tech debt, "we rebuilt auth again" posts |

---

## Disqualifiers (Who NOT to Sell To)

- **Pre-product startups** — no agents to manage yet
- **Enterprise (5000+)** — sales cycle too long for our stage, build-vs-buy committees
- **Single-agent hobby projects** — don't feel the multi-agent pain
- **Companies using only hosted agent platforms** (e.g., ChatGPT API directly) — not running custom agents
- **Companies with existing NHI solutions** (CyberArk, Oasis Security) — already solved at enterprise scale
