# The EU AI Act Applies to Your Agents Now. Your Logs Are Not the Evidence It Asks For.

*By **Jeff Leva** — Founder, AI Identity*

On 2 August 2026, the main body of the EU AI Act (Regulation (EU) 2024/1689) became applicable — including the high-risk obligations under Annex III and the deployer duties under Article 26. The prohibitions landed in February 2025. The general-purpose model rules landed in August 2025. This month, the rest arrived.

Most of the compliance content flooding inboxes right now is written for model providers: GPAI documentation, training data summaries, conformity assessments. That content is useful — and it is aimed at someone else. If your company *runs* AI agents rather than trains models, you are a **deployer** under the Act, and the deployer's obligations get far less airtime. They are also the ones your team will be asked to evidence first.

## What a deployer actually owes

Article 26 is the deployer's chapter. Strip it to the operational requirements and four of them land directly on whoever operates agent infrastructure:

1. **Operate the system per the provider's instructions** (Art. 26(1)) — which means you need a record of how each agent was configured, and when that configuration changed.
2. **Assign human oversight** (Art. 26(2)) — a named function with the competence and authority to intervene, and a record that intervention actually happened when it should have.
3. **Monitor operation** (Art. 26(5)) — and inform the provider or authorities when something looks like a serious incident.
4. **Retain the automatically generated logs for at least six months** (Art. 26(6)) — longer where other EU or national law says so.

Behind these sits Article 12, the record-keeping requirement the logs come from in the first place: high-risk systems must automatically record events over their lifetime, at a level that makes the system's behavior traceable.

None of this is exotic. Every engineering team believes they already have it, because every engineering team has logs.

## Why ordinary logs don't clear the bar

Here is the question that separates a logging checkbox from an evidentiary posture. A market surveillance authority — or your own counsel, after an incident — asks about a decision one of your agents made in March:

*How do you know this record wasn't edited after the fact?*

If your answer involves the phrase "our vendor's dashboard," you don't have evidence. You have a relationship. Application logs in a SaaS console are mutable rows in someone else's database. They can be complete, well-intentioned, and beautifully searchable, and still prove nothing — because nothing about them lets a third party verify, independently of the vendor, that the sequence of events is intact.

Our position hasn't changed since we started building: **if you can't verify it offline, it's not evidence.** The Act's record-keeping obligations are the first regulation that makes that position a procurement question. Retained logs are only worth their six-month shelf life if, at month five, they can still withstand the question above.

## What the evidence set actually looks like

Claims are cheap in August 2026, so here is the receipt. This is the artifact set our EU AI Act export profile (`eu_ai_act_2024`) produces for a reporting period — one bundle, generated from the platform's hash-chained audit records, verifiable with an open CLI and no account on our side:

```
eu_ai_act_2024_export/
├── manifest.json                     # DSSE-signed index of the bundle
├── annex_iv_documentation.json       # Annex IV technical documentation fields
├── access_log.csv                    # Art. 12 — every agent decision in period
├── attestations/<session_id>.dsse.json  # Art. 12(4) — signed session attestations
├── human_oversight_log.csv           # Art. 14 / 26(2) — approvals, denials, expiries
├── agent_risk_classification.csv     # Annex III category per agent
├── policy_change_log.csv             # Art. 9 — risk-management change history
└── capability_disclosures.csv        # Art. 13 — per-agent capability set over time
```

Each artifact maps to a specific article, not to a vibe:

| Obligation | Article | What's in the bundle |
|---|---|---|
| Record-keeping | Art. 12 | Every gateway decision — agent identity, subject, outcome — as hash-chained events |
| Tamper-evidence | Art. 12(4) | HMAC chain verification plus DSSE-signed session attestations, checkable offline |
| Transparency | Art. 13 | Agent descriptions and capability declarations at each point in the period |
| Human oversight | Art. 14 / 26(2) | The full approval record — approved, denied, and auto-expired |
| Risk management | Art. 9 | Policy rules and their change history |
| Log retention | Art. 19 / 26(6) | Six-month floor; our default retention is 13 months |

