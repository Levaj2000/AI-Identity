# Draft reply — OCSF Slack, Mitchell Wasson (Cisco) on MCP calls as OCSF

**Context:** 2026-08-11, OCSF community Slack. Mitchell Wasson (Cisco) asked
whether anyone is representing AI agent logs (Codex, Claude) in OCSF and
which event type to use for MCP calls — "thinking of possibly using API
Activity." That is our production shape, and the gap he'll hit is Issue 1 of
the CoSAI WS4 issues draft (`docs/cosai-ws4-ocsf-mapping/ocsf-issues-draft-with-teryl.md`
— the `tool` object).

**Filing ownership (settled 2026-08-11):** Teryl leads the upstream filing of
the MCP-gap issue with Jeff as co-author — agreed directly, superseding the
draft's earlier "Lead: Fred" note. Teryl is in CoSAI but **not** in the OCSF
community Slack, so this reply deliberately keeps the proposal at
one-sentence altitude: no field sketch, no "happy to share the draft," no
channel discussion the author can't join. Jeff's role in-channel is
connector — confirm the production shape, name the gap, and route Cisco's
interest to the issue once Teryl files it.

**Posting notes:** paste the body below into the Slack thread. When the
issue lands upstream, follow up in the same thread with the link so
Mitchell/Cisco can register their use case on the record.

---

Hi Mitchell — yes, we're doing exactly this in production at AI Identity.
API Activity (6003) with the `ai_operation` profile is the right call, and
it's what our gateway emits today — one event per agent call/decision,
`ai_agent` (merged via #1641) carrying agent identity, allow/deny in
`action_id`, latency in `duration`, and the `record_integrity` profile
(1.9, #1661) on top if you want tamper-evident chains. Real export you can
poke at, 236 events, schema-conformant with verifiable signatures:
https://github.com/levaj2000/ai-identity/tree/main/docs/cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle

One thing you'll hit quickly: MCP call identity has no structured home yet.
The tool name ends up smuggled into `api.operation` as a path string, and
the MCP server identity / resource URI / prompt name have nowhere to go but
`unmapped` — so tool usage isn't queryable or comparable across producers.
There's a proposal to close exactly that gap coming out of the CoSAI WS4 /
OCSF alignment work — it should land as an ocsf-schema issue soon, and a
second producer hitting the same wall is great timing. I'll ping this thread
when it's filed so Cisco's use case can weigh in on the record.

Also worth watching: ocsf-schema#1724 (agent trust-base inventory) covers
the complementary side — tool *schemas* as declared/loaded configuration,
where the per-call events cover invocation.
