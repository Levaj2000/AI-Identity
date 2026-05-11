# LinkedIn — MongoDB for Startups Announcement

**Post date:** 2026-05-11
**Channel:** LinkedIn (founder feed, company page reshare)
**Status:** Draft — pending MongoDB asset drop + final founder review

---

## Version A — Short text post (200 words)

> Excited to share that AI Identity has joined **MongoDB for Startups**.
>
> Our H2 product — the Mandate Service — is the bridge between governed AI agents and agent-initiated commerce. It needs a database that can absorb the shape of agent workloads: deeply nested mandate documents, evolving schemas as the standards mature, and operational scale without re-architecting every quarter.
>
> That's MongoDB Atlas.
>
> Three reasons it was the right call for a one-week build:
>
> 1. **Document model = mandate model.** Agent mandates are nested by nature (issuer → constraints → audit chain). No ORM gymnastics, no schema migrations every time a new mandate field lands.
> 2. **Crypto-agility built in.** Hybrid ECDSA + ML-DSA-87 signatures store cleanly alongside the documents they sign. PQC readiness without a separate keystore.
> 3. **Atlas operations are boring.** That's the compliment. Backups, replica sets, audit logs — all the things you don't want a solo founder hand-rolling.
>
> The Mandate Service deploys to our first design partners in June. If you're building agent infrastructure and want to compare notes — DM me.
>
> Thanks to the MongoDB for Startups team for the partnership.
>
> #MongoDB #AIAgents #AgentIdentity #Startups

---

## Version B — Long-form / carousel-supported (350 words)

> AI Identity has joined **MongoDB for Startups** — and there's a real engineering reason behind it.
>
> Six months ago we committed to building the **Mandate Service**: a verifiable trust root for agent-initiated commerce. Every time an AI agent acts on behalf of a principal — placing an order, signing a contract, moving money — it needs a mandate that says *who* authorized *what*, *for how long*, and *with what constraints*. Signed, replayable, regulator-ready.
>
> The data model is genuinely hard:
>
> - Mandates are deeply nested (issuer + subject + capabilities + temporal constraints + spend caps + cryptographic chain).
> - The schema **must** evolve as standards like W3C VC Data Model 2.0, OAuth Mandate Extensions, and EU AI Act technical documentation mature.
> - Every document carries a hybrid signature (classical ECDSA + post-quantum ML-DSA-87) — and we need to keep that signature next to what it signed, not in a separate table.
>
> SQL would have meant a JSON-blob anti-pattern within a week. So we went with **MongoDB Atlas** and got the Mandate Service to a working deploy in seven days.
>
> Three things that made the choice obvious:
>
> 1. **Document model fits the domain.** A mandate is a document. Storing it as one means our schema and our wire format and our verification logic all look the same.
> 2. **Crypto-agility ships clean.** Hybrid signatures live alongside the payload. No keystore-vs-database state divergence. No "which DB is the source of truth" question when we cycle algorithms.
> 3. **Operational depth from day one.** A solo founder cannot run their own replica set drama. Atlas backups, audit logs, encryption-at-rest, BYOK — all baked in.
>
> Live with design partners in June 2026. If you're building anything in this space — agent identity, mandate issuance, verifiable agent actions — I'd love to compare architecture notes.
>
> Thanks to the MongoDB for Startups team for getting us moving fast.
>
> #MongoDB #MongoDBAtlas #AIAgents #AgentIdentity #VerifiableCredentials #AIStartups

---

## Carousel outline (5 slides, 1080×1350 — image-based per LinkedIn PDF rules)

| Slide | Title | Body |
|---|---|---|
| 1 | "Why we picked MongoDB to build the Mandate Service" | Hook: agent commerce needs a verifiable trust root. Atlas got us there in a week. |
| 2 | "The Mandate Problem" | Agents act on behalf of principals. Every action needs: who authorized? what scope? what limits? signed how? Document-shaped data. |
| 3 | "Hybrid signatures, one document" | ECDSA + ML-DSA-87 alongside the mandate they sign. Crypto-agility without a separate keystore. |
| 4 | "Operational depth on day one" | Atlas: backups, replica sets, audit logs, encryption-at-rest. Things a solo founder shouldn't hand-roll. |
| 5 | "Deploys to design partners June 2026" | CTA: building agent infra? DM to compare notes. Logos: AI Identity + MongoDB for Startups. |

Use the brand-voice plugin (`/brand-voice:enforce-voice`) before publishing the carousel — the carousel copy should be terser than the post copy.

---

## Asset drops needed from the MongoDB for Startups Drive folder

Save these to `landing-page/public/images/partners/` so they're build-time and brand-consistent:

| Asset | Suggested filename | Where used |
|---|---|---|
| MongoDB for Startups badge (SVG preferred) | `mongodb-for-startups-badge.svg` | Optional — swap text-only Footer/About mentions for image badge |
| MongoDB primary logo (SVG, dark-mode safe) | `mongodb-logo.svg` | Carousel slide 5, future architecture page |
| Co-branding usage guidelines (PDF) | `mongodb-cobranding-2026.pdf` | Reference only, not deployed |

Once the SVG is in place, the swap to image-based badge is a 5-line change in `MongoDBForStartupsBadge.tsx`.

---

## What to watch for (reviewer's note)

- **Code-state claims:** "The Mandate Service deploys to design partners in June" — verify Milestone #43 (Mandate Service design-partner deploy) is still on-track before publishing. Slip on this and the post is a hostage.
- **Strategic bets:** "Crypto-agility built in" — this hangs on Decision #42 (hybrid ECDSA + ML-DSA-87). If we walk that back, the post needs a rewrite. PQC implementation milestone (#45) is targeting end of 2026; the post implies it's already shipped in the Mandate Service. Confirm what's actually live vs. designed before publishing — soften to "designed for crypto-agility" if implementation hasn't shipped.
- **Analogies:** "Document model = mandate model" — accurate but oversimplified. Reviewers from the SQL camp will push back. Hold the line; the simplification is fair for LinkedIn.
- **Competitor assertions:** None made directly. Implicit "SQL would have meant a JSON-blob anti-pattern" is a swipe at Postgres/MySQL — defensible technically but may attract Postgres-loyal commenters. Acceptable risk.
- **MongoDB co-branding rules:** Verify the Drive folder includes co-branding guidelines. Some startup programs require posts to be reviewed by their team before publish. Check the program agreement.
