# OCSF Issues — Working Draft (Jeff + CoSAI WS4)

**Purpose:** Shared scratchpad to draft the OCSF gap issues before filing. One
section per issue — we tighten the wording together, then each becomes its own
GitHub issue in `ocsf/ocsf-schema`. Keep each short: problem + a small
proposed-schema table + one or two real use cases.

**Contributors:** Jeff Leva (AI Identity — telemetry/forensics reference impl);
Fred Araujo (IBM — CMF/CPEX runtime enforcement); Teryl Taylor (IBM Research).

**Status legend:** DRAFT, REVIEW, READY, FILED #xxxx

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

## ISSUE 1 — MCP tool / resource / prompt metadata has no OCSF home
**Status:** DRAFT · **Lead:** Fred (his #1)

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
| `tool.type` | string (enum) | ✓ | invocation source: `mcp` \| `function` \| `builtin` |
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
    "type": "mcp",
    "mcp": { "server_name": "filesystem", "resource_uri": "file:///repo/README.md" }
  }
}
```

This composes with the in-review **`ai_agent` (#1641)** and **attestation
(#1661)** objects already on the profile — the `tool` object says what the agent
did; those say who acted and that the record is intact.

**Open questions (for Teryl / Fred)**
1. Generic vs MCP-specific. Prefer a generic `tool` object with MCP as one type,
   or a dedicated MCP object? (Leaning generic for OCSF neutrality.)
2. Attachment point. Hang `tool` off the `ai_operation` profile (rides any
   class) or scope it to API Activity 6003?
3. CMF alignment. CMF `ContentPart` already types `tool_call` / `tool_result` —
   align names so CPEX↔OCSF maps 1:1 rather than introducing a third vocabulary?

---

## ISSUE 2 — Agentic framework context has no OCSF home
**Status:** DRAFT · **Lead:** Fred · **Pairs with Issue 1**

**Problem.** Orchestration context for a multi-step run has only a *partial* OCSF
home. Per Ania (2026-06-29), `ai_agent.type_id` is already an **agent-framework
enum**, so the framework *type* is partly covered — the genuinely missing piece
is the **run / graph identifiers** that correlate the events of a single run.
Pairs naturally with the MCP add.

**Proposed change.** Companion attributes (same context object as Issue 1, or
sibling). Scope narrowed to what `ai_agent` doesn't already carry.

| Attribute | Type | Notes |
|---|---|---|
| `framework_name` | string | partly covered by `ai_agent.type_id` (framework enum); add only if a free-text/version beyond the enum is needed |
| `framework_version` | string | not in the enum — candidate add |
| `run_id` / `graph_id` | string | **the genuinely missing piece** — correlates a multi-step run; not carried by `ai_agent` |

**Use cases.** Jeff — attribute events to a specific agent run. IBM — aligns CMF
framework context to OCSF.

**Open questions.** Bundle with Issue 1 into one proposal, or file separately?
(Lean: one combined proposal — same surface.) Confirm the existing
`ai_agent.type_id` enum values before proposing `framework_name`, so we don't
duplicate the enum.

---

## ISSUE 3 — Security labels + monotonic (append-only) semantics
**Status:** DRAFT · **Lead:** IBM ask + Jeff forensics alignment

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
dropped. Jeff — maps to CMF `MutabilityTier` (immutable/monotonic/mutable,
`tiers.rs`), same append-only provenance as the forensics/DSSE work.

**Open questions.** Bigger ask — does OCSF have appetite to prescribe entity
semantics (not just shapes)? Entity-type semantics came up on the OCSF call (IUT
ref) — cite for precedent.

---

## ISSUE 4 — Completion `stop_reason` missing from OCSF
**Status:** READY · **Lead:** Jeff · Small patch

**Problem.** `stop_reason` (why a completion ended — stop / length / tool_use /
etc.) is common across LLM APIs but isn't represented in OCSF (no AI/completion
class carries it).

**Proposed change.**

| Attribute | Type | Notes |
|---|---|---|
| `stop_reason` | string/enum | end-of-completion reason |

Verified 2026-06-27 (upstream/main, fetched live): no `stop_reason` /
`finish_reason` field exists anywhere in OCSF, and the merged `ai_operation`
profile has no equivalent. (The earlier "partial / already merged" note referred
to the OCSF repo, not Jeff's PRs — no such field is present now. If it meant an
adjacent enum rather than a literal field, worth one confirm; otherwise, a
genuine gap.)

**Use cases.** Jeff — distinguish a clean stop from a truncation in the record.
IBM — same signal for runtime decisions.

---

## ISSUE 5 — Workload attestation state needs a first-class signal
**Status:** DRAFT · **Lead:** IBM + Jeff

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

**Use cases.** IBM — runtime enforcement on attested workloads. Jeff — record the
attestation state alongside, not merged into, the signed event chain.

**Open question (CMF alignment).** Does CPEX expose a workload identifier (image
/ model digest) + attestation result that we can map 1:1 into this object? The
record's signer / co-signature stays in `record_integrity` / #1661, not here —
per the precision trap above.

---

## ISSUE 6 — Correlation + delegation-path lineage
**Status:** DRAFT · **Lead:** Jeff · **aligns with Ania's delegation PR #1665**

**Problem.** Need a correlation id + delegation-path (who-acted-on-behalf-of-
whom). CMF `delegation.chain` is close to an OCSF delegation lineage. Also
demanded by ODIS ("Delegation Chain Record").

**Proposed change.** Reuse one existing attribute + converge on #1665's
delegation object rather than inventing a parallel one:

| Attribute | Type | Notes |
|---|---|---|
| `correlation_uid` | existing OCSF attribute | ties related events together — reuse, don't invent a new field |
| delegation lineage | object | **converge on #1665's delegation object** (parent references for lineage) — confirm it carries the forensic/CMF use cases; don't add a parallel `delegation_chain[]` |

Verified 2026-06-27: OCSF already has `correlation_uid` (in the dictionary) —
reuse it. **Update (Ania, 2026-06-29):** #1641 adds the `ai_agent` identity
object only (no lineage), **but her open delegation PR #1665 already adds a
delegation object with parent references for lineage.** So this is **not net-new**
— converge on #1665's shape (and add the `correlation_uid` tie if it isn't
already there) rather than a parallel `delegation_chain[]`. Ania offered to walk
through #1665.

**Use cases.** Jeff — reconstruct a delegation chain in forensics. IBM — map CMF
`delegation.chain` to OCSF.

**Open question (for Teryl / Ania).** Attribute naming — align with #1665 and CMF
`delegation.chain` so CPEX ↔ OCSF maps 1:1 rather than introducing a third
vocabulary.

---

## Filing checklist (per issue, before GitHub)
- Problem in 2-3 sentences, no jargon pile-up
- Proposed-schema table present and minimal
- At least one concrete use case (telemetry and/or enforcement)
- Verified against existing OCSF schema / open PRs (especially Issues 4 and 6)
- Filed as an individual contribution (vendor-neutral — not an AI Identity or IBM pitch)
- One issue = one section; don't bundle unrelated gaps

> **Note:** CMF field names (`tiers.rs`, `delegation.chain`) reflect IBM's CPEX
> `dev` branch (their source of truth) — verify against `dev` before citing
> publicly.
