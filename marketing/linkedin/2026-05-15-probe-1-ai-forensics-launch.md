# LinkedIn — Probe 1 launch: AI Forensics standalone page

**Post date:** 2026-05-15 (launch day)
**Channel:** LinkedIn (founder feed)
**Probe slug:** `ai-forensics-standalone` (Milestone #48 — kill review 2026-06-15)
**Landing page:** https://www.ai-identity.co/ai-forensics

---

## Version A — Short post (~180 words)

> When an AI agent moves a transaction it shouldn't have, the first question is always the same: *which prompt, which tool call, which model version made that decision?*
>
> If your audit trail is a stream of mutable application logs, you can't answer that question. You can describe what probably happened. You can't prove it.
>
> Spinning out **AI Forensics** as a standalone product for that exact problem:
>
> 1. **Replay any agent session step-by-step** — prompt → tool calls → model response → policy evaluation. Year-old incident? Reproducible from the chain.
> 2. **Tamper-evident by construction.** HMAC-SHA256 hash chains today, SLH-DSA post-quantum signatures landing through Q1 2027.
> 3. **Regulator-ready evidence packages.** One-click export for EU AI Act Article 12/13, SOC 2 CC7, NIST AI RMF.
>
> Built on the AI Identity audit primitive, packaged for teams that already run an LLM gateway (Portkey, LangSmith, Helicone, custom) and need forensic-grade audit on top.
>
> Early-access list is open: https://www.ai-identity.co/ai-forensics
>
> #AIAgents #AISafety #IncidentResponse #AIForensics

---

## Version B — Long post (~310 words, more technical)

> Three questions every AI agent incident review eventually arrives at:
>
> - *Which agent identity made this decision?*
> - *Which prompt + tool calls + model version led to it?*
> - *Was the policy that authorized it actually in force at decision time?*
>
> Most teams running LLM gateways today can answer none of these confidently. The audit trail is application logs — mutable, fragmented across services, missing the prompt context, missing the policy snapshot.
>
> That's not audit. It's storage.
>
> **AI Forensics** is spinning out as a standalone product for teams that need real forensic-grade audit on AI agent decisions. What's in it:
>
> **Replay any agent session.** Step-by-step decision trail including the exact prompt, the tool calls, the model response, and the policy evaluation that ran. Reproduce a year-old incident from the chain — no log-stitching.
>
> **Tamper-evident by construction.** HMAC-SHA256 hash chain at write time, SLH-DSA post-quantum signatures landing through Q1 2027. The chain is evidence — an auditor verifies it independently of the vendor.
>
> **Behavioral anomaly intelligence.** Per-agent baseline, drift detection on the permission envelope, severity-scored auto-triage. Move from reactive logging to proactive threat intelligence.
>
> **Regulator-ready evidence packages.** One-click export pre-formatted for EU AI Act Article 12/13 technical documentation and SOC 2 CC7 audit evidence. Mapped to NIST AI RMF.
>
> Built on the AI Identity audit primitive. Designed to ingest from gateways you already run — Portkey, LangSmith, Helicone, custom — so you don't replace your stack to get forensic audit on top of it.
>
> Early-access list: https://www.ai-identity.co/ai-forensics
>
> If you're running AI agents in production and your incident response toolkit is "grep across CloudWatch and hope" — let's talk.
>
> #AIAgents #IncidentResponse #AIForensics #AISafety #SOC2 #EUAIAct

---

## Posting playbook

**Best time to post:** Tuesday or Wednesday between 8-10 AM ET (LinkedIn founder-feed engagement peaks). Launch day is 2026-05-15 — that's a Friday. Friday posts get less reach. **Consider posting Monday 2026-05-18 instead** if the day-of-launch isn't critical for narrative.

**Tag suggestions** (verify accounts exist before tagging):
- No competitor tags (don't draw eyeballs to alternatives mid-post)
- Tag specific industry analysts or researchers if you have a relationship; don't tag cold

**Engagement hygiene:**
- Reply to every comment in the first 2 hours (LinkedIn algorithm rewards early reply velocity)
- Don't ask "agree?" — flat engagement-bait reads as low-quality
- Pin the landing page URL in the first comment if LinkedIn de-prioritizes the in-post link

---

## What to watch for (reviewer's note)

- **"Spinning out" framing.** Implies a near-term packaging decision that hasn't been made yet at the product level — Milestone #48 is a probe, not a commitment to standalone product. If pressed on a launch date, the honest answer is "early access first; standalone product depends on Probe 2 signal." Don't get backed into a date commitment.
- **Post-quantum claims.** Aligned with the PQC whitepaper (PR #252) and Decision #42 — the slots are designed, the implementation lands Q4 2026 (hybrid signing) and Q1 2027 (PQ audit chain). The phrase "landing through Q1 2027" is honest. Don't drift toward "shipping today."
- **Competitor name mentions.** Portkey, LangSmith, Helicone are named as integration targets, not competitive comparisons. This is positioning as complementary, not as a wedge. If they DM you, lean into the complement framing.
- **TAM expansion implication.** Mentioning these as ingest sources implies a partnership / cooperation pathway. If the probe converts, the real product strategy has to decide: build native integrations to those gateways, or stay focused on first-party. Don't promise integrations in the post that aren't on the roadmap.
- **Brian-at-Cisco overlap.** He got the PQC whitepaper via DM 2026-05-11. This post mentions the same signature primitives. Make sure the post and the DM follow-up don't contradict each other. If Brian engages on the post comment-side, that's a signal worth tracking separately.
