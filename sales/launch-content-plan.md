# AI Identity — Launch Content Plan

> Blog post outlines, Show HN draft, Twitter/X thread, community distribution list, and content calendar.

---

## Content Pillars

Every piece maps to one of three pillars that ladder up to the product:

| Pillar | Theme | Target Persona |
|--------|-------|----------------|
| **Problem Awareness** | "Shared API keys are a shared password" — why the status quo breaks at scale | Platform CTO, Security Lead |
| **Architecture Education** | "How per-agent identity works" — technical deep dive, code examples | Platform CTO, Framework Builder |
| **Category Creation** | "Agent Identity Management is a thing now" — define the space | All personas, investors, community |

---

## Blog Post Outlines

### Blog Post 1: "Your AI Agents Share One API Key. Here's Why That Breaks."

**Pillar:** Problem Awareness
**Target keyword:** `AI agent API key management`
**Search intent:** Informational — developers searching for how to manage keys across agents
**Funnel stage:** Top of funnel (awareness)

**Outline:**

1. **Hook** — You have 5 agents calling the OpenAI API. They all use the same key. What happens when one gets compromised?
2. **The shared-key problem** — Walk through 3 failure modes:
   - Security: one leaked key exposes all agents
   - Cost: one runaway agent burns the entire budget — no attribution
   - Audit: "which agent made this call?" — no answer
3. **Why teams end up here** — It's the fastest path. One key in `.env`, shared across all agents. Works until it doesn't.
4. **What per-agent identity looks like** — Each agent gets its own key, scoped permissions, and an audit trail. Show a before/after architecture diagram.
5. **The 3 things every multi-agent system needs:**
   - Per-agent API keys (unique identity)
   - Least-privilege permissions (scoped access)
   - Immutable audit logs (who did what, when)
6. **CTA** — "We built AI Identity to solve exactly this. Try it in 15 minutes." Link to quickstart.

**Distribution:** Hacker News (standalone post), Reddit r/MachineLearning, r/LangChain, Dev.to, Hashnode, company blog.

---

### Blog Post 2: "Building an Identity Layer for AI Agents — Architecture Deep Dive"

**Pillar:** Architecture Education
**Target keyword:** `AI agent identity layer architecture`
**Search intent:** Informational — engineers evaluating how to build or buy agent auth
**Funnel stage:** Middle of funnel (consideration)

**Outline:**

1. **Hook** — When we added a fifth agent to our system, we realized we had no idea which one was calling which API. Here's how we built the identity layer.
2. **Architecture overview** — Diagram: Agent → Gateway (auth + policy) → External API. Three components: Identity Service, Policy Engine, Audit Logger.
3. **Identity Service deep dive:**
   - Agent registration: `POST /agents` → UUID + `aid_sk_` key
   - Key lifecycle: create → rotate (24hr grace) → revoke
   - SHA-256 hashing, show-once pattern, key prefix for identification
   - Code snippet: `curl` to create an agent, get the key
4. **Policy Engine design decisions:**
   - Per-agent rules (JSONB) — what this agent can access
   - Allow/deny decisions logged with every request
   - Why we chose JSONB over a DSL
5. **Audit trail that actually works:**
   - Every request logged: agent_id, endpoint, method, decision, latency, cost
   - Immutable — append-only, no edits, no deletes
   - Queryable: "show me all denied requests for agent X in the last 24 hours"
6. **What we learned building this:**
   - Key rotation grace periods are non-negotiable (agents crash on instant revocation)
   - Metadata on agents (framework, environment, team) is critical for filtering
   - Separate identity service from gateway — different scaling needs
7. **CTA** — "The code is live. Here's how to set it up." Link to GitHub + quickstart.

**Distribution:** Hacker News (ideal for this style), Dev.to, Hashnode, personal blog cross-post, LangChain community Discord.

---

### Blog Post 3: "NHI Management for Startups: Why Enterprise Solutions Don't Fit"

**Pillar:** Category Creation
**Target keyword:** `non-human identity management startups`
**Search intent:** Informational/commercial — security-minded devs evaluating options
**Funnel stage:** Middle of funnel (consideration)

**Outline:**

