# OCSF Extension Request — Draft for Filing Post-Vacation

**Status:** Draft, ready to file Tuesday 2026-05-26 (post-Memorial Day)
**Created:** 2026-05-15 · **Updated:** 2026-05-24 (placeholder UID language, spec repo marked live)
**Authorized by:** Decision #50 (Gate 1 commitment — file OCSF extension request)
**Target repo:** https://github.com/ocsf/ocsf-schema
**Action type:** New GitHub Discussion Issue (not a PR — see "Why a discussion issue first" below)

---

## Pre-filing checklist (do these in order, then file)

1. ✅ **Create the spec repo** — DONE 2026-05-24. Live at https://github.com/ai-identity/forensic-audit-trail-spec (Apache-2.0 + CC-BY-4.0, JSON Schema validated).
2. ✅ **Strip preemptive UID claims from the issue body** — DONE 2026-05-24. Body now uses vendor-namespace placeholders (1000000+ range) per OCSF convention instead of `class_uid 7001` / `category_uid 7`, which would have looked like preempting maintainers.
3. **Join `ocsf.slack.com`** (the OCSF community Slack) and post a brief heads-up in `#general` or `#proposals` — something like *"Filing a discussion issue shortly proposing a new AI Agent Activity event class, would welcome input."* This is the right etiquette before cold-filing. **Best done Sunday/Monday so Tuesday morning post lands without delay.**
4. **File the issue below** at https://github.com/ocsf/ocsf-schema/issues/new with the title and body verbatim. **Best timing: Tuesday 2026-05-26 mid-morning ET** (post-Memorial Day, weekday eyeballs in active inboxes).
5. **Mirror the filing on AI Identity's side** — close the loop by updating Decision #50 with the filed issue URL (sprint item #381).

## Why a discussion issue first (not a PR)

OCSF maintainers are at Splunk, AWS, Cloudflare, IBM, and others. Cold-filing a schema PR for a brand-new class is a faux pas — the convention is to file a discussion/RFC issue first, get community feedback on naming, attribute groupings, and whether the class belongs in core or as an extension, then submit the PR. Skipping the discussion phase signals you don't know the community's norms and dramatically lowers the chance of acceptance.

In parallel with the discussion issue, we ship our spec as a *private OCSF extension* so we are not blocked on the upstream timeline. The issue makes us a participant in the standards conversation; the extension lets us deliver to design partners.

---

## Issue title (paste into GitHub)

```
[Discussion] Proposal for a new "AI Agent Activity" event class in OCSF core
```

## Issue body (paste into GitHub)

````markdown
## Summary

This is a request for community discussion on adding a new event class to OCSF
core — provisional name **AI Agent Activity** — to capture the post-incident
telemetry needed to forensically reconstruct autonomous AI agent behavior.

I'm filing this from AI Identity, where we've published a draft v1.0
reference specification — the **AI Forensics Audit Trail Specification** —
that profiles OCSF as its event envelope alongside OpenTelemetry GenAI
semconv, MITRE ATLAS 2026, SPIFFE/SPIRE, NIST AI RMF, and the IETF Agent
Identity Protocol draft.

- Spec v1.0: https://github.com/ai-identity/forensic-audit-trail-spec
- Landing page: https://www.ai-identity.co/spec

In parallel with this discussion, we will publish our spec's class as a
private OCSF extension using vendor-namespace UIDs (1000000+ range, per
OCSF convention) so we can ship forensic-grade capture without preempting
working-group decisions on core class numbering. The intent of this issue
is to start the conversation about whether and how this class belongs in
OCSF core.

## Why existing OCSF classes don't fully cover this

Autonomous AI agent activity has telemetry requirements that don't map cleanly
to existing OCSF categories:

- **Process Activity (1007)** captures process lifecycle but not the
  prompt-chain, tool-invocation, or model-decision state that defines an
  agent step.
- **API Activity (6003)** captures API call telemetry but lacks the
  multi-pillar context that makes an agent action interpretable
  (system instructions, retrieved context, tool schemas as injected,
  guardrail verdicts, signing identity).
- **Authentication / Account Change** classes don't capture per-step
  workload identity bound to code/config attestation.

