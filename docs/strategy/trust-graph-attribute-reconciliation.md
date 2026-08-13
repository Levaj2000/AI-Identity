# Trust Graph Span Attributes — Reconciling Four Namespaces

**Status:** proposal for CoSAI WS4 review — companion to the
[OTel↔OCSF audit crosswalk](../otel-ocsf-audit-crosswalk/README.md) and the
[WS4 interop map](./cosai-ws4-interop-map.md). Offered for a CoSAI- or
OCSF-owned home if the group wants it there.

**Pinned inputs** (naming proposals against moving targets are worthless —
these are the exact revisions compared):

| Side | Source | Revision |
|---|---|---|
| POC | [`husky-parul/agents-identity`](https://github.com/husky-parul/agents-identity), `k8s/otel-tracing.yaml` → `set_auth_attributes` | `3b275fb` |
| OTel audit | [`specification/audit/data-model.md`](https://github.com/apeirora/opentelemetry-specification/blob/auditing/specification/audit/data-model.md), `apeirora/opentelemetry-specification` branch `auditing` ([community#2409](https://github.com/open-telemetry/community/pull/2409)) | `663d809` |
| OTel GenAI | `gen_ai.*` registry, [`open-telemetry/semantic-conventions-genai`](https://github.com/open-telemetry/semantic-conventions-genai) (`docs/registry`) | main as of 2026-08-13 — `gen_ai.agent.*` at **Development** stability |
| OCSF | API Activity 6003 + `ai_operation` + `record_integrity` | OCSF **1.9.0** (released 2026-08-03) |
| Token exchange | [RFC 8693](https://www.rfc-editor.org/rfc/rfc8693) (`sub`, `act`, nested `act`) | — |

**Why this exists.** The 2026-08-13 WS4 sync demonstrated a working
cross-runtime delegation trace: a user authenticates via OIDC, an orchestrator
performs dynamic agent discovery, and a downstream weather agent receives a
span carrying the originating principal, the acting agent, and a delegation
depth. That closed the open question — OpenTelemetry *can* carry Trust Graph
data across agent runtimes — and produced an action item to decide which
attributes to standardize.

The problem this document addresses is that **the same two facts already have
four names in flight**, in specs that WS4 participants are separately
contributing to. If the Trust Graph adopts a fifth, or adopts one of the four
without noticing the other three, every producer that needs to emit for more
than one consumer pays a translation tax privately. This is the same failure
mode the crosswalk was written to prevent at the record layer, one layer up.

Nothing here is a criticism of the POC's naming. The POC's job was to prove
propagation, and it did; naming was explicitly deferred to this discussion.

---

## 1. The four namespaces

The two facts every Trust Graph consumer needs are **which principal
authorized this** and **which agent acted**. Current state:

| Source | Principal | Acting agent | Requirement level |
|---|---|---|---|
| POC (`otel-tracing.yaml`) | `auth.subject` (+ `auth.username`) | `auth.actor` | POC-local |
| OTel audit data model | `audit.actor.id` / `audit.actor.type` — **one slot** | *(none)* | `MUST` |
| OTel GenAI semconv | *(none)* | `gen_ai.agent.id` / `gen_ai.agent.name` | Development stability |
| OCSF 6003 + `ai_operation` | `actor.user.uid` / `actor.user.type_id` | `ai_agent.uid` / `ai_agent.name` | `actor` required; `user` recommended; `ai_agent` optional |

Two structural observations fall out of the table.

**The OTel audit model has one actor slot, and its guidance says to use it for
the human** — "even if performed by an AI agent on behalf of a user." OCSF
splits the two. Crosswalk §2.5 argues the split is load-bearing for agentic
workloads, because *"which human authorized"* and *"which agent acted"* are
different investigations. A Trust Graph that collapses them cannot answer the
second one.

**Only the POC has a name for delegation depth.** See §3.

## 2. Proposed reconciliation

The rule this follows: **do not mint a private namespace for a fact that an
existing convention already names.** Private namespaces are cheap to emit and
expensive to consume — every downstream tool needs a mapping table, and the
tools that already understand `gen_ai.*` get nothing.

| Fact | Emit as | Maps to OCSF | Notes |
|---|---|---|---|
| Originating principal | `audit.actor.id` + `audit.actor.type` | `actor.user.uid` / `type_id` | `MUST`-level on the OTel side; the strongest anchor available |
| Acting agent | `gen_ai.agent.id` + `gen_ai.agent.name` | `ai_agent.uid` / `ai_agent.name` | crosswalk §2.5's existing transform rule; OTel tooling that understands GenAI attributes gets the agent for free |
| Delegation depth | *derive, do not transmit* — see §3 | — | no home in any of the four |
| Principal display name | **do not standardize** — see §5 | `actor.user.name` if needed at the record layer | PII-adjacent, and derivable from the principal id by anyone entitled to resolve it |

One citation note, verified 2026-08-13: the GenAI attribute registry now lives
in [`open-telemetry/semantic-conventions-genai`](https://github.com/open-telemetry/semantic-conventions-genai);
the `gen_ai.agent.*` entries still visible in the main `semantic-conventions`
repo are marked deprecated *because they moved*, not because they were retired.
Cite the new home — a reader checking the old registry will see "deprecated"
and draw the wrong conclusion. Both attributes sit at **Development** stability
there, which cuts two ways: the names are not yet frozen (a pinning risk), and
the names are not yet frozen (this group can still propose what the delegation
story needs before they are).

This is deliberately additive rather than novel: it asks the group to adopt two
names that already exist and carry requirement levels, rather than ratify three
that exist only in a POC. It also means a producer emitting for the Trust Graph
is simultaneously emitting a record that the crosswalk can carry into OCSF
without an escape hatch — which is the property that makes cross-boundary
delegation evidence composable at all.

## 3. `delegation_depth` — the one genuinely new attribute

The POC derives depth by walking the nested RFC 8693 `act` chain:

```python
act = claims.get("act")
if isinstance(act, dict):
    span.set_attribute("auth.actor", act.get("sub", ""))
    depth = 0; node = act
    while isinstance(node, dict):
        depth += 1; node = node.get("act")
    span.set_attribute("auth.delegation_depth", depth)
```

Two consequences worth putting in front of the group before this becomes a
standardization ask.

**It is derived, not observed.** Any party holding the token can recompute it
by walking `act`. Standardizing a transmitted copy creates a value that can
disagree with the token it was derived from, and a verifier then has to decide
which one is authoritative. Recommendation: specify depth as *derivable from
the `act` chain* and leave it out of the emitted attribute set, or — if
consumers genuinely need it without token access — specify it as a hint with
the token's chain as the normative source.

**Monotonic counters have a poor track record in these specs.** Crosswalk §2.4
records that OCSF [#1661](https://github.com/ocsf/ocsf-schema/pull/1661)
dropped its draft-era sequence counter in review — OTel's
`audit.sequence.number` (MAY) consequently maps to nothing on the OCSF side,
and the AI Identity fixture carries its org counter as
`unmapped.org_chain_seq`. A per-hop integer that every
independent implementation must agree to increment identically is the same
shape of proposal. Going in expecting resistance, with the derived-value
framing ready, is a better position than discovering it in review.

## 4. Canonicalization — a landmine in the content-ID design

The sync also proposed separating the integrity layer from the data layer: the
Trust Graph stores hashes or content IDs, actual payloads live with the
entities that own them under their own access control, and the hash guarantees
that the data you fetch is the data that was signed. That design is right, and
it is the same separation `record_integrity` was built for.

It has one prerequisite the discussion did not reach: **content addressing only
works if all parties hash the same logical event to the same digest.** That is
crosswalk §2.1, already diagnosed:

> OTel: the integrity proof is computed over the RFC 8785 (JCS) canonical form
> of the record (minus `audit.integrity.*`), and implementations "MUST NOT use
> any other serialization or canonicalization method." OCSF: the fingerprint
> *declares* its serialization (`serialization_id` + free-text `serialization`
> sibling), precisely so producers whose scheme isn't JCS can say so honestly.

And the consequence the crosswalk draws:

> a signature is bound to the canonical bytes of its origin shape and cannot be
> re-derived after translation without the signing key.

So: two conformant implementations that pick different canonicalizations
produce different content IDs for the same event, and the integrity claim
degrades from "verify the signature" to "trust the producer" — silently, with
no error surfaced anywhere. This is not hypothetical for us; AI Identity's own
audit chain uses a declared producer scheme rather than JCS, and
`common/ocsf/api_activity.py` says so in the schema rather than overstating:

```python
_HMAC_FINGERPRINT = {
    "algorithm_id": 99,          # Other — claiming plain SHA-256 (id 3) would misstate
    "algorithm": "HMAC-SHA-256",
    "serialization_id": 99,
    "serialization": "AI-Identity audit chain v1 (sorted-compact JSON + prev hash)",
}
```

**Ask for the group:** pin canonicalization in the Trust Graph schema, and
require that a content ID travel with its declared serialization. Crosswalk §4
already drafts the OTel-side fix as a one-attribute spec ask
(`audit.integrity.canonicalization`, defaulting to `jcs` so today's `MUST`
stays the default path). This is worth settling before an SDK is selected for
the hashing and bundling work, because the SDK's canonicalization becomes the
reference implementation's canonicalization by default.

## 5. What should not go in a span

The POC emits `weather.location: Boston` alongside the identity attributes,
which surfaced the privacy and confidentiality concern raised on the call. The
POC included it to make the demo legible and flagged it as illustrative, so
this is a note about the standardized set, not about the POC.

Two attribute-hygiene rules worth writing into the schema rather than leaving
to each producer:

**Request content does not belong in the Trust Graph, only its digest.** This
is §4's separation, stated as an attribute rule. Once payload content is in a
span it is in every backend that span reaches, under that backend's retention
and access model rather than the data owner's.

**Identity attributes should carry identifiers, not display names.** The POC
emits `auth.username` from the OIDC `preferred_username` claim. A login handle
is personal data, it is derivable from the principal identifier by anyone
entitled to resolve it, and it buys only human readability in a UI. AI
Identity's audit path takes the stricter version of this stance — an
allowlist-only sanitizer applied *before* write, `common/audit/sanitizer.py`:

```
- ALLOWLIST-ONLY: only recognized metadata keys pass through.
- PII-BLOCKED: known PII field names are explicitly rejected + logged.
- BODY-BLOCKED: request/response body content is NEVER stored.
- FAIL-SAFE: unknown keys are silently dropped, never stored.
```

An allowlist is offered as a starting shape for the tiered-Trust-Graph
discussion: a tier is then a named allowlist rather than a policy argued case
by case. AI Identity's compliance export profiles (SOC 2 Type II, EU AI Act,
NIST AI RMF) are the same pattern applied at the record layer, if a worked
example is useful.

## 6. What traces cannot carry

Recorded here because it bounds what the standardized attribute set can be
asked to do, not to relitigate the POC's design.

The POC's `parse_jwt_claims` base64-decodes the token payload without verifying
its signature — correctly, because the authorization proxy validated the token
upstream before the agent ever ran. The consequence for a Trust Graph built
from span attributes is that **the attributes are the emitting agent's own
assertion about its auth context.** A compromised or simply buggy agent emits
whatever principal it likes and the resulting trace is indistinguishable from
an honest one.

Combined with two properties of spans in general — they are sampled, and they
are retention-limited — this bounds traces to *correlation*: showing which
runtimes participated and in what order. The POC's own playbook reaches the
same conclusion, that traces are "necessary but not sufficient for full audit"
and a stronger guarantee "requires signed evidence."

That is the seam between this document and the crosswalk. Correlation is
OpenTelemetry's lane; integrity-protected evidence is OCSF's, and
`record_integrity` shipped for it in 1.9.0. The attribute set proposed in §2 is
worth standardizing because it makes the correlation lane *interoperable*, not
because it makes it *evidentiary*.

## 7. Code-state disclosure

So this document is not read as describing shipped behavior: **AI Identity does
not currently emit OpenTelemetry spans.** There is no `opentelemetry-*`
dependency in the codebase; request correlation is a flat per-request
correlation ID (`common/audit/correlation.py`), surfaced as OCSF
`metadata.correlation_uid`. A span-tree design exists at
`docs/specs/multi-step-agent-traces.md` and is unimplemented.

The positions above therefore rest on the crosswalk's executable test vectors
and on the OCSF export path (`common/ocsf/api_activity.py`), not on a running
tracing implementation. The POC is currently the only working demonstration of
cross-runtime propagation in this group, and any attribute set the group agrees
should be validated against it rather than against this document.

---

*The OTel-side requirement levels and the GenAI registry location were
re-verified against the live sources on 2026-08-13. Corrections still welcome,
particularly on anything mischaracterized about the POC — please correct your
own rows, per the interop map's convention.*