1. **Hook** — Gartner says non-human identities outnumber human identities 90:1. Enterprise has CyberArk, Aembit, and Astrix. What do startups have? Nothing.
2. **The NHI landscape today:**
   - Define NHI: service accounts, API keys, OAuth tokens, CI/CD creds, and now — AI agents
   - Enterprise players: Aembit (workload IAM), Oasis Security ($40M, NHI management), Astrix (NHI security)
   - The gap: all of them target Fortune 500 with 6-month procurement cycles
3. **Why AI agents are different from other NHIs:**
   - Agents make autonomous decisions — they're not just reading data
   - Agent behavior is non-deterministic — you can't predict every API call
   - Agents call external APIs with real cost and real consequences
   - Traditional NHI tools manage credentials — agents need identity, permissions, AND guardrails
4. **What startups actually need:**
   - Deploy in 15 minutes, not 15 weeks
   - API-first, not dashboard-first
   - Pay-as-you-grow pricing, not 7-figure contracts
   - Works with LangChain, CrewAI, AutoGen — not just enterprise LDAP
5. **Introducing Agent Identity Management (AIM):**
   - A new subcategory of NHI — purpose-built for AI agents
   - Core primitives: agent identity, scoped permissions, policy enforcement, audit trail
   - Why this matters now: agents are hitting production, compliance is catching up
6. **CTA** — "We're building the identity layer for this new world. Check out AI Identity."

**Distribution:** Hacker News, Reddit r/netsec, r/cybersecurity, LinkedIn (long-form post), Dev.to, security Slack communities.

---

## Show HN Draft

```
Show HN: AI Identity – Per-agent API keys, permissions, and audit trails for AI agents

Hey HN,

I've been building multi-agent systems and kept running into the same problem:
all my agents shared one API key. When one agent made an unexpected call, I had
no idea which one did it. When I needed to revoke access for one agent, I had to
rotate the key for all of them.

So I built AI Identity — an API proxy that gives each AI agent its own identity.

What it does:
- Each agent gets a unique API key (aid_sk_ prefix, SHA-256 hashed, show-once)
- Key rotation with 24-hour grace period (no downtime during rotation)
- Per-agent permissions via a policy engine
- Immutable audit log: which agent called which API, when, and what the decision was

Stack: Python/FastAPI, PostgreSQL (Neon), React/TypeScript dashboard.
API is live at https://ai-identity-api.onrender.com/docs

The identity service has 9 endpoints (agent CRUD + key management). The gateway
sits between your agents and external APIs — it authenticates the agent key,
evaluates policies, and logs every request.

Think of it as Okta for AI agents, but built for startups running 3-50 agents,
not enterprises with 6-month procurement cycles.

GitHub: https://github.com/Levaj2000/AI-Identity
API docs: https://ai-identity-api.onrender.com/docs
Quickstart: https://github.com/Levaj2000/AI-Identity/blob/main/QUICKSTART.md

Would love feedback on the API design and the policy engine approach. Happy to
answer any questions about the architecture.
```

