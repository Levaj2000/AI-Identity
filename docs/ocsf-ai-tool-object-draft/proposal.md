# [Schema Enhancement] Add an `ai_tool` object to the `ai_operation` profile for MCP primitive metadata

> **v2.** Iterated from Teryl's 2026-08-12 draft. Shape changes are recorded in
> the [decision log](README.md); the accompanying `objects/`, `profiles/`, and
> `dictionary-additions.json` files are the proposal in PR-ready form, verified
> against `ocsf-schema` `main` (`1.10.0-dev`). The v1 → v2 diff of this document
> is the second commit on this branch.

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

Add a new `ai_tool` object (extending `_entity`), referenced (optional) from the
`ai_operation` profile. It records the invoked primitive; it does **not**
duplicate the transport (`http_request`/`api`) or the affected objects
(`resources[]`), which remain the right home for those. Per OCSF metaschema
rules, every attribute below is either an existing `dictionary.json` entry
(marked *reused*) or a new entry defined in `dictionary-additions.json` — there
are no anonymous inline objects.

| Attribute | Requirement | Type | Description |
|---|---|---|---|
| `name` | Required | String *(reused)* | The primitive's name as advertised by its provider (tool, resource, or prompt name). |
| `type_id` / `type` | Recommended | Integer enum + string sibling | Primitive kind: `0` Unknown, `1` Tool, `2` Resource, `3` Prompt, `99` Other. |
| `uid` | Recommended | String *(reused)* | The **capability's** stable identifier (registry ID, or a producer-derived stable key such as server uid + name). Not the call ID — see `transaction_uid`. |
| `transaction_uid` | Optional | String *(reused)* | The capability-layer invocation ID correlating a request with its result (for MCP, the JSON-RPC request id). Distinct from `api.request.uid`, which is transport-scoped. |
| `namespace` | Optional | String *(reused)* | Namespace or grouping the primitive belongs to. |
| `source_id` / `source` | Recommended | Integer enum + sibling *(reused attr, object-local enum)* | How the capability was provided: `1` MCP, `2` Function (framework-native), `3` Built-in (provider-hosted), `0`/`99`. Orthogonal to `type_id`. |
| `service` | Recommended | `service` object *(reused)* | The **logical** serving system — for MCP, the MCP server (`uid`, `name`, `version`). Provenance, not a network endpoint; see the non-duplication section. |
| `transport_id` / `transport` | Optional | Integer enum + sibling | Transport binding to the serving system: `1` stdio, `2` Streamable HTTP, `3` HTTP+SSE (legacy), `0`/`99`. |
| `is_readonly` | Optional | Boolean *(reused)* | Declared `readOnlyHint`. Self-declared and unverified — see Justification. |
| `is_destructive` | Optional | Boolean | Declared `destructiveHint`. Self-declared and unverified. |
| `is_idempotent` | Optional | Boolean | Declared `idempotentHint`. Self-declared and unverified. |
| `is_open_world` | Optional | Boolean | Declared `openWorldHint`. Self-declared and unverified. |
| `input_schema_fingerprint` | Optional | `fingerprint` object *(reused)* | The declared input contract by reference: a reproducible fingerprint (`algorithm_id`, `encoding_id`, `serialization_id` — use `JCS` for canonical JSON), not the schema body. |
| `output_schema_fingerprint` | Optional | `fingerprint` object *(reused)* | The declared structured-output contract, by reference. |
| `uri` | Optional | URL *(reused)* | For `type_id = 2` (Resource): the resource URI. |
| `mime_type` | Optional | String *(reused)* | For `type_id = 2` (Resource): the resource MIME type. |
| `version` | Optional | String *(reused)* | The capability's advertised version, when versioned. |

A minimal example (a read-only tool served over MCP) — the full event is in
`example-event.json`:

```jsonc
"ai_tool": {
  "type_id": 1,
  "name": "get_weather",
  "uid": "weather-mcp/get_weather",
  "transaction_uid": "call_abc",
  "namespace": "weather",
  "source_id": 1,
  "service": { "uid": "weather-mcp", "name": "Weather MCP Server", "version": "2.3.0" },
  "transport_id": 2,
  "is_readonly": true,
  "is_destructive": false,
  "input_schema_fingerprint":  { "algorithm_id": 3, "serialization_id": 2, "value": "b5bb9d80…" },
  "output_schema_fingerprint": { "algorithm_id": 3, "serialization_id": 2, "value": "7d865e95…" }
}
```

### Optional forward-looking fields (MCP 2026-07-28 RC)

The current MCP Release Candidate adds three concepts that will produce
OCSF-worthy signals with no field to hold them; including them now avoids a
second round trip. Each is optional and independently justified:

| Attribute | Type | Why it is security-relevant |
|---|---|---|
| `cache_scope_id` / `cache_scope` | Integer enum + sibling: `0` Unknown, `1` Public, `2` Private, `99` Other | The RC's `cacheScope` (SEP-2549) is `public` \| `private`, modeled on HTTP Cache-Control; the enum mirrors the spec. A `Private` result cached in a shared scope is a cross-user data exposure — a question nothing else on the event answers. |
| `cache_ttl` | Long (ms) | The RC's `ttlMs` freshness window; bounds how long a result was treated as valid. |
| `task_uid` | String | The RC's Tasks extension returns a task handle for long-running calls; this correlates the originating call with later task lifecycle events (`get` / `update` / `cancel`) so an async tool lifecycle stays one thread instead of fragmenting across uncorrelated events. |

**Placement caveat:** in the RC, `cacheScope`/`ttlMs` ride on *responses*
(`tools/list`, `resources/read`, …), so they are declared caching metadata
observed at serving time, not invariant capability properties. They are kept
here for pragmatic single-home reasons, with descriptions that say so — whether
they instead belong nearer `api.response` is an open question.

## Justification

Each field earns its place against a concrete forensic question that cannot be
answered today:

- **`type_id` (primitive kind).** MCP defines three distinct primitives with
  different risk profiles; collapsing them into `api.operation` free text makes
  "resource reads vs. tool calls" un-queryable. A first-class discriminator is
  the single most valuable field here.
- **`service` + `transport_id`.** Tool provenance is a supply-chain question —
  *"which server served the tool this agent ran?"* — and there is no field for
  it anywhere on the event. This is the field most needed for trust and
  blast-radius analysis. The transport (`stdio` vs `Streamable HTTP`) further
  distinguishes a local-subprocess tool from a remote networked server — a real
  trust boundary, and the reason an event's endpoint fields may legitimately be
  empty (stdio has no network endpoint). OCSF has no field for this today
  (`protocol_name` is IP-layer, and stdio is not a network protocol at all).
  The `ai_agent.type_id` description already promises that communication
  protocols (MCP, A2A) "are surfaced on the relevant operation rather than
  here" — this is that slot.
