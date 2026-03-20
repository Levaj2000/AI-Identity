# AI Identity — Partner Onboarding Email Sequence

> 3-email drip sent after a design partner signs up. Manual for now (copy/paste from here), automate later via SendGrid or Resend.

---

## Sequence Overview

| # | Email | Trigger | Subject Line |
|---|-------|---------|-------------|
| 1 | Welcome | Day 0 — partner signs agreement | Welcome to AI Identity — your dashboard is ready |
| 2 | Quickstart | Day 1 — next business day | Your first agent in 5 minutes |
| 3 | Check-in | Day 7 | Quick check-in — how's the integration going? |

---

## Email 1: Welcome + Dashboard Invite

**Send:** Immediately after partner signs up
**Subject:** Welcome to AI Identity — your dashboard is ready
**From:** Jeff Leva <jeff@ai-identity.co>

---

Hi {{FIRST_NAME}},

Welcome to the AI Identity design partner program. You're one of 5 companies shaping the product before public launch — that means direct product influence and priority support.

**Your account is ready.** Here's what you need:

- **Dashboard:** [dashboard.ai-identity.co](https://dashboard.ai-identity.co)
- **API docs:** [ai-identity-api.onrender.com/docs](https://ai-identity-api.onrender.com/docs)
- **Your API key:** {{API_KEY}}

Store that API key somewhere safe — it's shown once and authenticates all your API calls via the `X-API-Key` header.

**What AI Identity gives you:**
- Per-agent API keys (each agent gets its own identity)
- Scoped permissions via policy enforcement
- Tamper-proof audit trail with HMAC chain
- Compliance checks against NIST AI RMF, EU AI Act, SOC 2

**What happens next:**
Tomorrow I'll send a quickstart guide to get your first agent running in 5 minutes. For now, feel free to explore the dashboard and API docs.

If you hit any issues, reply to this email — it goes straight to me, not a support queue.

Talk soon,
Jeff

P.S. — Bookmark the [API docs](https://ai-identity-api.onrender.com/docs). Everything is interactive — you can test endpoints right from the browser.

---

## Email 2: Quickstart — First Agent Walkthrough

**Send:** Day 1 (next business day)
**Subject:** Your first agent in 5 minutes
**From:** Jeff Leva <jeff@ai-identity.co>

---

Hi {{FIRST_NAME}},

Here's the fastest path to your first agent. Total time: about 5 minutes.

### Step 1: Create an agent

```bash
curl -X POST https://ai-identity-api.onrender.com/api/v1/agents \
  -H "X-API-Key: {{API_KEY}}" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-first-agent", "description": "Test agent", "capabilities": ["chat"]}'
```

You'll get back an agent UUID and an `aid_sk_` runtime key. Save that runtime key — it's the agent's identity.

### Step 2: Check your dashboard

Open [dashboard.ai-identity.co](https://dashboard.ai-identity.co) — you should see your agent listed with status `active`.

### Step 3: Set a policy

```bash
curl -X POST https://ai-identity-api.onrender.com/api/v1/agents/{{AGENT_ID}}/policies \
  -H "X-API-Key: {{API_KEY}}" \
  -H "Content-Type: application/json" \
  -d '{
    "rules": {
      "allowed_endpoints": ["/v1/chat/*"],
      "allowed_methods": ["POST"],
      "denied_endpoints": ["/v1/admin/*"]
    }
  }'
```

Now your agent can only hit chat endpoints — no admin access. That's least-privilege in one API call.

### Step 4: Run a compliance check

```bash
curl https://ai-identity-api.onrender.com/api/v1/compliance/status \
  -H "X-API-Key: {{API_KEY}}"
```

This runs 30 automated checks across NIST AI RMF, EU AI Act, SOC 2, and our internal best practices. You'll get a compliance score and specific remediation steps for any gaps.

### What to try next

- **Rotate a key** — `POST /agents/{id}/keys/rotate` (24-hour grace period, zero downtime)
- **Add upstream credentials** — encrypted at rest, never logged
- **Check your audit trail** — `GET /api/v1/audit` (tamper-proof HMAC chain)
- **View usage** — `GET /api/v1/usage` (see your quota utilization)

**Questions?** Reply to this email or DM me. I'm building this alongside you.

— Jeff

---

## Email 3: Day-7 Check-in

**Send:** Day 7
**Subject:** Quick check-in — how's the integration going?
**From:** Jeff Leva <jeff@ai-identity.co>

---

Hi {{FIRST_NAME}},

It's been a week since you joined the design partner program. Quick check-in:

**3 questions (reply inline, takes 2 minutes):**

1. **Have you created your first agent?** If not, what's blocking you? I can hop on a 15-minute call to get you unblocked.

2. **What's your biggest question so far?** About the API, the dashboard, how it fits into your stack — anything.

3. **What's missing?** The whole point of this program is building the right product. If something's not there, I want to know.

**What other partners are doing this week:**
- Running compliance assessments to prep for enterprise customer questions
- Setting up per-agent keys to replace shared API keys in their agent orchestrators
- Using the audit trail to debug "which agent made that call?" issues

**Reminder — your partner benefits:**
- Monthly 30-min call with me (let's schedule the first one if we haven't already)
- Priority feature requests
- Free access during the program + guaranteed free tier after launch
- Co-marketing opportunity at program end

If the integration is going well, I'd love to hear about it. If it's not, I'd love to fix it. Either way — reply to this email.

— Jeff

P.S. — Want to see the compliance engine in action? Run `GET /api/v1/compliance/status` — it checks 30 items across 4 frameworks automatically. Great ammo for when your enterprise customers ask about agent governance.

---

## Automation Notes (for later)

When we add SendGrid/Resend:

| Field | Source |
|-------|--------|
| `{{FIRST_NAME}}` | From partner sign-up form or CRM |
| `{{API_KEY}}` | Generated at account creation, included in welcome email only |
| `{{AGENT_ID}}` | Placeholder — partner fills in after Step 1 |

**Trigger logic:**
- Email 1: On partner account creation (webhook from API)
- Email 2: Cron job — send at 9am partner's timezone, day after Email 1
- Email 3: Cron job — 7 days after Email 1, skip weekends

**Tracking:**
- Open rates and click rates per email
- Reply rate on Email 3 (key engagement metric)
- Time-to-first-agent (measure from Email 1 send to first `POST /agents`)
