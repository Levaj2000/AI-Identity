# Design Partner Outreach
**Goal:** 5 design partners by end of Q1 2026 | **Tracking started:** 2026-04-08

---

## Pipeline Summary

| Company | Vertical | Stage | Contact | Status | Last Touch | Next Action |
|---|---|---|---|---|---|---|
| Lindy | AI Automation | Series A | Flo Crivello (CEO) | Not contacted | — | Send initial |
| Composio | DevTools | Seed | Karan Vaidya (CEO) | Not contacted | — | Send initial |
| E2B | DevTools / Infra | Seed | Jakub Novák (CEO) | Not contacted | — | Send initial |
| Dust | Enterprise AI | Series A | Stanislas Polu (CEO) | Not contacted | — | Send initial |
| Ema | Enterprise AI | Series A | Suresh Shanmugham (CEO) | Not contacted | — | Send initial |
| Orby AI | Process Automation | Series A | Bill Chen (CEO) | Not contacted | — | Send initial |
| Cogna | FinTech AI | Seed | — | Not contacted | — | Research contact first |
| Leena AI | HR/IT AI | Series B | Adit Jain (CEO) | Not contacted | — | Send initial |

**Status legend:** Not contacted → Sent → Replied → Call scheduled → Partner signed → Passed

---

## Follow-Up Schedule

Once initial outreach is sent, follow up on:
- **Day 5** — One short bump (included below per company)
- **Day 12** — Value-add nudge with a specific resource
- **Day 21** — Final close or move to nurture

---

## Target Profiles & Messages

---

### 1. Lindy (lindy.ai)
**What they do:** AI automation platform — users build AI "employees" that run workflows autonomously, calling tools and external APIs continuously.
**Why they're a fit:** They have users running multi-agent workflows in production with API credentials flowing through automations. Every Lindy workflow touches external API keys. Their users (and Lindy's own infrastructure) have exactly the "which agent called what, and how much did it cost?" problem.
**Contact:** Flo Crivello, CEO — flo@lindy.ai (verified from public profile)

#### Initial message
> Subject: AI agent identity for Lindy builders
>
> Hey Flo —
>
> My name is Jeff Leva. Sorry for the unexpected email.
>
> I'm building a SaaS product, AI Identity — cryptographic API key management and audit trails for AI agents. Basically, each agent gets its own scoped key, rate limit, and tamper-proof log. When something goes wrong (runaway API spend, a leaked key, a compliance question), you can replay exactly what happened.
>
> Are Lindy builders running into this? The moment someone's automation starts calling OpenAI + Slack + external APIs on their behalf, there's no visibility into which workflow triggered which call or how much it costs per agent.
>
> If this aligns with what you're seeing, it's free to try at ai-identity.co — docs and a live demo are there. I'm looking for 5 design partners to help shape what we build next; happy to jump on a call if you have questions after poking around.
>
> — Jeff

#### Day 5 follow-up
> Hey Flo — just bumping this in case it got buried. Happy to send a 1-pager if that's easier to forward internally.

#### Day 12 follow-up
> Flo — sharing this in case it's useful: [link to forensics reference architecture doc when published]. The short version: most agent platforms log what happened, but none produce a chain-verified record that's independently verifiable for compliance. That gap matters more as Lindy moves into enterprise. Let me know if worth a call.

---

### 2. Composio (composio.dev)
**What they do:** Integration infrastructure for AI agents — prebuilt tools and connectors that agent frameworks (LangChain, CrewAI, AutoGen) call at runtime.
**Why they're a fit:** Composio sits at the exact layer where agent actions and credentials intersect. Their developers are building agents that call 100+ external APIs. The "which agent made this call?" problem is Composio's native environment.
**Contact:** Karan Vaidya, CEO — reach via LinkedIn or karan@composio.dev

#### Initial message
> Subject: Scoped API keys for agents using Composio
>
> Hey Karan —
>
> My name is Jeff Leva. Sorry for the unexpected email.
>
> I'm building a SaaS product, AI Identity — per-agent API key management and audit trails, deployable in ~15 minutes alongside existing LangChain/CrewAI setups.
>
> Are your users running into this? Composio sits at the tool execution layer — credentials for agents at scale, but the pattern I keep seeing is one shared API key across all agents, no spend visibility per agent, no tamper-proof log when something goes sideways.
>
> If it resonates, it's free to try at ai-identity.co — docs and a demo are there. I'm looking for 5 design partners to shape what gets built next; happy to talk if you have questions after taking a look.
>
> — Jeff

#### Day 5 follow-up
> Hey Karan — just following up. Even a quick "not the right time" is useful signal for me. Would love your honest read.

#### Day 12 follow-up
> Karan — I wrote up a comparison of the "build vs. buy" decision for agent credential management (engineering hours vs. integration overhead). Sends it if it's helpful. Still happy to do a quick call if timing works.

---

