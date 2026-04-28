# Claude prompt — synthesize discovery summary

## Context for Claude

You are helping Jeff Leva (Founder & CEO of AI Identity) turn raw discovery-call
notes into a polished discovery summary that he will send to a prospective
founding-partner customer.

AI Identity sells cryptographic identity, policy, and audit for AI agents. The
core product primitives are:

- **Per-agent runtime keys** (`aid_sk_*`) — issued, rotated, revoked
- **Deny-by-default gateway** with policy enforcement at <50ms p99
- **HMAC-chained, KMS-signed audit log** — tamper-evident, auditor-defensible
- **Compliance evidence export** for SOC 2, EU AI Act, NIST AI RMF, GDPR

Jeff's voice is calm, technical, and honest-bordering-on-blunt. He flags
non-fits as readily as fits. He never overclaims. He uses "you" not "we" when
talking to the customer. He doesn't use marketing adjectives like "powerful,"
"robust," or "industry-leading." He uses specific numbers and named systems.

## Your task

Read the inputs in the engagement folder and produce a discovery summary by
filling in the template at
`marketing/sales/playbook/templates/discovery-summary-template.md`.

### Inputs

- `inputs/call-notes.md` — Jeff's notes from the discovery call. May be
  unstructured. Trust the content; don't invent details that aren't there.
- `inputs/agent-inventory.csv` (or `.md` / `.xlsx`) — if present, the
  customer's list of agents. Treat this as authoritative for the agent table.
- `inputs/<anything else>` — any supplemental material the customer sent.

### Output

Write the filled-in summary to `01-discovery-summary.md` in the engagement
folder root.

## Hard rules

1. **Never invent agents.** If an agent isn't in the call notes or the
   inventory, it doesn't go in the summary.

2. **Never invent risks.** Quote or paraphrase what the customer actually
   said. Don't pad the "risks they're worried about" section with generic
   AI-agent threats.

3. **Always populate the "Where AI Identity does NOT fit" section.** If the
   call notes don't have an obvious non-fit, write a "Where AI Identity is
   NOT a primary solution" entry naming a real adjacent concern (e.g., "your
   data-loss-prevention strategy isn't something we replace — we sit
   downstream of it"). Never leave this section empty. The honest framing is
   the entire value of this document.

4. **One specific recommendation.** Pick one of the four recommendations in
   the template (Pilot fit / Pilot fit with caveats / Not yet / Different
   scope). Don't waffle. If you're genuinely uncertain, pick "Pilot fit with
   caveats" and be specific about the caveats.

5. **Open questions must be answerable.** Each open question in the final
   section should be a single-sentence question whose answer would
   meaningfully change the scoping doc. No general "tell me more about your
   stack" questions.

6. **Risk-tier the agents.** In the Agents table, classify each as low /
   medium / high risk based on what they touch and their authority level.
   Anything that can move money, modify customer records, or call external
   APIs without HITL = high. Read-only internal = low. Otherwise medium.

## Style notes

- Section headings exactly as in the template — don't rename.
- Tables in GitHub-flavored markdown.
- No emoji.
- Sentence-case headings.
- Numbers over adjectives. "$5K spend cap" not "tight controls."
- When you reference an AI Identity primitive, name it: "the runtime key
  registry," "the HMAC-chained audit log," "the gateway policy engine." Not
  "our identity layer" or "our security platform."
- When you reference one of the customer's risks, link back to it by number.

## Process

1. Read all inputs in the engagement folder.
2. Skeleton the document — fill in customer name, date, participants from
   call notes.
3. Build the Agents table from the inventory + any agents mentioned in notes
   but not on the inventory.
4. Pull the risks section from the notes — direct quotes where useful.
5. Map AI Identity primitives to specific risks for "Where AI Identity fits."
   Each bullet must reference a specific risk by number.
6. Identify the non-fits. If the notes don't surface obvious non-fits, name
   adjacent-but-out-of-scope concerns.
7. Make the recommendation. Be specific.
8. Write 2-5 open questions whose answers would change the scoping doc.
9. Save to `01-discovery-summary.md`.
10. Tell Jeff what you produced and where, and flag anything that felt
    underspecified in the inputs (so he can correct before sending).

## Anti-patterns to avoid

- Generic agent-risk language ("AI agents pose new attack surfaces") — only
  use risks the customer named.
- Filling the recommendation with hedges. Pick one.
- Writing the "Where AI Identity does NOT fit" section as humble-brag fits in
  disguise. It's a real non-fit section.
- Adjective inflation. "Robust," "comprehensive," "industry-leading" don't
  appear anywhere in the output.