- **`is_readonly` / `is_destructive` / `is_idempotent` / `is_open_world`.**
  MCP tools self-declare these hints, and they are exactly the signals a
  reviewer wants to pivot on ("every destructive tool invoked under delegated
  authority"). **They are also self-declared and unverified**: a malicious or
  compromised server can label a destructive tool read-only, so the attribute
  descriptions state that the hints support triage, must not be treated as
  enforced properties, and that a mismatch between declaration and observed
  behavior is itself a detection signal. The profile guidance permits deriving
  `activity_id` from the hints (e.g., declared-read-only → `Read`) only when
  observed behavior does not contradict the declaration.
- **`input_schema_fingerprint` / `output_schema_fingerprint`.** Recording the
  contract *identity*, not its body, keeps events small while letting a SIEM
  group by tool-contract version and detect drift — including "rug pull"
  changes where a tool's schema silently changes after initial approval.
  Reusing OCSF's `fingerprint` object (rather than an opaque string) makes the
  fingerprint reproducible: `serialization_id: JCS` pins the canonicalization,
  so independent producers converge on the same value.
- **`transaction_uid`.** Correlates a call with its result across two events at
  the capability layer (distinct from `api.request.uid`, which is
  transport-scoped), while `uid` stays what `_entity` semantics say it is: the
  identity of the capability itself.
- **`source_id`.** A protocol-neutral object must be able to say *how* the
  capability was bound — MCP server, framework-native function, or provider
  built-in — or consumers cannot separate the very bindings this proposal
  describes. (Promoted from v1's open question 1.)

### Scope and non-duplication

This object is deliberately narrow. It reuses `http_request`/`api` for
transport, `resources[]` for affected objects, and `ai_agent`/`ai_model`/
`delegation` for the actor, model, and authority. Schemas are referenced, not
embedded; the per-call argument values and results go in `api.request.data` /
`api.response.data` (subject to the producer's redaction policy), while
`ai_tool` holds only the invariant description of the capability (the one
deliberate exception being the observed-declaration cache fields, flagged
above). The object is protocol-neutral — MCP is the motivating binding, but a
`Function`- or `Built-in`-sourced tool populates the same shape (omitting the
`service` and MCP-specific fields). And because the `ai_operation` profile is
attached at the category level (application, network, IAM, system), `ai_tool`
will surface on many classes beyond API Activity — no attribute description
assumes HTTP or MCP.

**Relationship to the network path / hops.** The network path to the server —
including any gateway an MCP call traverses — is *out of scope* for this object;
it is already owned by `src_endpoint` / `dst_endpoint`, the `network_proxy`
profile, and the `trace` object (per-hop events correlated by `trace.uid`).
`ai_tool.service` is **not** a network endpoint: when a gateway sits in the path,
`dst_endpoint` is the *gateway*, while `ai_tool.service` is the *logical* MCP
server that actually served the primitive behind it — an application-layer
identity the transport objects cannot express. The two are complementary, not
redundant. (Credential/authority hops — e.g. token exchange at each gateway —
are a third, separate concern, carried by the `delegation` object, not here.)
Relatedly, `message_context.service` ("the server or service handling the
request") partially overlaps; the profile guidance should state that when both
apply, `ai_tool.service` is the capability's serving system and
`message_context.service` is the conversation-level AI service.

## Open questions

1. **Naming.** `ai_tool` parallels `ai_agent`/`ai_model` and matches industry
   usage ("tool calling"), but an `ai_tool` with `type_id = Resource` reads
   oddly; `ai_capability` is the natural alternative. The collision-avoidance
   argument vs. `product` holds either way.
2. **Cache fields placement.** Keep `cache_scope_id`/`cache_ttl` on `ai_tool`
   as observed-declaration metadata (single home, at the cost of the
   invariance caveat), or move them toward `api.response`?
3. **`activity_id` derivation wording.** The draft profile guidance permits
   hint-derived `activity_id` unless observed behavior contradicts the
   declaration — does the working group want stronger wording (observed
   behavior always wins) given the hints are unverified?
4. **Transport placement.** `transport_id` sits on `ai_tool` (it describes how
   the client reached the serving system for *this* capability); an alternative
   is a dedicated MCP-server object carrying its own transport. The `service`
   reuse avoids a new object now.

## References

- [Model Context Protocol specification](https://modelcontextprotocol.io/specification) —
  tool / resource / prompt primitives and tool annotations (`readOnlyHint`,
  `destructiveHint`, `idempotentHint`, `openWorldHint`).
- [MCP 2026-07-28 Release Candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) —
  `cacheScope`/`ttlMs` (SEP-2549; values `public` | `private`), Tasks extension.
- OCSF `ai_operation` profile (current: `ai_agent`, `ai_model`, `delegation`,
  `message_context`) and API Activity class (`6003`), verified against
  `ocsf-schema` `main` at `1.10.0-dev`, 2026-08-12.
- `README.md` in this directory — file map and v1 → v2 decision log.