### 3. E2B (e2b.dev)
**What they do:** Code execution sandboxes for AI agents — lets agents run code safely in isolated environments. Used by LangChain, Vercel AI SDK, and others.
**Why they're a fit:** E2B agents are executing code that often needs API credentials passed in. Their users are sophisticated developers who care about security at the infrastructure layer. Strong technical overlap, and they'd likely want SDK-level integration.
**Contact:** Jakub Novák, CEO — jakub@e2b.dev

#### Initial message
> Subject: Identity layer for E2B agents
>
> Hey Jakub —
>
> My name is Jeff Leva. Sorry for the unexpected email.
>
> I'm building a SaaS product, AI Identity — each agent gets its own cryptographic API key, policy set, and HMAC-chained audit log. One URL change to add to an existing agent setup.
>
> Are E2B users hitting this? Your sandboxes execute agent code that often has credentials injected at runtime — but there's no standard for scoping those credentials per-execution or tracking which sandbox session called which upstream API.
>
> If it's relevant, it's free to try at ai-identity.co — docs and a demo are there. I'm looking for 5 design partners to shape what we build next; happy to talk if questions come up.
>
> — Jeff

#### Day 5 follow-up
> Hey Jakub — bumping this in case timing was bad. No pressure — even a "not our problem right now" is useful to hear.

#### Day 12 follow-up
> Jakub — we just shipped per-agent spend caps alongside the key management layer. Curious if that's a pain your users are hitting (runaway API costs from agent loops). Worth a quick sync?

---

### 4. Dust (dust.tt)
**What they do:** AI assistant platform for enterprise teams — companies build internal assistants using GPT-4, Claude, and custom data. Agents are collaborative and deal with sensitive company data.
**Why they're a fit:** Dust is in enterprise with compliance-sensitive customers (financial services, legal). Their agents are touching internal company data and calling external APIs. Tamper-proof audit trails are directly relevant to their enterprise customers' security reviews.
**Contact:** Stanislas Polu, CEO — spolu@dust.tt

#### Initial message
> Subject: Compliance-grade audit trails for Dust agents
>
> Hey Stanislas —
>
> My name is Jeff Leva. Sorry for the unexpected email.
>
> I'm building a SaaS product, AI Identity — cryptographic identity per agent, scoped API keys, and a tamper-proof audit log. Think of it as the layer between your agents and the upstream APIs they call, with a chain-verified record of every action.
>
> Is this coming up for Dust's enterprise customers? Security teams are increasingly asking "what exactly did the agent access and when, and can we prove it independently?" — and log-based audit doesn't hold up well in a real security review.
>
> If it's relevant, it's free to explore at ai-identity.co — docs and a demo are there. I'm looking for design partners whose enterprise customer feedback directly shapes what we build next; happy to talk if questions come up after you've had a look.
>
> — Jeff

#### Day 5 follow-up
> Hey Stanislas — just following up on this. Totally understand if timing isn't right.

#### Day 12 follow-up
> Stanislas — I put together a short explainer on the difference between log-based audit trails and HMAC-chained forensic records for regulated industries. Happy to share. Enterprise security teams are asking for this in procurement reviews — might be useful context for Dust's sales process.

---

### 5. Ema (ema.co)
**What they do:** Enterprise AI employee platform — companies deploy AI "employees" that handle workflows across HR, IT, finance, and operations. Claims 200+ enterprise integrations.
**Why they're a fit:** Ema's agents are running inside large enterprises with strict compliance requirements. Their customers are in finance and healthcare. The audit trail and credential management story maps directly to their enterprise procurement blockers.
**Contact:** Suresh Shanmugham, CEO — suresh@ema.co

#### Initial message
> Subject: Tamper-proof audit trails for Ema agents in regulated industries
>
> Hey Suresh —
>
> My name is Jeff Leva. Sorry for the unexpected email.
>
> I'm building a SaaS product, AI Identity — governance infrastructure for AI agents: cryptographic identity per agent, least-privilege API key management, and HMAC-chained audit logs that are independently verifiable.
>
> Is this coming up in Ema's enterprise sales? You're selling into regulated industries — finance, healthcare, insurance — where compliance teams are asking "can you prove what the agent accessed, and can we verify that record wasn't altered?" A log entry inside the vendor's infrastructure isn't sufficient for a SOX or HIPAA audit. A tamper-evident chain is.
>
> If it maps to something you're navigating, it's free to explore at ai-identity.co — docs and a live demo are there. I'm looking for 5 design partners; happy to talk through specifics if questions come up after you've taken a look.
>
> — Jeff

#### Day 5 follow-up
> Hey Suresh — bumping this. If it's the wrong time or wrong contact, feel free to point me in a better direction.

#### Day 12 follow-up
> Suresh — we published a short piece on what "compliance-ready agent governance" means in regulated procurement. Shares it in case it's useful for Ema's enterprise sales conversations.

---

### 6. Orby AI (orby.ai)
**What they do:** Generative AI automation for enterprise processes — combines computer vision, NLP, and AI agents to automate complex workflows. Series A, focused on finance and ops.
**Why they're a fit:** Orby agents are executing automated business processes — invoicing, reconciliation, procurement workflows. These touch sensitive financial systems and external APIs. Credential scoping and audit trails are directly relevant.
**Contact:** Bill Chen, CEO — bill@orby.ai

