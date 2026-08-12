# [Schema Enhancement] Add an `ai_tool` object to the `ai_operation` profile for MCP primitive metadata

## Summary

When an AI agent invokes a Model Context Protocol (MCP) primitive — a **tool**,
a **resource**, or a **prompt** — OCSF has no structure to record *what* was
invoked or *where it came from*. This proposes a small `ai_tool` object on the
`ai_operation` profile so that the invoked capability is a first-class,
queryable part of the event, alongside the `ai_agent` (the actor) and `ai_model`
(the model) the profile already defines. The name parallels `ai_agent`/`ai_model`
and avoids collision with OCSF's existing `product` object (which represents the
security tool that generated telemetry).

## The gap

OCSF models the *transport* and the *actor* of an AI tool call well, but not the
*capability* being invoked. API Activity (`6003`) already carries the HTTP
envelope (`http_request` / `http_response`), an `api.operation` string, an
`actor`, and affected `resources[]`; the `ai_operation` profile adds `ai_agent`,
`ai_model`, `delegation`, and `message_context`. But none of these can express
the facts that matter for reasoning about an MCP call: **which kind of primitive
it was** (tool vs. resource vs. prompt), **which server served it**, **what
input/output contract (schema) it advertised**, and **what safety annotations it
declared** (e.g. read-only vs. destructive). Today the primitive kind is
flattened into the free-text `api.operation` string, the serving server is not
recorded at all, and `message_context` — a conversation-turn object holding
roles and prompt/response text — has no home for a capability's identity or
provenance. As a result, a SIEM cannot answer questions OCSF exists to make
answerable: *"every call to a tool served by server X"*, *"every write-capable
tool an agent invoked"*, or *"resource reads vs. tool calls"* — the data is
either absent or buried in vendor-specific free text.

## Proposed addition

Add a new `ai_tool` object, referenced (optional) from the `ai_operation` profile.
It records the invoked primitive; it does **not** duplicate the transport
(`http_request`/`api`) or the affected objects (`resources[]`), which remain the
right home for those.

| Attribute | Requirement | Type | Description |
|---|---|---|---|
| `name` | Required | String | The primitive's name (tool name, resource name, or prompt name). |
| `type_id` | Recommended | Integer (enum) | Primitive kind: `0` Unknown, `1` Tool, `2` Resource, `3` Prompt, `99` Other. |
| `type` | Optional | String | The enum's string sibling. |
| `uid` | Optional | String | The invocation/call identifier that correlates a request with its result. |
| `namespace` | Optional | String | Namespace or grouping the primitive belongs to. |
| `server` | Optional | Object | The MCP server that served the primitive — `{ uid, name, transport }`, where `transport` is `stdio` \| `streamable_http` \| `other` (per the MCP transport spec). Provenance. |
| `input_schema` | Optional | Object | The declared input contract, by reference — `{ uid }` (e.g. a schema fingerprint), not the schema body. |
| `output_schema` | Optional | Object | The declared structured-output contract, by reference — `{ uid }`. |
| `annotations` | Optional | Object | Declared safety hints: `read_only`, `destructive`, `idempotent`, `open_world` (booleans). |
| `uri` | Optional | String | For `type_id = 2` (Resource): the resource URI. |
| `data_type` | Optional | String | For `type_id = 2` (Resource): the resource MIME type. |

A minimal example (a read-only tool served over MCP):

```jsonc
"ai_tool": {
  "type_id": 1,
  "name": "get_weather",
  "uid": "call_abc",
  "namespace": "weather",
  "server": { "uid": "weather-mcp", "name": "Weather MCP Server", "transport": "streamable_http" },
  "input_schema":  { "uid": "sha256:…" },
  "output_schema": { "uid": "sha256:…" },
  "annotations": { "read_only": true, "destructive": false }
}
```

### Optional forward-looking fields (MCP 2026-07-28 RC)

The current MCP Release Candidate adds three concepts that will produce
OCSF-worthy signals with no field to hold them; including them now avoids a
second round trip. Each is optional and independently justified:

