# AI Identity — Outreach Templates

> 3 cold email templates, 2 DM templates, and a follow-up cadence.
> Personalize the `{{variables}}` before sending.

---

## Cold Email Templates

### Template 1: Platform CTO — "The Build-vs-Buy"

**Subject:** `How {{company}} handles agent API keys at scale`

**Body:**

Hi {{first_name}},

I noticed {{company}} is running agents on {{framework}} — impressive stack. Quick question: how are you managing API keys and permissions across your agents today?

Most teams I talk to start with shared keys or a homegrown auth layer. It works until you're at 5+ agents and an auditor (or a customer) asks "which agent made this API call?" Then it becomes a 2-month platform engineering project.

We built AI Identity to solve exactly this. Each agent gets its own identity, scoped permissions, and a full audit trail. It takes about 15 minutes to set up:

1. Register your agent (POST /agents)
2. Get a scoped API key (aid_sk_...)
3. Route agent traffic through our gateway — we enforce permissions and log every call

Would you be open to a 15-minute walkthrough? Happy to show how it maps to {{company}}'s setup.

Best,
Jeff

P.S. We're inviting 10 design partners to shape the product. Free access + direct product input in exchange for feedback.

---

### Template 2: Security / DevSecOps Lead — "The Compliance Angle"

**Subject:** `Agent identity for {{company}}'s SOC 2 posture`

**Body:**

Hi {{first_name}},

As {{company}} scales its AI agent deployments, I imagine the compliance conversation around non-human identities is getting interesting. Most teams I talk to can't answer one basic audit question: "Which agent called which API, with what permissions, at what time?"

Traditional IAM tools like Okta handle human users well, but they weren't designed for autonomous agents that make API calls at machine speed. That's what we're building at AI Identity:

- **Per-agent identity** — each agent gets its own key (aid_sk_...) instead of sharing app-wide credentials
- **Scoped permissions** — least-privilege policies enforced per agent, per API
- **Immutable audit log** — every agent API call logged with identity, endpoint, decision, and cost

If NHI (non-human identity) management is on {{company}}'s compliance roadmap, I'd love to share how we're approaching it. 15-minute call?

Best,
Jeff

---

### Template 3: Agent Framework Builder — "The Integration Partner"

**Subject:** `Agent identity integration for {{framework}}`

**Body:**

Hi {{first_name}},

I've been following {{company}}'s work on {{framework}} — really solid execution. I keep seeing the same question come up in the community: "How do I manage API keys across a multi-agent deployment?"

Right now everyone rolls their own solution. We're building AI Identity to give the ecosystem a standard answer:

- Each agent gets a unique identity and scoped API key
- A gateway sits between agents and external APIs — enforces permissions, logs decisions
- Key rotation with 24-hour grace periods so deployments don't break

We'd love to explore an integration where {{framework}} users can manage agent identity natively. Think: `agent.set_identity(aid_key)` and the rest is handled.

Would you be interested in a quick call to explore a partnership? We're early enough that partner feedback directly shapes the product.

Cheers,
Jeff

---

## DM Templates

### Twitter/X DM — Short & Curious

> Hey {{first_name}} — saw your post about {{topic}}. We're building an identity layer for AI agents (per-agent keys, permissions, audit trails). Think Okta but for agents instead of humans. Your work on {{their_product}} is in the exact space we're solving for. Would you be up for a 15-min chat? No pitch, genuinely looking for design partner feedback.

### GitHub / Discord DM — Community Angle

> Hey {{first_name}} — I've been following {{repo_or_project}} and noticed {{specific_issue_or_discussion}} about managing agent credentials/keys. We're building an open-source identity layer for AI agents (per-agent API keys, scoped permissions, audit logging). Would love your take on the approach — happy to share what we've built so far. No sales pitch, just looking for feedback from people who deeply understand the problem.

---

## Follow-Up Cadence

| Day | Action | Channel | Message |
|-----|--------|---------|---------|
| **Day 0** | Initial outreach | Email or DM | Use template above |
| **Day 3** | Soft bump | Same channel | "Just bumping this to the top — would love your take even if it's a quick 'not now'." |
| **Day 7** | Value add | Email | Share something useful — a blog post about agent security, a relevant GitHub issue, or a data point about agent key management pain. End with: "Thought you'd find this relevant. Still happy to chat if timing works." |
| **Day 14** | Final follow-up | Email | "Last note on this — totally understand if the timing isn't right. If agent identity/permissions becomes a priority down the road, I'm here. In the meantime, here's our docs if you want to kick the tires: [link]" |
| **Day 14+** | Close file | — | Mark as "No Response" in pipeline. Re-engage only if a trigger event surfaces (new blog post, funding round, hiring signal). |

### Follow-Up Rules

1. **Never more than 4 touches** — respect their inbox
2. **Each follow-up adds value** — no "just checking in" emails
3. **Switch channels if no email response** — try Twitter DM on Day 7 if email went cold
4. **Personalize every touch** — reference something specific (their blog post, GitHub commit, tweet)
5. **Accept "no" gracefully** — a polite "not now" is a future "maybe"

---

## Personalization Checklist

Before sending any outreach, verify:

- [ ] Used their **first name** (not full name)
- [ ] Referenced their **specific company/product** (not generic)
- [ ] Mentioned their **framework/stack** correctly (LangChain vs LangGraph vs CrewAI)
- [ ] Included a **specific trigger** (their blog post, tweet, GitHub issue, job posting)
- [ ] Subject line is **under 50 characters** and curiosity-driven (not salesy)
- [ ] Email is **under 150 words** (respects their time)
- [ ] CTA is **specific and low-friction** ("15-minute call" not "let's chat sometime")
- [ ] **No attachments** on first email (triggers spam filters)
- [ ] Sent from a **personal email** (jeff@, not sales@)

---

## Anti-Patterns (What NOT to Do)

- ❌ "I hope this email finds you well" — instant delete
- ❌ Attaching a pitch deck on first contact
- ❌ Claiming "we're the #1 agent identity platform" (we're pre-revenue)
- ❌ Mass-mailing the same template without personalization
- ❌ Following up more than 4 times
- ❌ Being pushy about scheduling a call
- ❌ Namedropping customers we don't have
- ❌ Using "AI" buzzwords without substance
