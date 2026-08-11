# Draft reply — OCSF Slack, Mitchell Wasson (Cisco) on MCP calls as OCSF

**Context:** 2026-08-11, OCSF community Slack. Mitchell Wasson (Cisco) asked
whether anyone is representing AI agent logs (Codex, Claude) in OCSF and
which event type to use for MCP calls — "thinking of possibly using API
Activity." That is our production shape, and his gap-to-be is Issue 1 of the
CoSAI WS4 issues draft (`docs/cosai-ws4-ocsf-mapping/ocsf-issues-draft-with-teryl.md`
— the `tool` object, Teryl pass done, Fred lead, status REVIEW since July).

**Posting notes:** paste the body below into the Slack thread. A Cisco
producer asking this question in public is the multi-producer demand signal
Issue 1 has been waiting on — if Mitchell engages, the follow-up move is to
file Issue 1 upstream with Cisco named as an interested producer alongside
the IBM/CMF alignment.

---

Hi Mitchell — yes, we're doing exactly this in production at AI Identity.
Short version: API Activity (6003) with the `ai_operation` profile is the
right call, and it's what our gateway emits today — one event per agent
call/decision, `ai_agent` (merged via #1641) carrying agent identity,
allow/deny in `action_id`, latency in `duration`, and the `record_integrity`
profile (1.9, #1661) on top if you want tamper-evident chains. Real export
you can poke at, 236 events, schema-conformant with verifiable signatures:
https://github.com/levaj2000/ai-identity/tree/main/docs/cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle

The catch you'll hit quickly: MCP call identity has no structured home yet.
The tool name ends up smuggled into `api.operation` as a path string, and
the MCP server identity / resource URI / prompt name have nowhere to go but
`unmapped` — so tool usage isn't queryable or comparable across producers.
We've been drafting a proposal for exactly this with the CoSAI WS4 folks
(cross-checked against IBM's CMF taxonomy): a small generic `tool` object on
the `ai_operation` profile — `name`, `primitive` (tool | resource | prompt),
`type` (mcp | function | builtin), plus an optional `mcp` sub-block
(`server_name`, `server_uid`, `resource_uri`, `prompt_name`). Identity of
the invocation only in v1; args/results deliberately out of scope (sensitive
payloads).

Related thread worth watching: ocsf-schema#1724 (agent trust-base inventory)
covers the complementary side — tool *schemas* as declared/loaded
configuration, where the per-call events cover invocation.

If Cisco's landing on the same shape, that's exactly the multi-producer
signal this needs — happy to share the full draft and compare notes before
we file it.
