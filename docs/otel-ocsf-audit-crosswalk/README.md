# OTel Audit ↔ OCSF `record_integrity` Crosswalk

**Status:** draft for review — written for the OpenTelemetry Audit Logging
initiative ([open-telemetry/community#2409](https://github.com/open-telemetry/community/pull/2409)),
offered for the spec repo if the group wants it there.

**Pinned inputs** (a crosswalk against moving targets is worthless — these are
the exact revisions mapped):

| Side | Source | Revision |
|---|---|---|
| OTel | [`specification/audit/data-model.md`](https://github.com/apeirora/opentelemetry-specification/blob/auditing/specification/audit/data-model.md), `apeirora/opentelemetry-specification` branch `auditing` | `663d809` (includes `578b930`) |
| OCSF | `attestation` object + `record_integrity` profile ([ocsf/ocsf-schema#1661](https://github.com/ocsf/ocsf-schema/pull/1661)), API Activity 6003 + `ai_operation` | OCSF **1.9.0** (released 2026-08-03) |
| Fixture | [Production reference bundle](../cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle/) — 236-event hash-chained export, per-event ECDSA-P256 signatures verifiable against a [public JWKS](https://api.ai-identity.co/.well-known/ai-identity-public-keys.json) | bundle of 2026-08-06 |

**Why this exists:** both specs define tamper-evident audit records — hash
chain, per-record signature, stream identity. If the field mapping between
them is explicit and lossless, one producer can emit both shapes, and an
OTel-Collector-side translation (the
[opentelemetry-collector-contrib#47461](https://github.com/open-telemetry/opentelemetry-collector-contrib/pull/47461)
OCSF-connector idea) becomes a mechanical transform instead of a design
exercise. If it isn't written down, the two ecosystems grow divergent
integrity constructs and every producer that needs both pays the design tax
privately. This document is the mapping, the honest list of places it is
**not** 1:1 with what a transform must do there, and derived test vectors
that prove the integrity constructs survive the round trip.

Everything here is checked against running code, not read off the two specs:
`derive_otel_vectors.py` applies the mapping to the production OCSF export
and re-verifies chain linkage across the transform (235/235 links on the
full export).

---

## 1. The mapping

Requirement levels are quoted from each side (`MUST`/`SHOULD`/`MAY` from the
OTel data model; `required`/`recommended`/`optional` from the OCSF schema).

### 1.1 Envelope

| OTel (`AuditRecord` on `LogRecord`) | Req | OCSF (API Activity 6003) | Req | Notes |
|---|---|---|---|---|
| `Timestamp` | MUST | `time` | required | OTel ns vs OCSF ms — precision loss OTel→OCSF (§2.8) |
| `ObservedTimestamp` | MUST | `metadata.logged_time` | optional | OCSF→OTel: when absent, set `= Timestamp` (the constraint floor) |
| `EventName` | MUST | `class_uid` + `activity_id` (`type_uid`) | required | open string vs closed enum (§2.8) |
| `Body` | MAY | `message` | recommended | |
| `Resource` (`service.*`) | MUST | `metadata.product` | required | |
| `TraceId` / `SpanId` | MAY | `metadata.correlation_uid` | optional | loose: correlation, not trace identity |
| `audit.record.id` | MUST | `metadata.uid` | optional | the stable per-record identifier; also the chain join key (§2.2) — a requirement-level mismatch worth noting: MUST vs optional |
| `audit.actor.id` / `audit.actor.type` | MUST | `actor.user.uid` / `actor.user.type_id` | `actor` required; `user` recommended | OCSF splits human vs agent actor (§2.5) |
| — | | `ai_agent.uid` / `ai_agent.name` (`ai_operation` profile) | optional | no `audit.*` home; carry as `gen_ai.agent.id` / `gen_ai.agent.name` (§2.5) |
| `audit.action` | MUST | `activity_id` (verb axis) | required | `CREATE`/`READ`/`UPDATE`/`DELETE` ↔ 1/2/3/4 |
| `audit.outcome` | MUST | `action_id` (`security_control` profile; + `status_id`) | recommended | **decision ≠ outcome** — see §2.6 |
| `audit.target.id` / `audit.target.type` | SHOULD | `api.operation` (+ `http_request.url.path`) | `api` required | the data model's own `http.endpoint` example |
| `audit.source.id` / `audit.source.type` | MAY | `src_endpoint.ip` / type | required | not exercised in the fixture |
| `audit.schema.version` | SHOULD | `metadata.version` | required | derived vectors carry `ocsf/1.9.0` to say *which* schema versioned the payload |

### 1.2 Integrity constructs (the core)

| OTel | Req | OCSF (`attestation` via `record_integrity`) | Req | Notes |
|---|---|---|---|---|
| `audit.sequence.stream_id` | MAY | `attestation.chain_uid` | recommended | **clean 1:1.** Same semantics: opaque id scoping one chain; demultiplexing key |
| `audit.sequence.number` | MAY | *(none — `unmapped.org_chain_seq` in the fixture)* | — | #1661 dropped the draft-era counter; see §2.4 |
| `audit.sequence.prev_hash` | MAY | `attestation.prev_event.fingerprint.value` | `prev_event` recommended; `fingerprint` within it optional | hash-only vs id+hash pointer; see §2.2, genesis in §2.3 |
| — | | `attestation.prev_event.uid` (+ `type_uid`) | **required** within `prev_event` | the resolvable half of the chain pointer; no OTel home (§2.2) |
| `audit.integrity.value` | MAY | `attestation.signatures[]` *describes* it; bytes have no OCSF field (ocsf-schema#1709) — fixture: `unmapped.signature_b64` | at_least_one | §2.1 governs what the proof is *over* |
| `audit.integrity.signer` (`producer` \| `collector`) | MAY | `attestation.authority_uid` | recommended | tier-role vs named authority; see §2.5b |
| *(multi-valued `.0`/`.1` pairs)* | MAY | `attestation_list[]` — one entry per attester | — | OCSF's array is the cleaner multi-attester shape |
| `audit.integrity.algorithm` (Resource, JWA) | MUST if value set | `signatures[].algorithm_id`/`algorithm` (per signature) | required | placement + naming differ; see §2.7 |
| `audit.integrity.certificate` (Resource) | MAY | *(no field — fixture: `unmapped.signature_key_id` = JWKS `kid`)* | — | OTel's Key-ID form fits exactly; OCSF gap is #1709 again |
| *(JCS is mandated, not declared)* | MUST | `fingerprint.serialization_id`/`serialization` | required | **the deepest divergence** — §2.1 |
| `AuditReceipt` (`RecordId`, `IntegrityHash`, `SinkTimestamp`) | MUST (API) | *(no counterpart)* | — | receipt is an emit-API artifact, not a record field; out of scope for a record-level transform |

---

## 2. Where the mapping is not 1:1 — and what a transform must do

In roughly descending order of how much they matter.

### 2.1 Canonicalization: mandated (JCS) vs declared (`fingerprint.serialization`)

OTel: the integrity proof is computed over the RFC 8785 (JCS) canonical form
of the record (minus `audit.integrity.*`), and implementations "MUST NOT use
any other serialization or canonicalization method." OCSF: the fingerprint
*declares* its serialization (`serialization_id` + free-text `serialization`
sibling), precisely so producers whose scheme isn't JCS can say so honestly.

Consequence for any transform, in either direction: **a signature is bound to
the canonical bytes of its origin shape and cannot be re-derived after
translation without the signing key.** Translating the record does not —
cannot — re-sign it. So a transform MUST carry the origin-side digest and its
declared canonicalization along with the signature, or the proof degrades to
noise. The derived vectors do this with three attributes:
`ocsf.attestation.entry_hash`, `ocsf.attestation.entry_hash.algorithm`,
`ocsf.attestation.canonicalization`. Verification recipe in §3.

Note what this means for strict conformance: a producer whose proof is over a
non-JCS canonicalization (this fixture's is a declared producer scheme) can
be *represented* in the OTel shape but not *conformant* to the MUST as
written. A small spec ask that would fix it is in §4.

### 2.2 The chain pointer: hash-only vs id + hash

OTel `audit.sequence.prev_hash` is a bare hash. OCSF `prev_event` carries
`uid` + `type_uid` + `fingerprint` — a *resolvable* reference plus the hash
binding it to content. The requirement levels are the tell: within
`prev_event`, `uid` is **required** and `fingerprint` is optional — OCSF made
the locator the mandatory half, the exact inverse of OTel's hash-only
pointer. A predecessor hash proves linkage but cannot locate
the predecessor across storage, sharding, or retention boundaries (raised as
#2409 review point; the id half is what makes a broken-chain investigation
actionable). OCSF→OTel is lossy here: the transform parks the id in
`ocsf.attestation.prev_event.uid`. OTel→OCSF must synthesize `prev_event.uid`
from the predecessor's `audit.record.id` — which works, because
`audit.record.id` is MUST-level. §4 has the one-attribute spec ask.

### 2.3 Genesis: SHA-256 of empty string vs omission

OTel: the first record of a stream "SHOULD set `audit.sequence.prev_hash` to
the SHA-256 hash of the empty string" (`e3b0c442…`). OCSF fixture behavior:
genesis **omits `prev_event` entirely** — there is no predecessor to point
at. The empty-string constant is schema-safe (unlike a `"GENESIS"` string
sentinel, which we shipped once and documented as an anti-pattern), but it is
indistinguishable from a genuine hash of empty content and it makes "has a
predecessor" a value comparison instead of a presence check. Transform rule
adopted by the vectors: genesis omits `audit.sequence.prev_hash`; a receiver
should treat the OTel constant and omission as equivalent genesis markers.
§4 asks to align on omission.

### 2.4 Sequence number: OTel has one, final-#1661 OCSF does not

`audit.sequence.number` (monotonic, gap = lost/deleted record, alert) has no
home in the merged attestation object — the draft-era `sequence` field was
dropped before merge. This fixture's producer keeps a per-chain counter in
`unmapped.org_chain_seq`, so OCSF→OTel maps cleanly *for this producer* but
not for OCSF producers in general: a generic transform MUST tolerate absent
sequence numbers and fall back to linkage-only continuity (deletion is still
detectable — the chain breaks — but "how many records are missing" is not).
This is a real capability OTel has that merged OCSF lacks; worth stating
plainly in both venues rather than papering over.

### 2.5 Actor: one slot vs human + agent split

OTel has a single mandatory `audit.actor.id`/`type` (guidance: use `user`
"even if performed by an AI agent on behalf of a user"). OCSF 6003 with
`ai_operation` carries both `actor.user` (the human/principal) **and**
`ai_agent` (the acting agent, merged via ocsf-schema#1641). For agentic
workloads that split is load-bearing — "which human authorized" and "which
agent acted" are different investigations. Transform rule: `audit.actor.*` ←
`actor.user`; the agent rides OTel's existing GenAI semconv
(`gen_ai.agent.id`, `gen_ai.agent.name`) rather than a private namespace, so
OTel tooling that already understands GenAI attributes gets the agent for
free.

### 2.5b Signer: tier role vs named authority

`audit.integrity.signer` is a closed tier enum — `producer` | `collector` —
answering *where in the pipeline* the proof was made. `attestation.authority_uid`
names *who* attested. These compose rather than conflict: role and identity.
OCSF→OTel: signer = `producer` when the attesting authority is the emitting
service (this fixture), `collector` for a custody-tier attestation — but that
classification requires out-of-band knowledge of which authority is which.
OTel→OCSF: `authority_uid` should carry a stable identity (service identity
or signing-key reference; `audit.integrity.certificate` is the natural
source), not the literal string "producer" — a tier is not an identity. §4
proposes the missing attribute.

### 2.6 Outcome vs decision

`audit.outcome` (`success`/`failure`) records whether the action completed.
OCSF `action_id` (`Allowed`/`Denied`) records the **policy decision** — a
denied call is a *successfully denied* operation, and OCSF separately has
`status_id` for operational success. For an enforcement-point producer the
decision is the primary fact. Transform rule: `Allowed` → `success`,
`Denied` → `failure` (from the caller's perspective the action did not
complete), and the decision is preserved verbatim as `ocsf.action` /
`ocsf.action_id` so the distinction is never laundered away. Receivers doing
policy analytics should query the latter, not `audit.outcome`.

### 2.7 Algorithm: placement and naming

Placement: OTel pins `audit.integrity.algorithm` + `certificate` at
**Resource** scope — once per service instance, "identical for every
AuditRecord emitted." OCSF carries `algorithm` per signature. Resource scope
is the right economy for the common case but cannot represent a batch whose
records were signed by different keys (mid-batch key rotation, multi-tenant
exporters). A transform MUST verify the single-key invariant before claiming
Resource-level attributes — `derive_otel_vectors.py` hard-fails if the
export contains more than one key or algorithm rather than silently
misrepresenting it.

Naming: OTel wants JWA identifiers (`ES256`); OCSF uses an enum + string
(`algorithm_id: 3`, `"ECDSA-P256-SHA256"`). Small, mechanical, but a
transform needs the table (`ES256` ↔ `ECDSA-P256-SHA256`, `EdDSA` ↔
`Ed25519`, …) — it's in the script.

### 2.8 Smaller frictions, recorded so nobody rediscovers them

- **Timestamp precision:** OTel ns, OCSF ms. OCSF→OTel is exact (×10⁶);
  OTel→OCSF truncates. Only matters if the timestamp is inside the signed
  canonical form — which is another reason §2.1's declared-canonicalization
  discipline matters.
- **`EventName` (open, MUST NOT be empty) vs `type_uid` (closed enum):**
  the vectors derive `api.activity.create|read|update|delete`; the reverse
  direction needs an EventName→class registry and will be lossy for names
  outside it.
- **`SeverityNumber`:** OTel says SHOULD NOT set; OCSF `severity_id` is
  required. Transform drops it OCSF→OTel (the fixture's severity encodes the
  decision, already preserved); OTel→OCSF must synthesize (`Informational`).

---

## 3. Test vectors

| File | What |
|---|---|
| [`otel-audit-records.sample.ndjson`](otel-audit-records.sample.ndjson) | 7 OTel `AuditRecord`s derived from the bundle's annotated excerpt (one agent's lifecycle, chain seq 16–22) |
| [`derive_otel_vectors.py`](derive_otel_vectors.py) | stdlib-only derivation + post-transform chain verification; `--full` runs the 236-event production export |
| OCSF side | the [reference bundle](../cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle/) — same records, origin shape, with its own verifier (`regenerate.py`) |

Because both shapes are derived from the same production records, they chain
against **each other**: record N+1's `audit.sequence.prev_hash` (OTel shape)
equals record N's `attestation.fingerprint.value` (OCSF shape). Current run:
7/7 excerpt records, 6/6 internal links; full export 236 records, 235/235
links, 1 genesis (prev omitted).

**What verifies without any secret:**

1. *Chain linkage, both shapes, and across shapes* — structural hash
   comparison, no keys (`derive_otel_vectors.py` does it for the OTel shape).
2. *Every ECDSA signature* — `audit.integrity.value` is a DER ECDSA-P256
   signature over `bytes.fromhex(ocsf.attestation.entry_hash)`; the public
   key is in the [JWKS](https://api.ai-identity.co/.well-known/ai-identity-public-keys.json)
   under `kid = audit.integrity.certificate`. Note that per §2.1 the
   signature is bound to the origin (OCSF) fingerprint carried in the
   record — not to JCS of the OTel form. That is the honest state of a
   translated proof, and exactly why §2.1/§4 matter.

**What requires the org key:** recomputing `entry_hash` itself from record
content (the chain hash is keyed HMAC — key-holder verifiable, declared as
such in `ocsf.attestation.entry_hash.algorithm`).

### Worked example — one record, both shapes

The allowed inference call (chain seq 18; the same event annotated in the
[bundle README](../cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle/README.md#anatomy-of-one-event-the-allowed-inference)).
OTel shape, as derived (long values truncated here; the ndjson carries full
values):

```json
{
  "Resource": {
    "service.name": "ai-identity-gateway",
    "audit.integrity.algorithm": "ES256",
    "audit.integrity.certificate": "projects/…/cryptoKeys/session-attestation/cryptoKeyVersions/1"
  },
  "Timestamp": 1776094414825000000,
  "ObservedTimestamp": 1776094414825000000,
  "EventName": "api.activity.create",
  "Body": null,
  "Attributes": {
    "audit.record.id": "99",
    "audit.actor.id": "a33fb1e9-adac-4052-bdd6-e6d96292bbce",
    "audit.actor.type": "user",
    "audit.action": "CREATE",
    "audit.outcome": "success",
    "audit.target.id": "/v1/chat/completions",
    "audit.target.type": "http.endpoint",
    "audit.schema.version": "ocsf/1.9.0",
    "audit.sequence.stream_id": "f3576cf6-87ff-4c07-b446-e6ac526236a5",
    "audit.sequence.number": 18,
    "audit.sequence.prev_hash": "90ba42f3b92586ff…",
    "audit.integrity.value": "MEUCIQC7SNQRH0a8IEKO…",
    "audit.integrity.signer": "producer",
    "ocsf.attestation.entry_hash": "1d9548729d942e30…",
    "ocsf.attestation.entry_hash.algorithm": "HMAC-SHA-256",
    "ocsf.attestation.canonicalization": "AI-Identity audit chain v1 (sorted-compact JSON + prev hash)",
    "ocsf.attestation.prev_event.uid": "98",
    "gen_ai.agent.id": "32928870-56a1-4518-be76-7e99bfcdeac4",
    "gen_ai.agent.name": "QA-eae97318",
    "http.request.method": "POST",
    "url.path": "/v1/chat/completions",
    "ocsf.class_uid": 6003,
    "ocsf.type_uid": 600301,
    "ocsf.action": "Allowed",
    "ocsf.action_id": 1,
    "ocsf.duration_ms": 182,
    "ocsf.policy_version": 10
  }
}
```

Read it against the OCSF anatomy and every §2 rule is visible in data:
`stream_id` = `chain_uid`, `prev_hash` = seq 17's fingerprint value, the
signature carried with its origin digest and declared canonicalization, the
human in `audit.actor.*` and the agent in `gen_ai.agent.*`, the Allowed
decision surviving next to the derived outcome.

---

## 4. What would make the mapping lossless — four small spec asks

Each of these is one attribute or one sentence, not a redesign. OTel-side
asks are for the audit data model; the OCSF ask is already filed.

1. **`audit.integrity.canonicalization` (OTel, closes §2.1).** An optional
   companion to `audit.integrity.value` naming the canonicalization the
   proof is over — `jcs` (default, keeps today's MUST as the default path),
   or a declared producer scheme. Mirrors OCSF's `fingerprint.serialization`
   enum + sibling. Without it, "verify the signature" quietly becomes "trust
   the producer" for every record that crossed a schema boundary.
2. **`audit.sequence.prev_record_id` (OTel, closes §2.2).** The resolvable
   half of the chain pointer, `= audit.record.id` of the predecessor.
   `prev_hash` binds content; the id locates it across storage, sharding,
   and retention boundaries. OCSF's merged shape requires both halves for
   the same reason.
3. **Genesis by omission (OTel, closes §2.3).** Change the SHA-256("")
   SHOULD to: the first record of a stream omits `audit.sequence.prev_hash`.
   Presence check beats value comparison, and no verifier has to special-case
   a magic constant.
4. **Signature bytes + key reference (OCSF, closes the `unmapped` riders).**
   Already filed as [ocsf-schema#1709](https://github.com/ocsf/ocsf-schema/issues/1709):
   `digital_signature` describes a signature but cannot carry its bytes or
   key id. When it lands, `audit.integrity.value` ↔ signature bytes and
   `audit.integrity.certificate` ↔ key reference become clean 1:1 rows in
   §1.2.

With 1–3 in the OTel model and 4 in OCSF, every row in §1.2 is bidirectional
without an `ocsf.*` / `unmapped` escape hatch, and a signed record survives
OCSF → OTel → OCSF byte-identical in its integrity constructs.

---

*Maintained in the AI Identity repo; regenerate the vectors with
`python3 derive_otel_vectors.py` after any bundle refresh. Questions /
corrections: the #2409 thread, or issues here.*