One structural detail matters more than it looks: risk classification lives on the agent record itself. Every agent carries an Annex III category code — `3(a)`, `5(b)`, or explicitly `not_in_scope` — so "which of our agents are high-risk systems?" is a query, not a quarterly archaeology project. That inventory question is where most deployer conversations stall today.

## What we deliberately don't claim

Two honest limits, because fear-based compliance content with no artifacts behind it is exactly the genre we refuse to write.

First, **Article 10 data governance is the provider's problem, and we say so.** Governance of upstream training data sits outside a deployer platform's visibility. Our Annex IV export acknowledges that boundary explicitly rather than fabricating evidence to fill the section.

Second, **there is no EU AI Act certificate to wave.** Conformity assessment bodies for this regime are still standing up. Any vendor claiming to be "EU AI Act certified" today is selling you a logo. What can exist today is architecture that produces the required records in the required shape — and an export a regulator can verify without trusting us.

## The six-month clock is already running

Article 26(6) has a quiet implication: the logs you must be able to produce next February are the ones your agents are generating **right now**. Record-keeping is the one obligation you cannot backfill. A policy document can be written late. A record either existed at decision time, in tamper-evident form, or it never will.

If you deploy agents that touch an Annex III use case — credit decisions, hiring, essential services, critical infrastructure — the practical starting point is a two-column list: the records Article 12 and Article 26 require, and where each one lives today. We keep a version of that list current here: **[ai-identity.co/eu-ai-act-checklist](https://www.ai-identity.co/eu-ai-act-checklist)**.

---

**From AI Identity** — We build the identity, policy, and forensics layer for AI agents: per-agent identity, fail-closed policy enforcement, and hash-chained audit trails that export as regulator-verifiable evidence bundles. Learn more at **[ai-identity.co](https://ai-identity.co)**.

---

## What to watch for (reviewer's note — strip before publication)

- **Legal dates.** Application dates cited: prohibitions 2 Feb 2025, GPAI 2 Aug 2025, general application incl. Annex III high-risk + Art. 26 deployer duties 2 Aug 2026, Annex I product-safety high-risk 2 Aug 2027 (not mentioned). Verified against the staged timeline in Regulation (EU) 2024/1689 as understood at draft time — have counsel or a fresh EUR-Lex read confirm before publishing, especially any 2026 amendments/omnibus changes to the schedule.
- **Article 12(4) framing.** The Act's literal text requires automatic recording and traceability; "tamper-evident" is our engineering interpretation of what makes such records usable as evidence, consistent with the mapping in `docs/compliance/export-profiles.md` and `scripts/seed_compliance.py`. The post is worded to claim the mapping, not to quote the statute. Keep it that way.
- **Article 26 paragraph numbers.** Operate-per-instructions / oversight / monitoring / retention cited as 26(1), 26(2), 26(5), 26(6). Spot-check paragraph numbering against the final OJ text before publish.
- **Export bundle contents.** The tree matches the v1 profile in `docs/compliance/export-profiles.md` (required + recommended artifacts; `incident_records.json` omitted as it's a flagged gap). `capability_disclosures.csv` is a *recommended* artifact — confirm it ships in the current build before showing it, or drop the line.
- **Retention claim.** "Default retention is 13 months" comes from export-profiles.md. Verify against current production config.
- **Open verification CLI.** The "verifiable with an open CLI" claim references the forensics verification tooling — confirm the public CLI path is live (same dependency the PQC whitepaper had).
- **Checklist URL.** `ai-identity.co/eu-ai-act-checklist` is already referenced in the LinkedIn carousel (`marketing/linkedin/build_carousel.py`). Confirm the page exists before this goes out — same sequencing rule as the PQC landing page.
- **Word count.** ~1,150 words body (excluding this note) — inside the 800–1,200 blog band from the brand guidelines.
- **Timing vs. W&B.** Prompted by the 2026-08-20 Weights & Biases EU AI Act whitepaper email. Their guide targets providers/GPAI + observability; this post deliberately takes the deployer/evidence lane and does not mention them. Keep it that way — no competitor punching.
