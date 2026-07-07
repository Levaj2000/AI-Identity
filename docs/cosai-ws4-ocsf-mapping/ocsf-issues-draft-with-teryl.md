# OCSF Issues — Working Draft (Jeff + CoSAI WS4)

**Purpose:** Shared scratchpad to draft the OCSF gap issues before filing. One
section per issue — we tighten the wording together, then each becomes its own
GitHub issue in `ocsf/ocsf-schema`. Keep each short: problem + a small
proposed-schema table + one or two real use cases.

**Contributors:** Jeff Leva (AI Identity — telemetry/forensics reference impl);
Fred Araujo (IBM — CMF/CPEX runtime enforcement); Teryl Taylor (IBM Research).

**Status legend:** DRAFT, REVIEW, READY, FILED #xxxx

**Revision 2026-07-06 (iteration 2):** applied Teryl's CMF-verified redline
(`ocsf-gaps-cmf-redline.md`, verified against cpex `feat/hil_apl`) and the
mapping-review corrections that touch these issues (`cmf-ocsf-mapping-review.md`
C1/C2/C7). **Schema verification pass done same day:** all four [VERIFY] tags
resolved against upstream `ocsf/ocsf-schema` main (@ #1641 merge, `b268a0cc`)
and the live #1665 PR diff — resolutions inline, marked RESOLVED. Next: Fred
review, then file.

> ODIS context (CoSAI WS4, 2026-06-25): the group endorsed OCSF as the evidence
> / system-of-record layer for agent identity + delegation. These issues are
> what OCSF needs to be a complete evidence format.
>
> Delegation lineage is demanded by IBM CMF (`delegation.chain`) and ODIS
> ("Delegation Chain Record"). #1641 adds `ai_agent` identity, **not** lineage;
> per Ania (2026-06-29), her open delegation PR **#1665** already adds a
> delegation object with parent references for lineage — so ISSUE 6 is about
> converging on #1665's shape, not inventing a new one.

---

## Shared framing (settled 2026-07-06, per Teryl's cross-cutting edits)

**Three lineages, three homes.** These are different DAGs over the same run and
must not be conflated (they don't coincide):

| Lineage | Edge | Home |
|---|---|---|
| **Spawn** (who *created* whom — orchestration tree) | `agent.agent_id → parent_agent_id` | Issue 2 (sibling attribute) |
| **Delegation** (who *acts on behalf of* whom — authority graph) | `delegation.chain` hops w/ scopes/audience | Issue 6 / #1665 |
| **Message-derivation** (what *derived from* what — provenance DAG) | `provenance.parent_id` | Candidate issue (below) — NOT the hash chain; see mapping-review C2 |

**RESOLVED (2026-07-06, verified against the live #1665 diff):** #1665's object
is the *delegation* DAG (`uid` required, `parent_uid`, `created_time`,
`issuer_uid`; rides the `ai_operation` profile) — **but** `parent_uid`'s
description folds "re-delegation **or sub-agent spawning**" into one edge, i.e.
it partially conflates the spawn tree with the authority graph. **Raise with
Ania:** a spawn that doesn't change authority shouldn't mint a new delegation;
keep the spawn edge on the agent side (Issue 2's `parent_agent_uid`) and let
`delegation.parent_uid` mean re-delegation only.

**One correlation model.** `run_id` and `correlation_uid` are the same concept —
file one field, not two. CMF carries five candidate ids; the agreed mapping:

| Grain | CMF source | OCSF target |
|---|---|---|
| **Run** (primary forensic grain) | `agent.conversation_id` | **`correlation_uid`** (existing attribute — reuse) |
| Session (may span runs) | `agent.session_id` | `ai_agent.instance_uid` |
| Transport hop | `trace_id` / `span_id` | `metadata.trace_id` / `span_id` |
| Single tool call | `tool_call_id` | `api.request.uid` / `message_context.uid` — **never** `correlation_uid` (per-event ids correlate nothing; mapping-review C1) |

---

## ISSUE 1 — MCP tool / resource / prompt metadata has no OCSF home
**Status:** REVIEW (Teryl pass done) · **Lead:** Fred (his #1)

**Problem.** When an AI agent invokes a tool, OCSF has no structure to record
what tool it called or where the tool came from. In a gateway emitting API
Activity (`class_uid` 6003) today, the tool name is smuggled into the
`api.operation` path as a string, and any tool-source context (which MCP server,
which resource URI, which prompt) has no home — it's unmapped. That makes tool
usage non-queryable and non-interoperable: two producers will each invent a
different unmapped shape, and a consumer can't correlate "agent X called tool Y
on server Z" across them. MCP makes this acute — an MCP invocation carries a
server identity, a tool/resource/prompt reference, and a transport that OCSF
currently can't represent.

**Proposed change.** Add a small, generic `tool` object (carried on the
`ai_operation` profile, so it rides any class), with an optional MCP sub-block.
Generic-first keeps OCSF protocol-neutral; MCP is the first concrete type.

| Attribute | Type | Req | Notes |
|---|---|---|---|
| `tool.name` | string | ✓ | invoked tool, e.g. `read_file` |
| `tool.primitive` | string (enum) | ✓ | **what kind of primitive**: `tool` \| `resource` \| `prompt` — makes resource/prompt access first-class-queryable instead of buried inside a field named `tool` (Teryl structural edit; CMF treats the three as peer `ContentPart` variants + `ENTITY_*` taxonomy) |
| `tool.type` | string (enum) | ✓ | **invocation source**: `mcp` \| `function` \| `builtin` — orthogonal axis to `primitive`; keep both, don't merge |
| `tool.mcp.server_name` | string | – | MCP server identity |
| `tool.mcp.server_uid` | string | – | stable server id, when available |
| `tool.mcp.resource_uri` | string | – | resource accessed, when applicable |
| `tool.mcp.prompt_name` | string | – | prompt invoked, when applicable |

**Scope (v1):** identity/reference of the invocation only. Tool arguments and
results are out of scope for v1 — they carry sensitive payloads and belong in a
later, opt-in extension. This issue captures *which* tool ran, not *what* data
passed through it.

**Grounded example.** A real (scrubbed) gateway event today — note the tool name
trapped in `api.operation` and the absence of any tool-source structure:

```json
{
  "class_uid": 6003,
  "activity_id": 2,
  "metadata": { "profiles": ["ai_operation"] },
  "api": { "operation": "/ada/tools/read_file" },
  "ai_agent": { "uid": "a9c3e7d1-…", "name": "ada" },
  "unmapped": { "policy_version": 36, "status_code": 200 }
}
```

The same event with the proposed `tool` object — queryable, and MCP-ready:

```json
{
  "class_uid": 6003,
  "activity_id": 2,
  "metadata": { "profiles": ["ai_operation"] },
  "api": { "operation": "/ada/tools/read_file" },
  "ai_agent": { "uid": "a9c3e7d1-…", "name": "ada" },
  "tool": {
    "name": "read_file",
    "primitive": "tool",
    "type": "mcp",
    "mcp": { "server_name": "filesystem", "resource_uri": "file:///repo/README.md" }
  }
}
```

This composes with the merged **`ai_agent` (#1641)** and in-review **attestation
(#1661)** objects on the profile — the `tool` object says what the agent did;
those say who acted and that the record is intact.

**Resolved (Teryl, 2026-06-30/07-06):**
1. Generic vs MCP-specific → **generic.** CMF's taxonomy is protocol-neutral with
   MCP as one binding.
2. Attachment point → no CMF objection to the `ai_operation` profile.
3. CMF alignment → **confirmed 1:1-able**: CMF `ContentPart` serde tags
   (`tool_call`/`tool_result`/`resource`/`prompt_request`/…) already match; the
   one delta was the missing primitive discriminator — added above as
   `tool.primitive` (sourced from CMF `ENTITY_TOOL|RESOURCE|PROMPT|LLM`).

---

## ISSUE 2 — Agentic framework context has no OCSF home
**Status:** REVIEW (Teryl pass done) · **Lead:** Fred · **File separately from Issue 1**

**Problem.** Orchestration context for a multi-step run has only a *partial* OCSF
home. Per Ania (2026-06-29), `ai_agent.type_id` is already an **agent-framework
enum**, so the framework *type* is partly covered — the missing pieces are the
**graph/node identifiers** and the **spawn lineage** that place an event inside
an orchestrated run.

**Proposed change.** Companion attributes, scoped to what `ai_agent` doesn't
already carry. (CMF verification: `FrameworkExtension` carries `framework`,
`framework_version`, `graph_id`, `node_id` — richer than the first draft assumed.)

| Attribute | Type | Notes |
|---|---|---|
| `framework_version` | string | not in the `ai_agent.type_id` enum — candidate add; 1:1 with CMF |
| `graph_id` | string | orchestration graph identity — **maps 1:1 to CMF `graph_id` today** |
| `node_id` | string | position within the graph — CMF carries it; first draft missed it (Teryl add) |
| `parent_agent_uid` | string | **spawn lineage** (who spawned this agent) — the orchestration tree, distinct from delegation (see shared framing); maps to CMF `agent.parent_agent_id` |

~~`run_id`~~ — **dropped.** Run correlation is `correlation_uid =
conversation_id` (shared framing above); don't file two ids for one concept.

**Use cases.** Jeff — attribute events to a specific agent run and its position
in the orchestration. IBM — aligns CMF framework context to OCSF.

**Open questions.** ~~Bundle with Issue 1?~~ → **file separately** (Teryl lean:
the surface is "graph/node ids + spawn lineage," not "tool object").
**RESOLVED (2026-07-06, upstream main @ #1641 merge):** `ai_agent.type_id` enum
= `Unknown | Native | LangChain | AutoGen | CrewAI | Other` — framework *type*
only. No version, no graph/node ids, no parent reference anywhere on `ai_agent`.
One nuance to respect: `ai_agent.version` already exists but is defined as the
**agent's own code/config revision** — so the proposed `framework_version` is
genuinely distinct (don't overload `version`). All four proposed adds are clean.
**[DECIDE w/ Fred]** spawn lineage here as `parent_agent_uid` (as tabled) vs.
its own micro-issue.

---

## ISSUE 3 — Security labels + monotonic (append-only) semantics
**Status:** REVIEW (Teryl pass done) · **Lead:** IBM ask + Jeff forensics alignment

**Problem.** OCSF lacks (a) multi-level security labels with lattice /
partial-order semantics, and (b) a prescribed append-only / monotonic semantic —
labels addable, never removable — for robust access control.

**Proposed change.** Security-label object + a normative note that label sets are
monotonic:

| Attribute | Type | Notes |
|---|---|---|
| `labels[]` | string array | multi-level, lattice-ordered |
| `mutability` | enum | `immutable` / `monotonic` / `mutable` |

**Use cases.** IBM — robust access control where labels can't be silently
dropped. Jeff — maps to CMF `MutabilityTier` (`tiers.rs`), same append-only
provenance as the forensics/DSSE work.

**CMF precedent (Teryl verification — strongest 1:1 of the six).**
`MutabilityTier { Immutable, Monotonic, Mutable }` serializes exactly as the
proposed enum values — and it is **not label-specific**: it's the `tier` field on
`SlotPolicy`, applied to *every* extension slot (delegation, completion, labels,
…) as a generic, reusable field-level mutability contract. Labels themselves are
a `MonotonicSet<String>` (add-only). **Use this as the argument:** OCSF should
prescribe the mutability semantic **generically** (a reusable field-level
contract), not as a label-only special case — running-code precedent exists.

**Open questions.** The real risk stands: does OCSF have appetite to prescribe
entity *semantics* (not just shapes)? Entity-type semantics came up on the OCSF
call (IUT ref) — cite for precedent, plus the CMF generic-contract precedent above.

---

## ISSUE 4 — Completion `stop_reason` missing from OCSF
**Status:** READY (with Teryl's normalization edit) · **Lead:** Jeff · Small patch

**Problem.** `stop_reason` (why a completion ended) is common across LLM APIs but
isn't represented in OCSF (no AI/completion class carries it).

**Proposed change.**

| Attribute | Type | Notes |
|---|---|---|
| `stop_reason` | string (normalized enum) | end-of-completion reason — **OCSF defines a normalized vocabulary; producers map their native values into it** |

**Why normalized (Teryl verification).** Vendors genuinely disagree: CMF
`StopReason` is `end / return / call / max_tokens / stop_sequence`
(`completion.rs` — field confirmed, named `stop_reason` not `finish_reason`),
while Anthropic/OpenAI use `stop / length / tool_use`-style values. It's a
*mapping*, not identity (`call`→tool_use, `max_tokens`→length,
`end|stop_sequence`→stop). Don't mirror any one vendor's enum — define the
normalized set and let producers map in.

Verified 2026-06-27 (upstream/main, fetched live): no `stop_reason` /
`finish_reason` field exists anywhere in OCSF, and the merged `ai_operation`
profile has no equivalent. CMF side now also confirmed → clean
"both-runtimes-have-the-signal, OCSF-lacks-it" story.

**Use cases.** Jeff — distinguish a clean stop from a truncation in the record.
IBM — same signal for runtime decisions.

---

## ISSUE 5 — Workload attestation state needs a first-class signal
**Status:** REVIEW (reframed per Teryl — both-sides gap) · **Lead:** IBM + Jeff

**Problem.** Workload / runtime attestation (TEE quote, measured boot) lives in
ad-hoc extension fields. It needs a first-class OCSF signal — distinct from
record integrity.

**Proposed change.** Workload-attestation object separate from any
record-integrity/hash-chain fields:

| Attribute | Type | Notes |
|---|---|---|
| `attestation_type` | enum | e.g. TEE quote, measured boot |
| `attestation_evidence` | string | quote / evidence ref |
| `verified` | boolean | verification result |

**PRECISION TRAP.** Workload/runtime attestation (*is the environment
trustworthy?*) is NOT the same as record/action non-repudiation (*was the event
tampered with* — the entry-hash chain). Keep them as separate fields.

**Add — workload identity binding.** Record which workload was attested (image /
model-artifact digest), not just the attestation state. Where a process is
present, reuse `process.file.hashes[]` (SHA-256 = `algorithm_id` 3) rather than a
new field. Evidence is generic-first: a software-portable digest
(offline-verifiable) or a hardware-rooted TEE / RATS quote (RFC 9711) — hardware
additive, not required.

**Reframed (Teryl verification — the old open question is ANSWERED: no).**
CPEX has **no 1:1 today**: `WorkloadIdentity` carries SPIFFE attestation
*provenance* (`spiffe_id`, `trust_domain`, `attestor`, `attested_at`,
`selectors`) but **no artifact/image/model digest, no `verified` result, and no
attestation object exists in the workspace** (nor a `process.file` equivalent).
So Issue 5 is a real gap on **both** sides — which is the *stronger*
contribution story: the OCSF object and the CMF field get **co-designed**, not
retrofitted to an existing CPEX shape.

**Action (IBM side):** file a **paired CMF issue** — add image/model digest +
`verified` to CPEX so the 1:1 exists. [Owner: Teryl/Fred]

**Use cases.** IBM — runtime enforcement on attested workloads. Jeff — record the
attestation state alongside, not merged into, the signed event chain.

---

## ISSUE 6 — Correlation + delegation-path lineage
**Status:** REVIEW (Teryl pass done) · **Lead:** Jeff · **aligns with Ania's delegation PR #1665**

**Problem.** Need a correlation id + **delegation**-path lineage
(who-acted-on-behalf-of-whom — explicitly the *authority* graph, not the spawn
tree; see shared framing). CMF `delegation.chain` is close to an OCSF delegation
lineage. Also demanded by ODIS ("Delegation Chain Record").

**Proposed change.** Reuse one existing attribute + converge on #1665's
delegation object rather than inventing a parallel one:

| Attribute | Type | Notes |
|---|---|---|
| `correlation_uid` | existing OCSF attribute | reuse — **semantic pinned: `correlation_uid` = the run = CMF `agent.conversation_id`** (shared framing; must be multi-event-stable — not `request_id`, not `tool_call_id`) |
| delegation lineage | object | **converge on #1665's delegation object** — confirm it carries the forensic/CMF use cases; don't add a parallel `delegation_chain[]` |

**CMF verification (Teryl).** `DelegationExtension`: `chain: Vec<DelegationHop>`,
`depth`, `origin_subject_id`, `actor_subject_id`, `delegated`, `age_seconds`.
Each `DelegationHop`: `subject_id`, `subject_type`, `audience`, `scopes_granted`,
`authorization_details` (RFC 9396), `timestamp`, `ttl_seconds`, `strategy`
(TokenExchange | ClientCredentials | SpiffeSvid | Passthrough | Ucan |
TransactionToken | Custom), `from_cache`.

**Convergence checklist for #1665 (walk with Ania) — verified 2026-07-06
against the live PR diff:**
- ✅ #1665 = the *delegation* DAG, with one wording fix to request: `parent_uid`
  folds "sub-agent spawning" into re-delegation (see shared framing — spawn
  belongs on the agent side).
- ⚠️ **Confirmed: #1665 carries only the pointer skeleton** (`uid`,
  `parent_uid`, `created_time`, `issuer_uid`) — **no per-hop authority
  content**: no scopes, no audience, no `authorization_details`, no TTL. So CMF
  `DelegationHop` does NOT map 1:1 yet. This is the concrete contribution to
  bring to Ania: add the authority fields per delegation node
  (`scopes_granted[]`, `audience`, `authorization_details[]`, `expiration_time`)
  — as a follow-up to her PR, not a competing shape. Positive note: her
  `issuer_uid` ("generated by a trusted system component, not self-asserted")
  matches the gateway-issuance model exactly.
- **RAR rides the hop (mapping-review C7):** RFC 9396 `authorization_details`
  belong **inside each delegation hop**, not in a detached authorization object —
  and OCSF base has no RAR shape (`locations`/`actions`/`datatypes`/`privileges`),
  so that's a sub-gap of this issue, folded here rather than filed separately.
- Naming reconciliation: CMF `origin_subject_id`/`actor_subject_id` vs #1665's
  parent-reference naming; CMF `strategy` enum has no obvious OCSF home — raise
  as a sub-gap.

**Use cases.** Jeff — reconstruct a delegation chain in forensics. IBM — map CMF
`delegation.chain` to OCSF.

---

## Candidate issues (not yet in the six — decide with Fred)

**C-a. Message-derivation edge (`provenance.parent_id`) has no OCSF home.**
From mapping-review C2: the provenance DAG (what derived from what) must be
carried *as data* in each record — the attestation hash chain links records in
*emission* order and cannot represent *derivation* order. `message_context.uid`
carries a node's own id but there is no parent/derivation edge
(`message_context.parent_uid`-style). Without it the provenance graph is lost
even in a perfectly tamper-evident log. This is the **third lineage** (shared
framing). **RESOLVED (2026-07-06, upstream main):** confirmed — `message_context`
carries `uid`, `name`, `ai_role(_id)`, `application`/`service`, prompt/response/
token fields; **no parent or derivation edge exists**. A sibling
`message_context.parent_uid` is the natural minimal add. (Side observation for
the filing: `message_context.uid`'s own description says "session ID,
conversation ID, or other" — loose grain that overlaps the correlation model;
worth one clarifying sentence when this files.) Decide: fold into Issue 1/2's
`message_context` surface or file as its own micro-issue.

**C-b. Data governance / retention (Teryl's Q1 — candidate Issue 7).**
CMF carries object-level data-handling with no OCSF home:
`ObjectSecurityProfile` (`managed_by`, `permissions`, `trust_domain`),
`RetentionPolicy` (`max_age_seconds`, `delete_after`), `DataPolicy`
(`apply_labels`, `allowed/denied_actions`). Coherent, distinct, lower-priority
than the six. **RESOLVED (2026-07-06, upstream main) — the blocking check
passed; the gap is real:**
- There is **no Data Security *category*** (categories: application, discovery,
  findings, iam, network, remediation, system, unmanned_systems). What exists:
  `data_classification` (classification levels/categories/confidentiality, with
  a generic `policy` reference), and `data_security` (DLP/finding-oriented;
  its `data_lifecycle_state` enum is at-rest / in-transit / in-use — data
  *state*, not retention).
- **No retention semantics anywhere** — no `delete_after`, `max_age`, or
  retention-period field in the dictionary or any object; no allowed/denied
  data-handling actions contract. Generic `expiration_time` exists and is
  reusable for the delete-after moment.
- **Recommendation: FILE as Issue 7**, framed vendor-neutrally as *extending the
  existing `data_classification`/`policy` surface* with retention
  (`retention_period`, reuse `expiration_time`) + handling-actions — not as a
  new area. Keep it last in the queue.

---

## Filing checklist (per issue, before GitHub)
- Problem in 2-3 sentences, no jargon pile-up
- Proposed-schema table present and minimal
- At least one concrete use case (telemetry and/or enforcement)
- Verified against existing OCSF schema / open PRs (especially Issues 4 and 6)
- Filed as an individual contribution (vendor-neutral — not an AI Identity or IBM pitch)
- One issue = one section; don't bundle unrelated gaps
- ~~All inline [VERIFY] tags resolved~~ **DONE 2026-07-06** — all four resolved
  against upstream main (@ #1641 merge) + the live #1665 diff. Remaining human
  steps: Ania conversation (spawn-vs-redelegation wording + per-hop authority
  fields on #1665); Fred decisions (spawn-lineage placement; Issue 7 file order)

> **Note:** CMF field names (`tiers.rs`, `delegation.chain`, `completion.rs`,
> `security.rs`, `framework.rs`) reflect IBM's CPEX dev source of truth (branch
> `feat/hil_apl`, verified by Teryl 2026-06-30) — re-verify before citing
> publicly if the branch advances.
