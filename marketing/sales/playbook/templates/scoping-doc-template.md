# AI Identity 90-day pilot — scoping doc for {{ Customer }}

**Prepared by:** Jeff Leva (Founder & CEO)
**Date:** {{ YYYY-MM-DD }}
**Pilot start (target):** {{ YYYY-MM-DD }}
**Pilot end (day 90):** {{ YYYY-MM-DD }}

---

## Pilot summary

A 90-day founding-partner pilot of AI Identity at {{ Customer }}, covering
{{ N }} agents across {{ team / department }}. The pilot is **free for 90
days** under the founding-partner offer. After day 90, {{ Customer }} can
continue at $1,500/mo (multi-tenant) or $3,000/mo (dedicated VPC) with a
24-month rate lock at today's published rates, step down to a Pro / Business
/ Business+ tier, or walk away with no contractual penalty.

## Agents in scope

| # | Agent | Owner | What it does | AI Identity treatment |
|---|---|---|---|---|
| 1 | {{ name }} | {{ team }} | {{ what }} | runtime key + policy + audit |
| 2 | ... | ... | ... | ... |

**Out of scope for this pilot** (will not be onboarded to AI Identity in 90 days):

- {{ agent / system → reason it's deferred. }}

## Policies to author (first three)

The pilot includes white-glove policy authorship on the first three policies.
Below is the proposed list — to be confirmed with {{ Customer }} before pilot
kickoff.

### Policy 1: {{ name }}

- **Applies to:** {{ which agents }}
- **What it enforces:** {{ specific rule, e.g. "no orders > $5K without HITL approval; supplier must be in approved-list" }}
- **Failure mode:** {{ what happens when policy denies }}
- **Success signal:** {{ how we know the policy is doing its job }}

### Policy 2: {{ name }}

...

### Policy 3: {{ name }}

...

## Compliance posture

| Framework | In-scope for this pilot | Notes |
|---|---|---|
| SOC 2 Type II | ☐ Yes / ☐ No | {{ whether evidence pack is part of day-90 deliverables }} |
| EU AI Act | ☐ Yes / ☐ No | {{ ... }} |
| NIST AI RMF | ☐ Yes / ☐ No | {{ ... }} |
| GDPR | ☐ Yes / ☐ No | {{ ... }} |
| {{ customer-specific framework }} | ☐ Yes / ☐ No | {{ ... }} |

## Day-90 success criteria

The pilot is "successful" if all of the following are true at day 90. {{
Customer }} signs off on these criteria before the pilot starts.

1. **{{ Specific, measurable, verifiable criterion. }}** Verification method: {{ how we'll check }}.
2. **{{ ... }}** Verification: {{ ... }}.
3. **{{ ... }}** Verification: {{ ... }}.

These are the things that, if achieved, justify continuing past day 90 at the
locked Enterprise rate. If none of these criteria land, the right answer is
to walk away with no contractual penalty.

## Deployment topology

- **Infrastructure:** ☐ Multi-tenant (default) / ☐ Dedicated VPC (+$5,000 one-time stand-up, waived for founding cohort)
- **Region:** {{ US-East default, or specified }}
- **Identity provider integration:** {{ Okta / Entra / Auth0 / other }}
- **SIEM integration:** {{ Splunk / Sentinel / Datadog / other / none }}

## Cadence during the pilot

- **Week 1:** Pilot kickoff. First three policies authored together. Agents registered and online.
- **Weeks 2-4:** Weekly office hours with Jeff (30 min). Review audit logs, anomaly events, policy effectiveness.
- **Week 6 (day 42):** Mid-pilot review. Adjust policies if needed.
- **Week 9 (day 60):** Joint review. Decide: continue, step down, or walk away. Decision recorded here.
- **Day 90:** Coupon expires. If continuing, billing begins automatically at locked rates.
- **Quarterly thereafter:** Compliance evidence pack delivered if SOC 2 / EU AI Act / NIST in scope.

## What {{ Customer }} commits to

- Designated point of contact (typically the Security Director or platform lead).
- Engineering availability for the first three policy-authoring sessions (~2 hours of their time).
- Weekly office-hours attendance during the first month (30 min × 4).
- Honest feedback at the day-60 review on whether to continue.

## What AI Identity commits to

- Founding-partner pricing and 24-month rate lock if continuing past day 90.
- 100%-off coupon for the full 90 days.
- White-glove authorship of the first three policies.
- Weekly office hours with the founder for the first month, then bi-weekly.
- Same-day response on Slack or email during business hours throughout the pilot.
- Quarterly compliance evidence export through {{ Customer }}'s auditor of choice (post-pilot, if continuing).
- Optional named launch case study with full sign-off on every quote (not required).

## Out of scope (explicitly)

The pilot does NOT cover:

- {{ Specific thing they raised that AI Identity won't solve. }}
- {{ ... }}
- {{ ... }}

## Open questions

{{ Anything that still needs an answer before pilot kickoff. Each should be
addressable in a single message exchange — if it requires more, it probably
belongs in scope-of-pilot rather than scoping-doc-revision. }}

1. ...

---

*Sign-off below begins the 90-day pilot at no cost to {{ Customer }}.*

| | |
|---|---|
| **For {{ Customer }}** | **For AI Identity** |
| {{ name }} | Jeff Leva |
| {{ title }} | Founder & CEO |
| Date: ____ | Date: ____ |
