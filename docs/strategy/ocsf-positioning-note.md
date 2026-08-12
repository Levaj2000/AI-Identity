# OCSF Positioning Note — "Why the standards work matters"

**Reusable copy · 2026-06-05 (updated 2026-07-21) · For sales decks, investor FAQ, grant narratives**

Three framings of the same idea, pick by audience. Core message: *AI Identity is planting its flag in the open standard the security industry will use to describe AI agent behavior — so when "prove what your agent did" becomes a requirement, the answer is shaped like our product.*

> **Standards status (2026-07-21):** Three contributions **merged into OCSF**. PR [#1662](https://github.com/ocsf/ocsf-schema/pull/1662) added the `serialization` / `serialization_id` canonical-serialization fields to `digital_signature` (lets any third party reproduce the exact signed bytes and verify a signature **offline**). PR [#1661](https://github.com/ocsf/ocsf-schema/pull/1661) — the flagship — **merged 2026-07-17**: the `attestation` object and `record_integrity` profile (hash-chained, signed, independently verifiable per-event integrity) shipped in **OCSF 1.9.0** ([released 2026-08-03](https://github.com/ocsf/ocsf-schema/releases/tag/v1.9.0)). PR [#1684](https://github.com/ocsf/ocsf-schema/pull/1684) added `fingerprint.encoding_id`. For the attestation / record-integrity work you may now say **"shipped in OCSF 1.9.0"** (cite the GitHub release). `ai_agent` (#1641) is still in review — keep "contributing to" framing for that piece.

---

## 1. One-liner (use anywhere)

> We're helping define the open standard (OCSF) for how the security industry describes and verifies AI agent actions — and our product is the most complete implementation of it.

---

## 2. Sales deck slide

**Headline:** Built on the open standard, not a silo

- **OCSF is the security industry's shared language** — Splunk, AWS, Cisco and others emit and ingest telemetry in this schema so tools interoperate.
- **We're authoring the AI-agent accountability vocabulary in it** — cryptographic attestation, independent verifiability, and delegation of authority.
- **Your tools already speak it.** Our agent records map natively onto OCSF, so the verifiable audit trail flows into the SIEM and security stack you already run — no proprietary lock-in.
- **When "prove what your agent did" becomes an audit requirement, you're already compliant** — by adopting an open standard, not betting on one vendor.

*Speaker note:* lead with the buyer's risk reduction (open standard = no lock-in), not our schema credits. The credibility ("our work is merged into OCSF alongside Cisco/Splunk/AWS") is the proof point, not the pitch.

---

## 3. Investor FAQ

**Q: You spend time contributing to an open standard (OCSF). How does that create value rather than give the work away?**

Standards define categories, and whoever helps author one shapes it to fit their product. We're writing the vocabulary for AI agent accountability — non-repudiation, independent signature verification, delegated authority — directly into OCSF, the schema the security industry is standardizing on.

Three returns:
1. **Distribution.** As SIEMs and security tools implement these fields, each becomes a place our attestations work natively — pull-through demand we don't integrate one by one.
2. **Moat protection.** Being an author/reviewer keeps the standard compatible with our architecture, rather than a competitor shaping it in a way we'd have to retrofit to.
3. **Credibility.** Merged contributions alongside Cisco, Splunk, and AWS is third-party validation we spend in enterprise sales, regulated-buyer trust, and grant applications.

The standard makes our product the obvious, trusted choice. The product — the gateway, Mandate Service, and verification tooling — is still what generates revenue.

---

## 4. NSF SBIR broader-impact paragraph

> **Shelved 2026-08-12** per CEO Dashboard decision "Do not pursue NSF SBIR/STTR funding":
> second Project Pitch (00121677) declined; NSF submission limits lock us out until
> 2027-06-04, with one lifetime pitch remaining for this technology. Kept for reference —
> revisit only if the decision is reopened (review date 2027-06-04).

> The accountability layer this project develops is being contributed to the Open Cybersecurity Schema Framework (OCSF), the open standard the security industry uses to represent and exchange telemetry. By defining a vendor-neutral vocabulary for cryptographic non-repudiation, independent signature verification, and delegated authority of autonomous AI agents, the work provides a public good: any security tool, auditor, or regulated organization gains a standard, interoperable way to verify what an AI agent did and under whose authority — rather than relying on proprietary, non-verifiable logs. As autonomous agents proliferate across healthcare, finance, and government, this open foundation for agent accountability benefits the broader economy and national security posture well beyond any single company's products.

---

### What to watch for (reviewer's note)
- **Strategic bet:** the whole note assumes the agent-accountability category grows *and* OCSF adoption continues — both are real bets, not facts. Don't present "the industry will use this" as settled; it's a directional thesis.
- **Code-state claim:** "most complete implementation" and "maps natively onto OCSF" lean on the gateway/Mandate Service emitting these fields — true today but verify before putting in front of a technical buyer who'll probe it.
- **Competitor assertion:** "moat protection" implies a competitor could steer the standard — keep this internal/investor-facing; don't name competitors in buyer-facing copy.
- **Standards status:** **#1662, #1661, and #1684 are all MERGED** (#1661 on 2026-07-17; attestation + `record_integrity` ship in OCSF 1.9) — for the attestation / record-integrity / serialization work you may now say **"merged into OCSF 1.9."** Remaining precision points: `ai_agent` (#1641) is still in review, and `delegation` (#1665) is Ania's PR, not ours — so "the full agent-accountability vocabulary is merged" is still an overclaim; the *integrity* vocabulary is. The SBIR paragraph's "being contributed to" hedge can now be upgraded to "contributed to (with core objects merged)" — but keep "being contributed to" if the grant narrative needs present-tense ongoing work.
- **Vendor names:** Splunk/AWS/Cisco are illustrative of OCSF participants; fine as ecosystem context, but don't imply they endorse or use AI Identity specifically.
