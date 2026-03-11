# AI Identity — Brand Brief

> One-page brand identity reference for landing page, marketing, and sales collateral.

---

## Positioning Statement

**For engineering teams running AI agents in production** who need to manage API keys, permissions, and audit trails across multiple agents, **AI Identity is the identity and access management layer** that gives each agent its own identity, scoped permissions, and full audit trail. **Unlike enterprise NHI platforms** (Aembit, Oasis Security, Astrix) that target Fortune 500 with 6-month sales cycles, **AI Identity is built for startups and mid-stage teams** — deploy in 15 minutes, not 15 weeks.

---

## Tagline Candidates

| # | Tagline | When to Use |
|---|---------|-------------|
| 1 | **Identity for AI agents.** | Default — website hero, social bios, pitch decks |
| 2 | **Know which agent did what.** | Pain-driven — outreach emails, conference talks |
| 3 | **The Okta for AI agents.** | Analogy — investor conversations, cold outreach to CTOs |
| 4 | **Every agent gets an identity.** | Product-focused — docs, onboarding, developer landing page |
| 5 | **Agent keys. Agent rules. Agent logs.** | Feature-driven — technical blog posts, GitHub README |

**Primary tagline:** "Identity for AI agents." — short, clear, category-defining.

**Elevator pitch (15 seconds):** "AI Identity gives each of your AI agents its own API key, scoped permissions, and audit trail. Think Okta but for agents instead of humans. Deploy in 15 minutes."

---

## Voice & Tone

### Voice Attributes

| Attribute | What It Means | What It Doesn't Mean |
|-----------|---------------|----------------------|
| **Technical** | Use real terms (API keys, least-privilege, audit logs). Show code examples. | Don't dumb it down or use vague marketing language. |
| **Direct** | Get to the point. Lead with the problem, then the solution. | Don't hedge, waffle, or bury the value in paragraphs. |
| **Confident** | We know this problem well. We built the right solution. | Don't oversell — we're pre-revenue, not "the #1 platform." |
| **Developer-first** | Write for the person who'll `curl` the API, not the person who'll read the slide deck. | Don't write for procurement. Don't use enterprise jargon. |
| **Honest** | Say what we do and don't do. Acknowledge we're early. | Don't fake scale, namedrop customers we don't have, or claim awards. |

### Tone by Context

| Context | Tone | Example |
|---------|------|---------|
| Landing page | Clear, confident, concise | "Each agent gets its own identity. You get a full audit trail." |
| Documentation | Precise, helpful, no-BS | "POST /agents creates an agent and returns an aid_sk_ key." |
| Blog posts | Thoughtful, opinionated, technical | "Most teams share one API key across all agents. Here's why that breaks." |
| Outreach emails | Curious, specific, respectful | "How are you managing API keys across your agents today?" |
| Social media | Sharp, punchy, value-first | "Your agents share one API key. That's a shared password with extra steps." |
| Error messages | Helpful, actionable | "Key expired. Rotate via POST /agents/{id}/keys/rotate." |

### Words We Use

- Agent identity, agent key, scoped permissions, audit trail
- Per-agent, least-privilege, key rotation, grace period
- Gateway, proxy, policy engine, decision log
- Deploy in minutes, not months

### Words We Avoid