#### Initial message
> Subject: Per-agent API key management for Orby workflows
>
> Hey Bill —
>
> My name is Jeff Leva. Sorry for the unexpected email.
>
> I'm building a SaaS product, AI Identity — a governance layer for AI agents that gives each agent its own scoped API key, policy set, and an immutable audit trail with hash-chain integrity.
>
> Are Orby's customers asking about this? You're running agents that touch ERP systems, billing platforms, and external APIs on behalf of enterprise customers — the "which agent made this API call?" and "can we prove what it accessed for an audit?" questions seem live for that use case.
>
> If it resonates, it's free to try at ai-identity.co — docs and a demo are there. I'm looking for design partners; happy to talk through anything if questions come up after you've poked around.
>
> — Jeff

#### Day 5 follow-up
> Hey Bill — just following up. Happy to share a quick overview async if a call isn't convenient right now.

#### Day 12 follow-up
> Bill — we added spend caps per agent this week. For finance automation specifically, runaway API costs from workflow loops are a real exposure. Wanted to flag in case it's useful context for your customers.

---

### 7. Cogna (cogna.co)
**What they do:** AI agents for financial operations — automated workflows for finance teams (billing, reconciliation, reporting).
**Why they're a fit:** FinTech + AI agents + enterprise = highest audit sensitivity of any vertical. Strong design partner candidate for compliance use case.
**Contact:** Research needed — check LinkedIn for founder/CEO name before outreach.
**Note:** Find the founder before sending — don't send to a generic inbox.

#### Initial message (draft — fill in name)
> Subject: Compliance-grade audit trails for Cogna agents
>
> Hey [Name] —
>
> My name is Jeff Leva. Sorry for the unexpected email.
>
> I'm building a SaaS product, AI Identity — governance infrastructure for AI agents running in regulated environments: cryptographic identity per agent, scoped API keys, and HMAC-chained audit logs that are independently verifiable by an auditor.
>
> Is this something Cogna's customers are asking about? Finance operations is the sharpest use case — SOX and internal audit requirements mean "the agent accessed X at time Y" needs to be provable, not just logged. Log-based records inside the vendor's system don't satisfy a serious audit.
>
> If it resonates, it's free to try at ai-identity.co — docs and a demo are there. I'm looking for 5 design partners to directly shape what we build next; happy to talk if questions come up.
>
> — Jeff

---

### 8. Leena AI (leena.ai)
**What they do:** Enterprise AI agents for HR and IT service management — handles employee onboarding, helpdesk, policy questions. Series B, strong enterprise customer base.
**Why they're a fit:** HR/IT AI agents are touching sensitive employee data and internal systems. GDPR, SOC 2, and internal IT security policies make audit trails non-optional.
**Contact:** Adit Jain, CEO — adit@leena.ai

#### Initial message
> Subject: Agent audit trails for Leena's enterprise customers
>
> Hey Adit —
>
> My name is Jeff Leva. Sorry for the unexpected email.
>
> I'm building a SaaS product, AI Identity — per-agent cryptographic identity, API key scoping, and tamper-proof audit logs for AI agents in production.
>
> Are Leena's enterprise customers asking about this? Especially in healthcare and financial services, compliance questions go beyond what a standard log can answer: "What data did the agent access for this employee? Who authorized that? Can we prove the record wasn't modified?" That's the gap AI Identity fills.
>
> If it resonates, it's free to try at ai-identity.co — docs and a demo are there. I'm looking for 5 design partners to shape what gets built next; happy to talk if questions come up after you've had a look.
>
> — Jeff

#### Day 5 follow-up
> Hey Adit — bumping this. Happy to send a one-pager if that's easier to route.

#### Day 12 follow-up
> Adit — we have several customers in HR tech where the GDPR "right to explanation" requirement is driving the audit trail need. Happy to share what we've learned if it's useful for Leena's compliance conversations.

---

## Outreach Log

| Date | Company | Contact | Channel | Type | Notes |
|---|---|---|---|---|---|
| — | — | — | — | — | No outreach sent yet |

---

## How to Use This File

**Sending initial outreach:**
1. Pick a company from the pipeline table marked "Not contacted"
2. Find the message under their section above
3. Copy, personalize one specific detail (mention a recent funding round, product launch, or blog post), send
4. Update the Pipeline Summary table status to "Sent" and log it in the Outreach Log

**Follow-ups:**
- Day 5 and Day 12 messages are pre-written above each company
- The tracker (when pipeline data exists) will tell you who is due for follow-up today

**Updating status:**
- Change status in the Pipeline Summary table as conversations progress
- Add rows to the Outreach Log for every touch

**Adding new targets:**
- Add a row to the Pipeline Summary table
- Add a section below with their profile + 3 messages
- Include why they're a fit — helps calibrate whether to invest time

---

*Last updated: 2026-04-10*
