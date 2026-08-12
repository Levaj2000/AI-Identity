# OCSF Object Draft — `ai_tool` on the `ai_operation` profile

A PR-shaped draft of the `ai_tool` object proposed in `proposal.md` (Teryl
Taylor's MCP primitive metadata proposal, iterated per the review below).
Files are laid out exactly as they would land in the `ocsf-schema` repo;
conventions were verified against `main` (`1.10.0-dev`) on 2026-08-12 —
object shape from `objects/ai_agent.json` / `objects/ai_model.json`, profile
attachment from `profiles/ai_operation.json`, dictionary collisions checked
by name, and every attribute in the draft object cross-checked against
`dictionary.json` (reused entries exist; new entries are in the fragment).

**This is a draft for discussion, not a filed PR.** Requirement levels, enum
values, and the object name itself are the working group's to decide; the
open questions are called out at the bottom and in `proposal.md`.

## File map — where each file lands in ocsf-schema

| This directory | ocsf-schema destination |
|---|---|
| `objects/ai_tool.json` | `objects/ai_tool.json` (new) |
| `profiles/ai_operation.json` | `profiles/ai_operation.json` (adds the `ai_tool` attribute; otherwise unchanged) |
| `dictionary-additions.json` | merged into `dictionary.json` `attributes` (a fragment, not a standalone file) |
| `ocsf-schema.patch` | the same three changes as one `git apply`-able unified diff against `main` |
| `example-event.json` | worked example: an API Activity (6003) event with the `ai_operation` profile and a populated `ai_tool` |

To try it against a real checkout: `git -C <ocsf-schema> apply ocsf-schema.patch`.

## Decision log — where this draft departs from proposal.md v1

Each departure exists because the v1 shape either collided with OCSF
metaschema rules or contradicted the current MCP spec. The proposal text
(`proposal.md`) has been revised to match; the v1 → v2 doc diff is the
second commit on this branch.

1. **No anonymous inline objects.** OCSF requires every attribute to be
   registered in `dictionary.json` and every object-typed attribute to
   reference a defined object. The v1 `server: {uid, name, transport}`,
   `input_schema: {uid}`, `output_schema: {uid}`, and `annotations: {…}`
   shapes cannot exist as written. Resolutions below.
2. **`server` → existing `service` object + `transport_id` on `ai_tool`.**
   The `service` object already carries `uid`/`name`/`version`/`labels`/`tags`.
   Transport is modeled as a normalized enum (`transport_id`: stdio,
   Streamable HTTP, legacy HTTP+SSE, Other) on `ai_tool` itself. Supporting
   precedent: the `ai_agent.type_id` description already promises that
   communication protocols (MCP, A2A) "are surfaced on the relevant
   operation" — this is that slot.
3. **`input_schema`/`output_schema` → the existing `fingerprint` object**
   (`input_schema_fingerprint` / `output_schema_fingerprint`). `fingerprint`
   carries `algorithm_id`, `encoding_id`, and `serialization_id` — including
   `JCS` for canonical JSON — so a schema fingerprint becomes reproducible
   and verifiable rather than an opaque string. This strengthens the
   drift/rug-pull detection story.
4. **`annotations` → flat `is_*` booleans** (`is_readonly` — already in the
   dictionary — plus new `is_destructive`, `is_idempotent`, `is_open_world`),
   matching the OCSF idiom for declared flags. Every description states the
   hints are **self-declared and unverified**; the profile guidance warns
   against deriving `activity_id` from a hint the observed behavior
   contradicts (a malicious server could otherwise label destructive calls
   as `Read`).
5. **`uid` is the capability's stable identity, not the call ID.** v1
   defined `uid` as the invocation identifier, contradicting its own claim
   that the object is the *invariant* description of the capability (and
   OCSF `_entity` semantics). The per-call correlation ID moved to the
   existing `transaction_uid` dictionary attribute.
6. **`cache_scope` enum corrected to the actual RC.** MCP SEP-2549 defines
   `cacheScope` as `public` | `private` (modeled on HTTP Cache-Control), not
   the v1 `per_user`/`shared`. The enum now mirrors the spec. Placement
   caveat: in the RC these fields ride on *responses*, so they are declared
   caching metadata, not invariant capability properties — flagged as an
   open question.
7. **`data_type` → existing `mime_type`;** `uri`, `namespace`, and `version`
   also reuse existing dictionary entries unchanged.
8. **v1 open question 1 (source axis) resolved as "include now":**
   `source_id` (MCP / Function / Built-in) reuses the existing generic
   `source_id` dictionary attribute with an object-local enum. Without it, a
   protocol-neutral object can't distinguish the bindings the proposal
   itself describes.

## Open questions for the working group

- **Name.** `ai_tool` parallels `ai_agent`/`ai_model` and matches industry
  usage, but an `ai_tool` of `type_id: Resource` reads oddly; `ai_capability`
  is the obvious alternative. (v1's collision-avoidance argument vs.
  `product` still holds either way.)
- **Cache fields placement.** Keep `cache_scope_id`/`cache_ttl` here as
  observed-declaration metadata, or move them toward `api.response`?
- **Overlap with `message_context.service`.** That attribute is described as
  "the server or service handling the request" for AI systems. This draft
  scopes `ai_tool.service` to the *logical serving system of the capability*
  (vs. `dst_endpoint` = the gateway actually contacted); the profile docs
  should say which one producers populate when both apply.
- **Requirement levels.** `name` required and `service`/`source_id`/`type_id`/
  `uid` recommended is a starting point, not a position.