- "Revolutionary", "game-changing", "next-generation"
- "AI-powered" (we're not AI — we manage AI agents)
- "Enterprise-grade" (we're startup-grade, by design)
- "Seamless", "frictionless", "end-to-end"
- "Solution" as a noun

---

## Visual Identity

### Color Palette

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| **Primary** | Electric Indigo | `#4F46E5` | Buttons, links, key UI accents, logo mark |
| **Primary Dark** | Deep Indigo | `#3730A3` | Hover states, active elements |
| **Secondary** | Cyan Accent | `#06B6D4` | Status indicators, success states, code highlights |
| **Background** | Near Black | `#0F172A` | Page backgrounds, hero sections (dark mode default) |
| **Surface** | Dark Slate | `#1E293B` | Cards, panels, code blocks |
| **Text Primary** | Off White | `#F8FAFC` | Body text on dark backgrounds |
| **Text Secondary** | Cool Gray | `#94A3B8` | Secondary text, labels, captions |
| **Danger** | Red | `#EF4444` | Errors, revoked status, destructive actions |
| **Warning** | Amber | `#F59E0B` | Expiring keys, at-risk states |
| **Success** | Emerald | `#10B981` | Active keys, successful operations |

**Why this palette:**
- **Indigo** — distinct from Okta's blue (#007DC1) and Auth0's orange. Signals trust + technical depth without copying established players.
- **Dark-mode first** — developer tools default to dark. Our brand should feel native in a terminal, IDE, or dashboard.
- **Cyan accent** — complements indigo, provides energy without competing. Works well for code syntax highlighting.

### Typography

| Role | Font | Fallback | Usage |
|------|------|----------|-------|
| **Headings** | Inter | system-ui, sans-serif | Page titles, section headers, UI labels |
| **Body** | Inter | system-ui, sans-serif | Paragraphs, descriptions, form text |
| **Code** | JetBrains Mono | monospace | API keys (`aid_sk_...`), code snippets, terminal output |

**Why Inter:** Open-source, excellent readability at all sizes, widely used in developer tools (GitHub, Vercel, Linear). Feels technical without being cold.

### Logo Direction

- **Wordmark + mark** — "AI Identity" in Inter Bold, paired with a simple geometric mark
- **Mark concept:** Abstract key/shield hybrid — conveys identity (key) and security (shield) without being literal
- **Monochrome** — must work in single color (white on dark, indigo on light)
- **Sizing:** Mark works at 24px (favicon) through 200px (hero)

### UI Principles

1. **Dark mode default** — light mode optional, dark is the primary experience
2. **Dense but readable** — developers want information density, not white space
3. **Code is UI** — API keys, endpoints, and JSON should look beautiful, not bolted on
4. **Status is color** — green (active), amber (expiring), red (revoked) at a glance
5. **Motion is functional** — animate state changes (key rotation, policy updates), not decorations

---

## Competitive Messaging

### vs. "Build It Yourself"

> *"You can build agent auth in-house. It'll take 2-3 months of platform engineering time, and you'll rebuild it every time requirements change. Or you can deploy AI Identity in 15 minutes and ship your actual product."*

**Key message:** We eliminate undifferentiated infrastructure work so your team can focus on what makes your product unique.

### vs. Aembit (Workload IAM)

> *"Aembit is workload IAM for enterprise — great for managing thousands of microservices at scale. AI Identity is purpose-built for AI agents — per-agent keys, agent-aware policies, and an audit trail that tracks agent decisions, not just API calls."*

**Key message:** Built for agents, not adapted from legacy IAM. Agent-native from day one.

### vs. Oasis Security / Astrix Security (Enterprise NHI)

> *"Oasis and Astrix manage non-human identities across the enterprise — service accounts, API keys, OAuth tokens, CI/CD pipelines. That's a 6-month procurement process and a 7-figure contract. AI Identity focuses on one thing: AI agent identity. Deploy today, not next quarter."*

**Key message:** Focused scope, startup speed, developer-first experience.

### vs. Shared API Keys (Status Quo)

> *"Shared API keys are a shared password. One compromised agent exposes every API. One runaway agent runs up every bill. One audit question — 'which agent did this?' — and you have no answer."*

**Key message:** The status quo is a ticking time bomb. Per-agent identity is the fix.

---

## Messaging Hierarchy

| Level | Message | Use Case |
|-------|---------|----------|
| **Tagline** | Identity for AI agents. | Logo lockups, social bios, meta titles |
| **One-liner** | AI Identity gives each agent its own API key, permissions, and audit trail. | Website hero subtitle, email signatures |
| **Elevator pitch** | AI Identity is the Okta for AI agents. Each agent gets its own identity, scoped permissions, and a full audit trail. It takes 15 minutes to set up — register your agent, get a key, and route traffic through our gateway. We enforce permissions and log every call. | Investor meetings, conference intros, DMs |
| **Full description** | AI Identity is an API proxy that sits between AI agents and external APIs. Each agent gets a unique identity (aid_sk_ keys), scoped permissions (policy engine with least-privilege enforcement), and guardrails (spend limits, rate controls, immutable audit logs). For engineering teams running multi-agent systems, we answer the question every auditor, customer, and incident responder will ask: "Which agent did what, when, and why?" | Landing page body, blog intros, press kit |

---

*Last updated: 2026-03-11*
