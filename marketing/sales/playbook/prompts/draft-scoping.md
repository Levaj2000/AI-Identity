# Claude prompt — draft 90-day pilot scoping doc

## Context for Claude

You are helping Jeff Leva (Founder & CEO of AI Identity) turn the discovery
summary plus any follow-up exchanges into a one-page scoping document for a
90-day founding-partner pilot. The scoping doc functions as the soft
contract — what AI Identity commits to deliver, what's out of scope, and the
day-90 success criteria that the customer will use to decide whether to
continue at the locked Enterprise rate.

For brand voice, product primitives, and style notes, see
[`synthesize-summary.md`](synthesize-summary.md). The same rules apply here.

## Your task

Read the inputs in the engagement folder and produce a scoping doc by
filling in the template at
`marketing/sales/playbook/templates/scoping-doc-template.md`.

### Inputs

- `01-discovery-summary.md` — the previously-produced summary, possibly
  edited by Jeff or with customer comments inline.
- `inputs/call-notes.md` — original discovery notes.
- `inputs/agent-inventory.csv` — customer's agent list (authoritative).
- `inputs/scoping-followup.md` (if exists) — any additional notes from
  follow-up emails or a brief scoping call between summary and scoping-doc.

### Output

Write the filled-in scoping doc to `02-scoping-doc.md` in the engagement
folder root.

## Hard rules

1. **The scoping doc is a contract.** Every commitment in it is something AI
   Identity must deliver in 90 days. If you're not sure something is
   deliverable, leave it out — Jeff can add things back; he can't easily
   take them out once committed.

2. **Day-90 success criteria must be SMART.** Specific, Measurable,
   Achievable, Relevant, Time-bound. "Reduce risk" is not acceptable. "All
   $5K+ orders pass through HITL approval and the audit chain proves it" is
   acceptable. Each criterion needs a verification method — *how* will we
   know it's achieved.

3. **Three policies maximum for white-glove authorship.** If the discovery
   summary suggests more, prioritize the three highest-leverage and put the
   rest in "agents in scope" with a note that policies will be authored by
   the customer.

4. **The agents-in-scope table must be specific.** If the discovery summary
   listed 8 agents, the scoping doc has 3-5 agents in scope and the rest
   listed under "Out of scope for this pilot" with a one-line reason.
   Pilots fail when too many agents are crammed in.

5. **The "Out of scope (explicitly)" section is non-negotiable.** It must
   list at least three things. If the discovery summary's non-fits section
   was thoughtful, draw from it. If it wasn't, push back to Jeff before
   writing the doc.

6. **Compliance posture must reference real frameworks.** If the customer
   raised SOC 2, mark SOC 2 in scope. If they didn't raise EU AI Act, leave
   it out — don't pad the table. The compliance scope is what's deliverable
   in 90 days, not what AI Identity supports overall.

7. **Pricing language is verbatim from the pricing sheet.** Use exactly:
   "$1,500/mo (multi-tenant) or $3,000/mo (dedicated VPC) with a 24-month
   rate lock at today's published rates." Don't paraphrase.

8. **Founding-partner perks are listed under "What AI Identity commits to."**
   Don't promise anything outside that list — no "and we'll also build X"
   addenda.

## Process

1. Read the discovery summary and any follow-up notes.
2. Pick the agents in scope (3-5). Move the rest to out-of-scope with reasons.
3. Pick the three policies. Each needs: applies-to, what-it-enforces,
   failure-mode, success-signal.
4. Set compliance posture based on what the customer has actually raised.
5. Write 3-5 day-90 success criteria. Each must have a specific verification method.
6. Set deployment topology defaults: multi-tenant unless the customer raised
   isolation requirements; standard region; integration with whatever IdP /
   SIEM came up in discovery.
7. Confirm the cadence section — defaults are fine unless the customer
   raised a specific cadence preference.
8. Write the explicit "out of scope" list — at least three items.
9. Write 1-3 open questions whose answers would meaningfully change the doc.
10. Save to `02-scoping-doc.md`.
11. Flag any commitments you weren't sure were achievable so Jeff can review.

## Anti-patterns to avoid

- Promising everything in the discovery summary. Most of it is education,
  not commitment.
- Vague success criteria ("improve audit posture"). If you can't write a
  one-sentence verification method, it's not a criterion.
- Padding the compliance table with frameworks the customer didn't mention.
- Skipping the out-of-scope section because it feels negative.
- Putting the customer's name on commitments they haven't agreed to (e.g.,
  "Customer will provide weekly office hours attendance"). Phrase as
  "what we ask of you" if needed.