An agent step is a compound event: one model invocation → zero-or-more tool
calls → decision boundary → output, with cryptographic identity binding the
whole thing to a specific workload, build, and principal. Modeling it as a
new class avoids overloading any existing one.

## Proposed scope of the class

Required attribute groups (full schema is in the spec):

1. **Prompt-chain state** — system instructions hash, messages with
   provenance (`injected_by`, `trust_zone`), tool definitions as presented to
   the model, RAG retrievals with source URI and trust zone, memory ops, and
   a `context_image_sha256` anchor.
2. **Tool invocation** — full args/result (content-addressed and encrypted),
   side-effect manifest correlated to existing OCSF classes (Network Activity
   4001, File Activity 1001, Authentication 3002) via `downstream_trace_id`.
3. **Decision boundary** — model id + weights hash, sampling parameters,
   per-branch candidate actions with logprob/score, guardrail verdicts,
   policy overrides, refusal traces.
4. **Agent identity** — SPIFFE SVID, workload attestation evidence (image,
   code, config measurements), per-step Ed25519 signature, hash chain link
   to the previous event in the agent's chain.

Side effects of the agent action are deliberately emitted as separate native
OCSF events and joined by W3C trace context, so existing SIEM/connector
infrastructure does not need to change to ingest them.

## Why this matters now

MITRE ATLAS's 2026 update formalized agentic threat techniques (AML.T0096
AI Service API abuse, AML.T0098 AI Agent Tool Credential Harvesting,
AML.T0099 AI Agent Tool Data Poisoning, AML.T0100 AI Agent Clickbait, AML.T0101
Data Destruction via Tool Invocation) that cannot be detected or
investigated from current telemetry classes alone. NIST AI RMF Generative AI
Profile MS-2.6 / MS-2.10 / MG-4.1 call for tamper-evident, principal-bound
audit trails. The EU AI Act Article 12 requires automatic logging across the
AI system lifecycle. Multiple vendors are starting to publish ad-hoc
schemas — having one OCSF-blessed class would prevent fragmentation.

## What we're offering

If the maintainers are open to this conversation, we're committed to:

- Doing the schema-writing work and submitting a PR.
- Participating in any OCSF working group sessions on this.
- Sharing our draft schema, JSON Schema validators, and example events.
- Iterating on naming, attribute grouping, category placement, and UID
  assignment based on community feedback. We're using vendor-namespace
  UIDs as placeholders; final numbers are entirely up to the working group.

## Asks

1. Is OCSF core the right home for this, or should it live as an extension
   in a long-running namespace (e.g., a hypothetical `aigov` extension)?
2. Is there an existing working group or open discussion thread we should
   join rather than starting fresh here?
3. What is the typical cadence for landing a new class in core?

Happy to break this into smaller issues or PRs based on your preference.

— Jeff Leva, AI Identity
   jeff@ai-identity.co · https://www.ai-identity.co
````

---

## After filing — track the response

- The OCSF maintainers typically respond within 1–3 weeks for new-class discussions. Subscribe to the issue for notifications.
- Likely responses to prepare for:
  - **"Submit as an extension first, then propose for core after adoption."** — Acceptable. We'd publish the extension immediately (Gate 1) and revisit the core PR in 2026 H2.
  - **"Have you talked to the OTel GenAI working group?"** — Yes-ish. Spec maps cleanly to OTel GenAI semconv and elevates Opt-In attributes to Required. If asked, offer to join their next meeting.
  - **"Why not a sub-class of Process Activity (1007)?"** — Because an agent step is a compound event spanning prompt+tool+decision+identity, not a process lifecycle event. Be ready to defend this in §"Why existing OCSF classes don't fully cover this."
  - **"Can you split this into multiple smaller classes?"** — Possibly. The four pillars could be four events linked by trace context. Be open to this; it may improve adoption.

## Resolved 2026-05-24

The earlier open question about `class_uid 7001` / `category_uid 7` is resolved: the issue body has been updated to use vendor-namespace placeholder framing (1000000+ range, per OCSF convention), and neither the public spec (`SPEC-v1.0.md`) nor the JSON Schema references the 7001/7 numbers — so no further changes needed on the spec repo side.

---

*End of OCSF extension request draft. File Tuesday 2026-05-26 mid-morning ET.*