| Attribute | Type | Why it is security-relevant |
|---|---|---|
| `cache_scope` | String (enum: `per_user`, `shared`, `unknown`, `other`) | The RC's `cacheScope` declares whether a result is safe to share across users. Recording it makes cross-tenant caching of user-specific data auditable — a data-exposure question nothing else on the event answers. |
| `cache_ttl` | Integer (ms) | The RC's `ttlMs` freshness window; bounds how long a result was treated as valid. |
| `task_uid` | String | The RC's Tasks extension returns a task handle for long-running calls; this correlates the originating call with later `tasks/get` / `update` / `cancel` events so an async tool lifecycle stays one thread instead of fragmenting across uncorrelated events. |

## Justification

Each field earns its place against a concrete forensic question that cannot be
answered today:

- **`type_id` (primitive kind).** MCP defines three distinct primitives with
  different risk profiles; collapsing them into `api.operation` free text makes
  "resource reads vs. tool calls" un-queryable. A first-class discriminator is
  the single most valuable field here.
- **`server`.** Tool provenance is a supply-chain question — *"which server
  served the tool this agent ran?"* — and there is no field for it anywhere on
  the event. This is the field most needed for trust and blast-radius analysis.
  Its `transport` (`stdio` vs `streamable_http`) further distinguishes a
  local-subprocess tool from a remote networked server — a real trust boundary,
  and the reason an event's endpoint fields may legitimately be empty (stdio has
  no network endpoint). MCP defines exactly these two standard transports plus
  optional custom ones; OCSF has no field for them today (`protocol_name` is
  IP-layer, and stdio is not a network protocol at all).
- **`annotations`.** MCP tools self-declare `readOnlyHint` / `destructiveHint` /
  etc. These are exactly the signals a reviewer wants to pivot on ("every
  destructive tool invoked under delegated authority"), and they also let a
  producer set `activity_id` to Read for a read-only tool rather than a generic
  invoke.
- **`input_schema` / `output_schema` (by reference).** Recording the contract
  *identity* (a fingerprint), not its body, keeps events small while letting a
  SIEM group by tool-contract version and detect drift — without carrying large
  JSON Schema documents on every event.
- **`uid`.** Correlates a call with its result across two events at the
  capability layer (distinct from `api.request.uid`, which is transport-scoped).

### Scope and non-duplication

This object is deliberately narrow. It reuses `http_request`/`api` for
transport, `resources[]` for affected objects, and `ai_agent`/`ai_model`/
`delegation` for the actor, model, and authority. Schemas are referenced, not
embedded; the per-call argument values and results go in `api.request.data` /
`api.response.data` (subject to the producer's redaction policy), while
`ai_tool` holds only the invariant description of the capability. The object is protocol-neutral — MCP is the motivating binding, but a
`function`- or `builtin`-sourced tool populates the same shape (omitting the
`server` and MCP-specific fields).

**Relationship to the network path / hops.** The network path to the server —
including any gateway an MCP call traverses — is *out of scope* for this object;
it is already owned by `src_endpoint` / `dst_endpoint`, the `network_proxy`
profile, and the `trace` object (per-hop events correlated by `trace.uid`).
`ai_tool.server` is **not** a network endpoint: when a gateway sits in the path,
`dst_endpoint` is the *gateway*, while `ai_tool.server` is the *logical* MCP
server that actually served the primitive behind it — an application-layer
identity the transport objects cannot express. The two are complementary, not
redundant. (Credential/authority hops — e.g. token exchange at each gateway —
are a third, separate concern, carried by the `delegation` object, not here.)

## Open questions

1. **A source axis?** Should the object also carry *how* the primitive was
   invoked (`mcp` / `function` / `builtin`), kept orthogonal to `type_id` (which
   is *what kind* of primitive)? Proposed as a follow-up, not part of the
   minimal ask.
2. **`activity_id` at the content layer.** A content-layer producer has no HTTP
   verb and would derive `activity_id` (Read vs. Create/Update) from the
   `annotations.read_only` hint rather than the method. Worth a one-line note in
   the profile guidance so producers are consistent.
3. **`cache_scope` enum values.** Confirm the value set OCSF wants to
   standardize beyond `per_user` / `shared`.

## References

- Model Context Protocol specification — tool / resource / prompt primitives and
  tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`,
  `openWorldHint`).
- MCP 2026-07-28 Release Candidate — `cacheScope`, `ttlMs`, Tasks extension.
- OCSF `ai_operation` profile (current: `ai_agent`, `ai_model`, `delegation`,
  `message_context`) and API Activity class (`6003`).