**Show HN best practices applied:**
- Title is explicit — tells you exactly what it is
- Leads with the personal pain point, not a pitch
- Talks to HN as fellow builders
- No superlatives — no "revolutionary" or "game-changing"
- Links to GitHub repo (HN loves open code)
- Links to live API docs (show, don't tell)
- Ends with a specific question to drive discussion
- Modest tone — acknowledges it's early stage

**Timing:** Post Tuesday or Wednesday, 8-9 AM EST (peak HN traffic).

---

## Twitter/X Thread Outline

**Thread: "I gave each of my AI agents its own API key. Here's what happened."**

> **Tweet 1 (Hook):**
> I gave each of my AI agents its own API key.
>
> Within a week I found:
> - One agent making 3x more calls than expected
> - Two agents hitting the same endpoint (redundant work)
> - Zero way to trace this before
>
> Here's what I built 🧵

> **Tweet 2 (Problem):**
> Most multi-agent systems share one API key.
>
> That means:
> → One compromised agent = every API exposed
> → One runaway agent = your entire bill
> → "Which agent did this?" = 🤷
>
> It's a shared password with extra steps.

> **Tweet 3 (What it does):**
> AI Identity gives each agent:
>
> 1. A unique API key (aid_sk_ prefix)
> 2. Scoped permissions (what it CAN access)
> 3. Full audit trail (what it DID access)
>
> Deploy in 15 minutes. Not 15 weeks.

> **Tweet 4 (Architecture):**
> How it works:
>
> Agent → Gateway → External API
>
> The gateway authenticates the agent key, checks the policy, and logs the decision.
>
> Allow, deny, or rate-limit — per agent, per endpoint.
>
> [Attach: architecture diagram]

> **Tweet 5 (Key rotation):**
> Key rotation without downtime:
>
> → New key issued, old key gets a 24-hour grace period
> → Both keys valid during transition
> → Old key auto-revokes after 24 hours
>
> No more "rotate the key and pray nothing breaks."

> **Tweet 6 (Who it's for):**
> Built for teams running 3-50 AI agents.
>
> If you use LangChain, CrewAI, or custom orchestration — and you share one API key across agents — this is for you.
>
> Not for enterprise with 6-month procurement cycles.

> **Tweet 7 (CTA):**
> API is live. 59 tests passing. MIT licensed.
>
> GitHub: [link]
> Live API docs: [link]
> Show HN: [link]
>
> Would love feedback from anyone building multi-agent systems.
>
> What's your current approach to agent key management?

**Format notes:**
- 7 tweets, each self-contained (works if someone sees just one)
- Hook tweet uses a list (high engagement format on X)
- Include one architecture diagram image (tweet 4)
- End with a question to drive replies
- No hashtags (they reduce reach on X in 2026)

---

## Community Distribution List

### Tier 1 — High-fit, post on launch day

| Community | Platform | Where to Post | Notes |
|-----------|----------|--------------|-------|
| **Hacker News** | Web | Show HN | The anchor. Post first, Tuesday 8-9 AM EST. |
| **r/MachineLearning** | Reddit | Main sub | Frame as architectural insight, not product launch |
| **r/LangChain** | Reddit | Main sub | Highly relevant — their users feel this pain |
| **LangChain Discord** | Discord | #showcase or #general | Many multi-agent builders here |
| **CrewAI Discord** | Discord | #showcase | CrewAI users run multi-agent systems by default |
| **Twitter/X** | X | Thread from personal account | Tag relevant builders: @LangChainAI, @craborai |

### Tier 2 — Post within 48 hours of launch

| Community | Platform | Where to Post | Notes |
|-----------|----------|--------------|-------|
| **r/LocalLLaMA** | Reddit | Main sub | Builders running local agents with API integrations |
| **r/netsec** | Reddit | Main sub | Blog post 3 (NHI angle) — security audience |
| **r/cybersecurity** | Reddit | Main sub | Same NHI angle, broader audience |
| **Dev.to** | Web | Blog cross-post | Cross-post blog post 1 or 2 |
| **Hashnode** | Web | Blog cross-post | Cross-post blog post 2 (architecture) |
| **Anthropic Discord** | Discord | #projects | Claude-powered agents need identity too |
| **OpenAI Discord** | Discord | #developers | GPT-based agents are the largest agent cohort |

### Tier 3 — Post within 1 week of launch

| Community | Platform | Where to Post | Notes |
|-----------|----------|--------------|-------|
| **LinkedIn** | LinkedIn | Long-form post | NHI/security angle for the security lead persona |
| **AutoGen Discord** | Discord | #showcase | Microsoft AutoGen multi-agent framework users |
| **Indie Hackers** | Web | Product launch | Frame as solo-founder building infra product |
| **Product Hunt** | Web | Product launch | Schedule for day after Show HN (stagger launches) |
| **AI Engineer Discord** | Discord | Relevant channel | Builders architecting agent systems |
| **OWASP Slack** | Slack | Security channel | NHI security angle for security leads |

### Community engagement rules:
- **Be a member before you post** — join communities 1-2 weeks before launch, participate genuinely
- **Lead with the problem, not the product** — "here's what I learned building multi-agent auth" > "check out my product"
- **Answer every comment** — engagement in the first 2 hours is critical
- **No cross-posting identical text** — tailor the message to each community's culture
- **Reddit:** never post product links directly. Write a text post with the insight, link in comments.

---

## Content Calendar

### Pre-Launch (Week of March 17-21)

| Date | Content | Channel | Owner | Status |
|------|---------|---------|-------|--------|
| Mon 3/17 | Join LangChain, CrewAI, Anthropic Discord servers | Discord | Marketing | Pending |
| Mon 3/17 | Follow/engage with AI agent builders on X | Twitter/X | Marketing | Pending |
| Tue 3/18 | Publish Blog Post 1: "Your AI Agents Share One API Key" | Company blog | Marketing | Pending |
| Wed 3/19 | Cross-post Blog Post 1 to Dev.to | Dev.to | Marketing | Pending |
| Thu 3/20 | Share Blog Post 1 in r/LangChain (text post, problem-focused) | Reddit | Marketing | Pending |
| Fri 3/21 | Engage in 3-5 Discord conversations about agent architecture | Discord | Marketing | Pending |

### Launch Week (Week of March 24-28)

| Date | Content | Channel | Owner | Status |
|------|---------|---------|-------|--------|
| Mon 3/24 | Publish Blog Post 2: "Building an Identity Layer" (architecture) | Company blog | Marketing | Pending |
| **Tue 3/25** | **LAUNCH DAY** | | | |
| | → Show HN post (8:30 AM EST) | Hacker News | CEO | Pending |
| | → Twitter/X thread (9:00 AM EST) | Twitter/X | CEO | Pending |
| | → Cross-post Blog Post 2 to Hashnode | Hashnode | Marketing | Pending |
| | → Post in LangChain Discord #showcase | Discord | Marketing | Pending |
| | → Post in CrewAI Discord #showcase | Discord | Marketing | Pending |
| | → Monitor HN comments, respond to all (full day) | Hacker News | CEO | Pending |
| Wed 3/26 | Product Hunt launch | Product Hunt | CEO | Pending |
| Wed 3/26 | Post in r/MachineLearning (architecture angle) | Reddit | Marketing | Pending |
| Thu 3/27 | Post in Anthropic + OpenAI Discord | Discord | Marketing | Pending |
| Thu 3/27 | LinkedIn long-form post (NHI security angle) | LinkedIn | CEO | Pending |
| Fri 3/28 | Publish Blog Post 3: "NHI Management for Startups" | Company blog | Marketing | Pending |

### Post-Launch (Week of March 31 – April 4)

| Date | Content | Channel | Owner | Status |
|------|---------|---------|-------|--------|
| Mon 3/31 | Cross-post Blog Post 3 to Dev.to | Dev.to | Marketing | Pending |
| Mon 3/31 | Post in r/netsec and r/cybersecurity (NHI angle) | Reddit | Marketing | Pending |
| Tue 4/1 | Post on Indie Hackers (solo-founder angle) | Indie Hackers | CEO | Pending |
| Wed 4/2 | Compile launch metrics: HN points, GitHub stars, signups | Internal | Marketing | Pending |
| Thu 4/3 | Write "What we learned from launching on HN" Twitter thread | Twitter/X | CEO | Pending |
| Fri 4/4 | Reach out to top 5 engaged commenters for design partner conversations | Direct | Sales | Pending |

### Ongoing (April 7+)

| Cadence | Content | Channel |
|---------|---------|---------|
| Weekly | 1 technical tweet or thread about agent architecture | Twitter/X |
| Biweekly | 1 blog post (alternate: tutorial / opinion piece) | Company blog + cross-post |
| Monthly | 1 community AMA or Discord office hours | LangChain or CrewAI Discord |
| Monthly | Retrospective: traffic sources, signup funnel, top content | Internal dashboard |

---

## Success Metrics

| Metric | Launch Week Target | 30-Day Target |
|--------|-------------------|---------------|
| HN upvotes | 50+ | — |
| GitHub stars | 100+ | 250+ |
| API signups (unique users) | 20+ | 50+ |
| Blog post views (total) | 2,000+ | 5,000+ |
| Twitter/X thread impressions | 10,000+ | — |
| Design partner conversations started | 3+ | 5+ |
| Discord community members | — | 25+ |

---

*Last updated: 2026-03-11*
