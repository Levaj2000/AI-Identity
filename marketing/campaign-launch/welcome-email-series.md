# Welcome Email Series (3 Emails)

## Email 1: Welcome (Sent immediately after signup)

**Subject:** You're in. Here's how to deploy your first agent in 15 minutes.

**From:** Jeff @ AI Identity

---

Welcome to AI Identity.

You just took the first step toward AI agents that are actually audit-ready. Here's how to get started:

**Step 1: Register your first agent**
Head to your dashboard and create an agent with scoped capabilities. Each agent gets its own identity and API key.

[Go to Dashboard ->]

**Step 2: Try the Interactive Playground**
Not ready to integrate yet? Our live API playground lets you run real API calls against production — no code required.

[Open Playground ->]

**Step 3: Connect your first policy**
Set up a deny-by-default gateway policy so every agent request is authenticated and authorized before it reaches your LLM provider.

Your free tier includes:
- 5 agents
- 2,000 requests/month
- 30-day audit log retention
- 1 upstream credential

That's enough to evaluate whether AI Identity fits your stack. If you need more, reply to this email — I read every one.

— Jeff

---

## Email 2: Value Highlight (Sent Day 3)

**Subject:** The question every auditor will ask about your AI agents

---

Hi,

There's one question coming for every team deploying AI agents in production:

**"Can you prove what this agent did, when it did it, and that the record hasn't been tampered with?"**

If you're logging agent activity in application code — console.log, CloudWatch, a shared logging table — the honest answer is no. Application logs can be modified, deleted, or silently fail. That's not an audit trail.

AI Identity creates tamper-proof audit records using HMAC-SHA256 cryptographic chaining. Every entry is linked to the previous one. If a single record is altered, the entire chain breaks — and we can tell you exactly where.

This matters for:
- **SOC 2** — tamper-evident audit trail is a core requirement
- **HIPAA** — activity logs must prove minimum necessary access
- **EU AI Act** — traceability and human oversight are mandatory for high-risk AI

If you haven't tried the audit verification yet, here's how:

1. Create an agent and run a few requests through the gateway
2. Go to Forensics in your dashboard
3. Click "Verify Chain" — you'll see cryptographic proof that your audit trail is intact

[Open Forensics ->]

This is the evidence auditors actually accept.

— Jeff

---

## Email 3: Design Partner Invitation (Sent Day 7)

**Subject:** Want to shape what we build next?

---

Hi,

You've been on AI Identity for about a week now. Whether you've deployed an agent or are still evaluating — I have a question:

**Would you be interested in becoming a design partner?**

Here's what that means:

**You get:**
- 50% off Pro tier for 6 months (that's $40/month instead of $79)
- Direct access to me for feature requests and roadmap input
- Priority support — Slack channel or email, your choice
- Early access to new features before public release

**We get:**
- Your feedback on what works and what doesn't
- A published case study after 90 days (with your approval)
- Understanding of real compliance workflows in your industry

We're looking for 5-10 design partners, specifically teams in:
- Healthcare (HIPAA, clinical AI)
- Financial services (transaction agents, compliance)
- Any regulated industry deploying AI agents

If this sounds interesting, just reply to this email with a sentence about what you're building. I'll set up a 20-minute call to see if it's a fit.

No pressure — the free tier isn't going anywhere. But if you want to influence the product while it's still early, this is the window.

— Jeff

P.S. If you're not the right person at your company but know who is, feel free to forward this. The design partner offer is for the team, not the individual.

---

## Technical Setup Notes

**Email platform:** Whatever you're using (Resend, SendGrid, Postmark)

**Trigger logic:**
- Email 1: On user creation (welcome_email_sent_at = now)
- Email 2: 3 days after welcome_email_sent_at, if user hasn't upgraded to Pro
- Email 3: 7 days after welcome_email_sent_at, if user hasn't upgraded to Pro

**Unsubscribe:** Standard one-click unsubscribe in footer

**Tracking:**
- Open rates (target: 40%+ for welcome, 25%+ for subsequent)
- Click rates (target: 10%+ for welcome, 5%+ for subsequent)
- Reply rate on Email 3 (target: 5-10% — this is where design partners come from)

**Sender:** Use a personal sender name ("Jeff @ AI Identity" or "Jeff Leva") — not "AI Identity Team." Personal sender names get 20-30% higher open rates.
