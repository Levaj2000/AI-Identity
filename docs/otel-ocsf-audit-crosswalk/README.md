# OTel Audit ↔ OCSF `record_integrity` Crosswalk

**Status:** draft for review — written for the OpenTelemetry Audit Logging
initiative ([open-telemetry/community#2409](https://github.com/open-telemetry/community/pull/2409)),
offered for the spec repo if the group wants it there.

**Pinned inputs** (a crosswalk against moving targets is worthless — these are
the exact revisions mapped):

| Side | Source | Revision |
|---|---|---|
| OTel | [`specification/audit/data-model.md`](https://github.com/apeirora/opentelemetry-specification/blob/3c5a0ff6f952846a634b9729117d853b6bad2d3a/specification/audit/data-model.md), `apeirora/opentelemetry-specification` branch `auditing` | `3c5a0ff` (rebased draft; supersedes the `25bff70e` pin) |
| OCSF | `attestation` object + `record_integrity` profile ([ocsf/ocsf-schema#1661](https://github.com/ocsf/ocsf-schema/pull/1661)), API Activity 6003 + `ai_operation` | OCSF **1.9.0** (released 2026-08-03) |
| Fixture | [Production reference bundle](../cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle/) — 236-event hash-chained export, per-event ECDSA-P256 signatures verifiable against a [public JWKS](https://api.ai-identity.co/.well-known/ai-identity-public-keys.json) | bundle of 2026-08-06 |

The OTel column describes a pinned branch draft, not an accepted OTel release.
The fixture and OCSF column use **1.9.0**; later OCSF changes are noted
separately and have not been applied to these records.

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
that check chain linkage across the OCSF-to-OTel transform.

The fixture mapping is checked against running code, not just read off the
two specs: `derive_otel_vectors.py` applies it to the production OCSF export
and re-verifies chain linkage across the transform (235/235 links on the
full export). Draft-only OTel features discussed below are not implemented
by that fixture.

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
| `audit.sequence.previous_hash` | MAY | `attestation.prev_event.fingerprint.value` | `prev_event` recommended; `fingerprint` within it optional | both halves map, both directions; but the carried value is the OCSF-origin entry hash (keyed HMAC-SHA-256, serialization_id 99, not JCS), not the draft's `IntegrityHash`: representable, not conformant. Linkage verifies against the `ocsf.attestation.entry_hash` rider, never a recomputed OTel hash; section 2.2 has the semantics and the conforming path |
| `audit.sequence.previous_record_id` | MAY | `attestation.prev_event.uid` (+ `type_uid`) | **required** within `prev_event` | **clean 1:1.** the resolvable locator half of the chain pointer |
| `audit.sequence.end` | MAY | *(none — transform parks in `unmapped.audit_sequence_end`)* | — | OTel-only end signal; see §2.9 |
| `audit.integrity.value` | MAY | `attestation.signatures[]` describes it; 1.9.0 fixture: `unmapped.signature_b64` | at_least_one | Post-1.9.0 `digital_signature.value` carries bytes (#1709); neither field makes an origin-shape signature valid over the translated shape (see section 2.1) |
| `audit.integrity.signer` (`producer` \| `collector`) | MAY | `attestation.authority_uid` | recommended | tier-role vs named authority; see §2.5b |
| *(multi-valued `.0`/`.1` pairs)* | MAY | `attestation_list[]` — one entry per attester | — | OCSF's array is the cleaner multi-attester shape |
| `audit.integrity.algorithm` (Resource, JWA) | MUST if value set | `signatures[].algorithm_id`/`algorithm` (per signature) | required | placement + naming differ; see §2.7 |
| `audit.integrity.certificate` (Resource) | MAY | *(no generic key-id field; fixture: `unmapped.signature_key_id` = JWKS `kid`)* | - | `digital_signature.certificate` describes an X.509-style certificate, not a bare `kid`; #1709 did not add a key-id field |
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
its origin-side signing input and cannot be re-derived after translation
without the signing key.** This fixture signs the decoded HMAC fingerprint,
not the canonical JSON directly. Translating the record cannot re-sign it.
A transform must preserve the origin-side digest, its declared
canonicalization, and the signing-input rule along with the signature,
or the proof degrades to noise. The derived vectors carry the digest and
canonicalization with three attributes:
`ocsf.attestation.entry_hash`, `ocsf.attestation.entry_hash.algorithm`,
`ocsf.attestation.canonicalization`. Verification recipe in §3.

The rebased OTel draft also specifies how to serialize the signing input.
Declaring the source canonicalization does not make a signature over the
OCSF fingerprint digest a signature over that OTel input.

Note what this means for strict conformance: a producer whose proof is over a
non-JCS canonicalization (this fixture's is a declared producer scheme) can
be *represented* in the OTel shape but not *conformant* to the MUST as
written. Half fixed by the §4 ask: `audit.integrity.canonicalization` landed —
`jcs` is the assumed default and producers SHOULD declare any other scheme,
so verifiers no longer guess and the spurious-failure mode is named in the
spec. But the JCS mandate ("MUST NOT use any other serialization or
canonicalization method") still stands, so the declared-non-JCS producer is
representable but still non-conformant. The divergence is now declared
rather than silent — the honest half of the fix.

### 2.2 The chain pointer: id + hash now available in OTel

In the rebased draft, `audit.sequence.previous_hash` is the preceding
record's IntegrityHash itself, **not SHA-256 of that hash**. The fixture's
`prev_event.fingerprint.value` already holds its predecessor's chain hash;
the script copies it directly, without rehashing. This equivalence relies
on this producer's fingerprint being the predecessor integrity hash; other
producers must check their own hash semantics before applying the row.
`audit.sequence.previous_hash` binds the chain by content;
`audit.sequence.previous_record_id` (`= audit.record.id` of the
predecessor) is the resolvable locator — the §4 ask landed, so OTel now
carries both halves, matching OCSF's `prev_event` (`uid` + `fingerprint`).
The requirement levels still tell the story: within `prev_event`, `uid` is
**required** and `fingerprint` optional, while on the OTel side both pointer
attributes are MAY. A predecessor hash proves linkage but cannot locate
the predecessor across storage, sharding, or retention boundaries (raised as
a #2409 review point; the id half is what makes a broken-chain investigation
actionable). Transform rules are now mechanical in both directions:
OCSF-to-OTel maps `prev_event.uid` to `audit.sequence.previous_record_id`
directly; the vectors already emit this native attribute. OTel-to-OCSF maps it to
`prev_event.uid` when present. If it is absent for a non-genesis record,
OCSF's required predecessor uid cannot be inferred from the current
record's id; the transform needs the preceding record or must report the
missing pointer.

**The hash half is representable, not conformant.** The structural mapping
above is closed; the value semantics are not. The pinned draft defines
`audit.sequence.previous_hash` as the predecessor's `IntegrityHash`: "the
SHA-256 hash of the canonical serialization of the `AuditRecord` as it was
written to persistent storage, computed by the sink", canonicalized per JCS
(RFC 8785). A `previous_hash` that does not match the stored `IntegrityHash`
of the previous record "MUST be treated as a critical integrity violation."
The value this transform copies from `prev_event.fingerprint.value` is the
OCSF-origin entry hash: keyed HMAC-SHA-256 (`algorithm_id` 99) over a
producer-declared, non-JCS serialization. It is not SHA-256, not JCS, and
not taken over the OTel record, so a draft-conformant receiver comparing it
against the stored `IntegrityHash` flags every chained record in the derived
vectors as tampering. Section 2.1's posture, representable but not
conformant, declared rather than silent, applies to the chain pointer
exactly as it does to the proof itself.

What the post-transform check proves is narrower, and worth stating
precisely: the copied `audit.sequence.previous_hash` equals the predecessor's
carried `ocsf.attestation.entry_hash` rider, and
`audit.sequence.previous_record_id` equals the predecessor's
`audit.record.id`. That is origin-link preservation. Anyone holding the OCSF
bundle can verify structural linkage across the translation, and the full
export's 235/235 run (with the excerpt's 6/6 and the genesis record omitting
the pointer per section 2.3) is that property passing. It is not OTel chain
conformance, and the two claims must not run together.

The conforming path, if the derived vectors ever need real OTel chain
semantics: the transform, acting as the sink for the records it emits,
computes each record's `IntegrityHash` (SHA-256 over the JCS
canonicalization of the OTel record minus `audit.integrity.*`) and points
`previous_hash` at the predecessor's computed value, while the OCSF-origin
hash stays in the `ocsf.attestation.*` rider so both chains coexist and
nothing the OCSF side proves is lost. That is a generator and vectors
change, not a wording fix, and the post-transform check would gain a second
assertion: `previous_hash` equals the recomputed predecessor `IntegrityHash`.
Until the fixture carries a computed `IntegrityHash`, this row is honest
only with the representable, not conformant label.

### 2.3 Genesis: by omission, both sides — closed

OTel (current): the first record of a stream **MUST omit** the
previous-record pointer — no SHA-256-of-empty-string constant, no magic
value. Absence is the normative genesis signal, and receivers MUST NOT
require a constant for genesis detection. (The §4 ask landed stronger than
written.) OCSF fixture behavior is the same: genesis **omits `prev_event`
entirely** — there is no predecessor to point at. The old empty-string
constant was schema-safe (unlike a `"GENESIS"` string sentinel, which we
shipped once and documented as an anti-pattern), but it was
indistinguishable from a genuine hash of empty content and made "has a
predecessor" a value comparison instead of a presence check. The vectors'
rule — genesis omits the pointer — is now the spec's rule. For back-compat,
a receiver may still treat the old OTel constant as a genesis marker, but
producers MUST NOT emit it.

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
source), not the literal string "producer": a tier is not an identity.
The transform still needs an identity from outside the tier-role field.

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
**Resource** scope for ordinary records; OCSF carries `algorithm` per
signature. The rebased OTel draft defines an explicit key-transition
record: `audit.integrity.value` uses the outgoing key,
`audit.integrity.new_value` uses the incoming key, incoming-key metadata
identifies it, and subsequent batches use the new Resource-level key.
This script does **not** model or verify such transition records or split
exports into Resource batches. It hard-fails if the input contains more
than one signing key or algorithm, rather than silently treating a
multi-key export as this single-key fixture.

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

### 2.9 Stream end: OTel signals it, OCSF does not

`audit.sequence.end` (bool, MAY) is `true` on the last record of a
gracefully closed stream — the SDK SHOULD set it on the final record
emitted during `ForceFlush`/`Shutdown`. Absence means the stream end is
unknown (crash, forcible kill, still-running stream), and receivers MUST NOT
treat a missing `end` as a chain violation: an ambiguous boundary, not proof
of tampering. Once an `end: true` record is persisted, any subsequent record
under the same `stream_id` is a chain violation. This resolves the graceful
half of the OTEP's completeness-boundary question; crash truncation stays
honestly "unknown."

OCSF 1.9's attestation object (`authority_uid`, `chain_uid`, `fingerprint`,
`prev_event`, `signatures`, `uid`) has no end-of-chain marker, and this
fixture's producer emits none. An optional `attestation.is_final` is proposed
in [ocsf-schema#1755](https://github.com/ocsf/ocsf-schema/issues/1755),
not present in the pinned 1.9.0 schema.

Transform rules:

- **OCSF-to-OTel: omit unless a prior transform parked a positive bit.** The
  native OCSF shape cannot say whether its stream closed cleanly, and
  OTel's absence semantics are exactly "unknown". Inventing an end signal
  would fabricate attestation.
- **OTel→OCSF: park in `unmapped.audit_sequence_end`.** Dropping `end: true`
  silently demotes a graceful close to "unknown" on the OCSF side — a
  verifier-visible information loss. This is a reverse-transform rule,
  not a feature exercised by the OCSF-to-OTel vector script.

---

## 3. Test vectors

| File | What |
|---|---|
| [`otel-audit-records.sample.ndjson`](otel-audit-records.sample.ndjson) | 7 OTel `AuditRecord`s derived from the bundle's annotated excerpt (one agent's lifecycle, chain seq 16–22) |
| [`derive_otel_vectors.py`](derive_otel_vectors.py) | stdlib-only derivation + post-transform chain verification; `--full` runs the 236-event production export |
| OCSF side | the [reference bundle](../cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle/) — same records, origin shape, with its own verifier (`regenerate.py`) |

Because both shapes are derived from the same production records, they chain
against **each other**: record N+1's `audit.sequence.previous_hash` (OTel shape)
equals record N's `attestation.fingerprint.value` (OCSF shape). Current run:
7/7 excerpt records, 6/6 internal links; full export 236 records, 235/235
links, 1 genesis (prev omitted).

> **Re-pinned 2026-10-06** from `25bff70e` to the rebased data-model
> `3c5a0ff`: `previous_hash` now means the predecessor's IntegrityHash,
> not SHA-256 of it. The script already copies the predecessor fingerprint
> without rehashing, emits `previous_record_id` natively, and checks both
> hash and id linkage. These vectors remain a single-key OCSF 1.9.0
> translation, not proof of OTel JCS signing or key-transition support.

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
    "audit.sequence.previous_hash": "90ba42f3b92586ff…",
    "audit.sequence.previous_record_id": "98",
    "audit.integrity.value": "MEUCIQC7SNQRH0a8IEKO…",
    "audit.integrity.signer": "producer",
    "audit.integrity.canonicalization": "AI-Identity audit chain v1 (sorted-compact JSON + prev hash)",
    "ocsf.attestation.entry_hash": "1d9548729d942e30…",
    "ocsf.attestation.entry_hash.algorithm": "HMAC-SHA-256",
    "ocsf.attestation.canonicalization": "AI-Identity audit chain v1 (sorted-compact JSON + prev hash)",
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
`stream_id` = `chain_uid`, `previous_hash` = seq 17's fingerprint value, the
signature carried with its origin digest and declared canonicalization, the
human in `audit.actor.*` and the agent in `gen_ai.agent.*`, the Allowed
decision surviving next to the derived outcome.

---

## 4. Spec asks: status relative to the pinned revisions

Asks 1-3 are present in the pinned `auditing` branch draft; they originally
landed before its rebase
([7cac2e1](https://github.com/apeirora/opentelemetry-specification/pull/6/commits/7cac2e1dcbaa028bf7941308413df0b7035972a8),
"address the three open points from levaj2000"). The pinned revision is
`3c5a0ff`, not the old `25bff70e` branch tip. Note the follow-up renames:
`prev_hash` to `previous_hash`,
`prev_record_id` → `previous_record_id`.

1. **`audit.integrity.canonicalization` (OTel, landed as written).**
   Declaration attribute exists: `jcs` is the assumed default, producers
   SHOULD declare any other scheme, verifiers no longer guess (§2.1's
   spurious-failure mode is named in the spec). The JCS mandate ("MUST NOT
   use any other serialization") still stands, so a declared non-JCS
   producer remains representable but non-conformant — the divergence is now
   declared rather than silent.
2. **`audit.sequence.previous_record_id` (OTel, landed).** The resolvable
   half of the chain pointer, `= audit.record.id` of the predecessor (see section 2.2).
3. **Genesis by omission (OTel, landed stronger than asked).** First record
   MUST omit the previous-record pointer; receivers MUST NOT require a magic
   constant (§2.3 closed).
4. **Signature bytes (OCSF, merged after 1.9.0); key reference (still a
   gap).** [ocsf-schema#1709](https://github.com/ocsf/ocsf-schema/pull/1709)
   added optional, standard-Base64 `digital_signature.value` for raw
   signature bytes. The pinned 1.9.0 fixture predates it and still stores
   bytes at `unmapped.signature_b64`; it must not claim the new field while
   `metadata.version` says `1.9.0`. #1709 did **not** add a generic JWKS
   `kid` slot. `digital_signature.certificate` represents an X.509-style
   certificate, not this fixture's bare key reference, so
   `unmapped.signature_key_id` remains. A versioned migration would need
   updated signing exclusions, validation, and conformance vectors.
5. **End-of-chain marker (OCSF, tracked in
   [#1755](https://github.com/ocsf/ocsf-schema/issues/1755)).**
   `audit.sequence.end` has no OCSF home (see section 2.9); the transform parks a
   positive signal in `unmapped` for reverse translation. This gap bites
   OTel-to-OCSF; the reverse direction honestly omits `end` when closure is
   unknown. Coordinate the proposed `attestation.is_final` field on #1755.

This fixture demonstrates OCSF-to-OTel chain-link preservation for one key
and one hash scheme. It does not establish a generic, escape-hatch-free
round trip: non-JCS signing, key identification, sequence numbering,
stream finality, and OTel key transitions still require explicit handling.

---

*Maintained in the AI Identity repo; regenerate the vectors with
`python3 derive_otel_vectors.py` after any bundle refresh. Questions /
corrections: the #2409 thread, or issues here.*
