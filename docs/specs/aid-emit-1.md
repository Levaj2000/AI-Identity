# AID-EMIT-1 — AI Identity Evidence Emitter Format

| Field         | Value                                                            |
|---------------|------------------------------------------------------------------|
| **Name**      | AID-EMIT-1                                                       |
| **Version**   | 1.2.0-draft                                                      |
| **Status**    | Draft — open for conformance review                              |
| **Date**      | 2026-10-12                                                       |
| **License**   | Apache-2.0 (same as the reference implementation)                |
| **Reference implementation** | [`integrations/cpex-ocsf-audit`](../../integrations/cpex-ocsf-audit) (adapter #1) |
| **Conformance vectors** | [`SAMPLE-OUTPUT.md`](../../integrations/cpex-ocsf-audit/SAMPLE-OUTPUT.md), [`SAMPLE-OUTPUT-DECISIONS.md`](../../integrations/cpex-ocsf-audit/SAMPLE-OUTPUT-DECISIONS.md), [`SAMPLE-OUTPUT-PROVENANCE.md`](../../integrations/cpex-ocsf-audit/SAMPLE-OUTPUT-PROVENANCE.md); the `aid` names in the in-tree praxis port (section 12) |

---

## Abstract

AID-EMIT-1 specifies a host-agnostic wire format for **signed, hash-chained,
OCSF-shaped audit evidence** emitted from a policy-enforcement point: what a
record contains, which bytes its fingerprint and signature cover, how records
chain, how enforcement decisions are rendered without losing distinctions, and
what a host engine must guarantee so that an out-of-tree emitter can attach
without source changes.

A record conforming to this specification can be verified **offline** — chain
integrity and signature — by any party holding the emitted JSON, the
authority's published public key, and this document. The format was first
verified against the CPEX audit seam (cpex PR #166) by the reference
implementation with zero source changes, and is versioned here so subsequent
hosts (including the Praxis policy engine, praxis#11/#12) implement a named
specification rather than vendoring an implementation.

This specification covers the **emitter side only**: producing verifiable
records. Key custody (HSM/KMS residency, rotation epochs, JWKS publication),
transparency-log anchoring and inclusion proofs, long-term re-attestation
across key rotations, cross-stream reconciliation at scale, and retention are
the domain of the authority operating the evidence plane, and are out of scope
here (see §2 and §13).

## Conformance language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be
interpreted as described in RFC 2119 and RFC 8174 when, and only when, they
appear in all capitals.

Three conformance classes are defined (§12):

- **Emitter** — produces AID-EMIT-1 records.
- **Host seam** — the engine surface an emitter attaches to.
- **Verifier** — checks records per §11.

## 1. Terminology

- **Host** — the policy engine or gateway in which the emitter runs (e.g. the
  CPEX core, or PPE inside the Praxis gateway).
- **Emitter** — the component that renders host activity and decisions as
  AID-EMIT-1 records. The reference emitter is the `cpex-ocsf-audit` plugin.
- **Record** — one emitted OCSF event carrying an attestation entry.
- **Chain** — the sequence of records sharing a `chain_uid`, linked by
  `prev_event` back-references bound into each record's fingerprint.
- **Authority** — the party named by `authority_uid`, which owns the signing
  key and its custody story.
- **Decision record** — a record produced at pipeline verdict time carrying
  the executor's `DecisionLog` (§9), as opposed to a passive observation
  record.

### 1.1 Namespaces

Field names under `unmapped` use two prefixes:

- **`aid.*`** names this format's own facts, the ones OCSF has no field for:
  the stream stamps (section 7), the decision steps and verdict, the
  invocation span, the entry-taint labels and the content digests (section
  9). The prefix is the format's, so a record says the same thing whichever
  engine emitted it.
- **`cmf.*`** names gap fields of the Common Message Format, the message
  format the reference hosts speak: `cmf.completion.stop_reason`, `cmf.mcp.*`,
  `cmf.framework.*`, `cmf.security.labels`, `cmf.workload_identity` and the
  join key `cmf.request.request_id` (section 8). CMF is a message format shared
  across hosts and emitters, not a product, so the prefix stays. An emitter
  whose host does not speak CMF has no `cmf.*` members and names its host gap
  fields `aid.<host>.*` (section 1.2).

Both are wire names: consumers and SIEM queries key on them, so from this
revision on an emitter MUST NOT rename them. A different message format gets
its own host prefix, never a rename of these strings.

**Why this draft renames.** Drafts before 1.2.0 used `cpex.*` for the facts
now under `aid.*`, and pinned those strings on the same rule. `cpex` named one
product, the first host the reference emitter ran in. The reference emitter's
home is now the in-tree port in praxis-proxy/policy, an engine that is not
that product, and the first release that ships these records to a consumer is
its 0.5.0, which carries the port. No consumer has keyed on `cpex.*`, so the
rename happens here, before the first consumer exists, rather than through a
successor format once one does. Section 13 records the versioning
consequence. `cpex.*` is retired: an emitter MUST NOT produce it, and a
verifier MAY accept it, reading `cpex.stream`, `cpex.decision`, `cpex.span`,
`cpex.taint.input_labels` and `cpex.content` as the `aid` member of the same
name, for records produced by pre-release builds.

### 1.2 Member table

| Fact | Member | Section |
|---|---|---|
| Stream stamps | `unmapped."aid.stream"` | 7 |
| Decision steps and verdict | `unmapped."aid.decision"` | 9 |
| Invocation span | `unmapped."aid.span"` | 9 |
| Entry-taint labels | `unmapped."aid.taint.input_labels"` | 9 |
| Content provenance | `unmapped."aid.content"` | 9.2 |
| Join key, CMF hosts | `unmapped."cmf.request.request_id"` | 8 |
| Join key, other hosts | `unmapped."aid.request_id"` | 8 |
| Host gap fields, CMF hosts | `unmapped."cmf.*"` | 3 |
| Host gap fields, other hosts | `unmapped."aid.<host>.*"`, e.g. `aid.litellm.deployment` | 3 |

Rules:

1. A member has one structure and one meaning wherever it appears; the host
   prefix changes which gap fields exist, never what an `aid.*` member means.
2. An emitter uses one host prefix per record, `cmf.*` or `aid.<host>.*`, and
   carries the join key under that prefix's name. A verifier reads
   `aid.request_id` first and falls back to `cmf.request.request_id`.
3. A fact with a native OCSF home MUST be emitted there and MUST NOT be
   repeated under `unmapped`; the prefixes name only facts OCSF has no field
   for. The reference emitter's documented deviations from OCSF 1.9.0 (fields
   it emits where the schema has no such member) are tracked in its README
   and are not an exception to this rule; they move in a later revision.
4. A prefix changes no covered-bytes rule. Every `aid.*` and `cmf.*` member
   sits inside the hashed bytes (section 4).
5. Records carry no namespace marker; the members present identify the host
   prefix. This matches section 13, where the wire-level descriptors, not a
   version field, are the self-description.
6. The host registration contract (section 10) describes the CMF seam. An
   emitter in another host conforms as an Emitter (section 12) and documents
   how it attaches, including whether it sees denied requests (section 9.3).

## 2. Scope and non-goals

In scope: the record shape, the canonical signing input, the fingerprint and
chain construction, the signature envelope, record identity, stream stamps,
the request join key, the decision vocabulary, the host registration contract,
the additive guarantee, and the offline verification procedure.

Out of scope, by design:

- **Key custody.** The emitter holds a key handle, not a key service. HSM/KMS
  residency, rotation epochs, and JWKS publication (including the
  never-unpublish guarantee for old keys) belong to the authority named by
  `authority_uid` — which is inside the hashed bytes precisely so the claimed
  authority cannot be swapped after the fact.
- **Third-party inclusion claims.** An emitter structurally cannot prove that
  a record was present in a log at a point in time; that is a claim only a
  party independently holding the log can make. Nothing in this format
  precludes such anchoring downstream; nothing in it provides it.
- **Transport and storage.** How records reach a consumer (stderr, file,
  HTTPS ingest, message bus) is deployment configuration.
- **Draw settlement and receipt minting.** Mandate settlement is a separate
  authority-plane API; this format only carries the join key (§8) that lets a
  settlement receipt reconcile against the record stream.

## 3. Record model

A record is an **OCSF API Activity (class_uid 6003)** event.
The reference emitter and conformance vectors set `metadata.version` to
`1.9.0`; later OCSF schema additions do not silently change this wire format.

- `metadata.profiles` MUST declare `"ai_operation"` and `"security_control"`,
  and MUST additionally declare `"record_integrity"` when chaining is enabled.
- `metadata.product` SHOULD identify the emitter implementation.
- `metadata.uid` MUST be present on every chained record (§6).
- `metadata.correlation_uid` carries the conversation/run-stable id (the same
  value on every event of a run). Per-call ids ride at `api.request.uid`.
  Per-request ids used for receipt reconciliation ride at the join key (§8) —
  the three MUST NOT be conflated.
- Activity mapping: resource/prompt fetches and tools declaring
  `readOnlyHint: true` → `activity_id 2` (Read); other tool invocations →
  `activity_id 99` with `activity_name: "Invoke Tool"`; completions →
  `activity_id 99` with `activity_name: "Completion"`. `destructiveHint` is
  security context and MUST NOT be rendered as a Delete claim.
- Fields with no native OCSF home ride under `unmapped` (gap fields:
  `cmf.completion.stop_reason`, `cmf.mcp.*`, `cmf.framework.*`, monotonic
  security labels, workload identity). The executable field mapping in the
  reference implementation ([`src/ocsf.rs`](../../integrations/cpex-ocsf-audit/src/ocsf.rs))
  is the normative mapping reference for this version.
- Passive observation records carry `action_id 3` (Observed) /
  `disposition_id 17` (Logged). Decision records replace these per §9.

Set-derived arrays (security labels, roles, groups — anything built from an
unordered collection) MUST be sorted at build time, so the emitted event is
itself canonical and array order can remain significant during
canonicalization (§4).

## 4. Canonical signing input

The fingerprint and the signature cover the **same bytes**, produced as
follows from the record as emitted:

1. Remove `attestation_list[0].fingerprint` and
   `attestation_list[0].signatures` (the schema's own exclusions — these are
   derived from the hash and cannot be inside it). The attestation entry's
   `uid`, `chain_uid`, `authority_uid`, and `prev_event` **remain present**:
   the record's chain position and claimed authority are inside the hashed
   input.
2. Remove `unmapped.signature_b64` and `unmapped.signature_key_id` (the
   signature and JWKS key-id locations in this 1.9.0 wire format, see section 5).
   If this leaves `unmapped` empty, remove `unmapped` itself.
3. Serialize canonically per RFC 8785 (JCS): object keys sorted, compact
   output, array order preserved.

Emitters MUST declare this by setting, in the `fingerprint` object,
`serialization_id 2` (JCS). That declaration is a promise that an
off-the-shelf RFC 8785 implementation reproduces the bytes, for every value a
record can carry:

- Object keys are any Unicode string, sorted by UTF-16 code units (RFC 8785
  section 3.2.3). Byte order and code point order agree with it inside the
  Basic Multilingual Plane and differ above it, so a canonicalizer MUST sort
  by code units, not bytes.
- Numbers are IEEE 754 doubles written in the ES6 `Number::toString` form
  (RFC 8785 section 3.2.2.3): `1.0` is `1`, `1e21` is `1e+21`, `1e-7` stays
  `1e-7`, and the shortest round-trip digits are chosen with ties to even.
- Integers are written as their exact decimal digits. Values beyond 2^53,
  which this format carries (the stream `epoch` is a nanosecond value, section
  7), are outside RFC 8785's interoperable range, so a verifier MUST parse
  them exactly rather than through a double, and MUST parse floats with a
  correctly rounding parser so the digits it re-serializes are the digits it
  read.

Drafts before 1.2.0 constrained the value space to ASCII keys and integers
and told emitters that could not meet it to declare `serialization_id 99`.
That constraint is withdrawn: a float bound in a tool's `inputSchema` or a
non-ASCII annotation key is routine metadata and is valid under the RFC. An
emitter that implements some other scheme still declares `99` (Other) and
names it.

**Fingerprint.** `SHA-256` over the canonical bytes, emitted as bare
lowercase hex — no `sha256:` prefix, no encoding markers inside the value.
The fingerprint object declares its own interpretation:

```json
"fingerprint": {
  "algorithm_id": 3,  "algorithm": "SHA-256",
  "encoding_id": 1,   "encoding": "Hex",
  "serialization_id": 2, "serialization": "JCS",
  "value": "<64 lowercase hex chars>"
}
```

Note: `fingerprint.algorithm_id 3` (SHA-256) and
`digital_signature.algorithm_id 3` (ECDSA) are **different enums** that happen
to share a number. Implementations MUST NOT conflate them.

## 5. Signature envelope

Signing is optional (a chain with no signer is tamper-evident but not
identity-bound); when present it MUST be:

- **DSSE** (`digital_signature.serialization_id 5`): the signature is computed
  over the DSSE Pre-Authentication Encoding of the canonical bytes (§4), never
  the raw payload:

  ```
  "DSSEv1" SP LEN(type) SP type SP LEN(payload) SP payload
  ```

  with payload type `application/vnd.ocsf.event+json`.
- **ECDSA P-256 with SHA-256** (`digital_signature.algorithm_id 3`), signature
  serialized as DER, carried base64-encoded. Deterministic signing per
  RFC 6979 is RECOMMENDED (it makes emitter output reproducible, which the
  conformance vectors rely on).
- The `attestation_list[0].signatures` entry carries the OCSF
  `digital_signature` descriptor:

  ```json
  { "algorithm_id": 3, "algorithm": "ECDSA",
    "serialization_id": 5, "serialization": "DSSE" }
  ```

- In this 1.9.0 wire format, signature bytes ride at
  `unmapped.signature_b64` and the key identifier (the JWKS `kid`) at
  `unmapped.signature_key_id`, **outside the hashed bytes** (section 4, step 2).
  [ocsf-schema#1709](https://github.com/ocsf/ocsf-schema/pull/1709)
  subsequently added optional `digital_signature.value` for standard-Base64
  raw signature bytes, but did not add a generic key-id field.
  `digital_signature.certificate` describes an X.509-style certificate
  (including issuer and serial number), not a bare JWKS `kid`. Moving the
  bytes to `value` requires a deliberate schema-version and format update;
  it does not happen in this version, and the `kid` still needs a home.

Because the signed bytes include the attestation entry's `chain_uid`,
`authority_uid`, and `prev_event`, the signature commits to the record's chain
position and claimed authority — a spliced, reordered, or re-attributed record
fails verification without any reference to storage.

## 6. Chain fields and record identity

Every chained record carries exactly one attestation entry at
`attestation_list[0]`:

| Field | Requirement |
|---|---|
| `uid` | Attestation entry id. MUST be unique per record. |
| `chain_uid` | Stable id of the chain (one per emitter deployment / edge). All records of a chain share it. |
| `authority_uid` | The signing authority. MUST be present when signing is enabled. Inside the hashed bytes. |
| `prev_event` | Back-reference to the predecessor: its `metadata.uid`, its `type_uid`, and its full `fingerprint` object. Absent on the genesis record of a chain, present on every other record. |
| `fingerprint` | This record's fingerprint (§4). Excluded from its own hash. |
| `signatures` | Signature descriptor(s) (§5). Excluded from the hash. |

**Record identity.** `metadata.uid` MUST be present before hashing (the next
record's `prev_event.uid` points at it) and MUST be unique within the chain.
Consumers MUST deduplicate on `metadata.uid`, treating an identical replay as
idempotent, and MAY use `(epoch, stream_id, stream_seq)` (§7) as a fallback
identity where `metadata.uid` is unavailable.

**Concurrency.** Sequence allocation, predecessor read, and chain advance MUST
be atomic in the emitter: two concurrent emissions must not mint the same uid
or fork the chain off the same predecessor.

## 7. Stream stamps

When the host seam provides completeness/ordering stamps, decision records
MUST carry them at `unmapped."aid.stream"`, **inside the hashed bytes**:

```json
"aid.stream": {
  "epoch": 1755000000000000000,
  "stream_id": "decision",
  "stream_seq": 7,
  "emission_seq": 42
}
```

- `epoch` identifies one host process lifetime; it changes on restart. Chains
  and sequence claims are scoped to an epoch.
- `stream_seq` MUST be dense (increment by exactly 1) per
  `(epoch, stream_id)`, and MUST start at `0`: the first record a host emits
  in an epoch carries `stream_seq: 0`. (The reference host stamps from a
  zero-initialised counter, so a restart resets the sequence to 0, not 1.)
  A gap in `stream_seq` is **evidence** — a crashed emitter, a dropped
  record, or tampering — and consumers MUST surface it, not renumber or
  discard around it. That includes the head: an epoch whose first observed
  record is `stream_seq: n > 0` has lost records `0..n-1`, and a consumer
  holding the stream's history MUST surface that exactly like an interior
  gap. A verifier given only a slice of a stream MAY report a non-zero head
  as unverifiable rather than as a loss. Post-hoc renumbering is impossible
  by construction: the stamps are inside the fingerprinted bytes.
- `emission_seq` orders emissions across streams within an epoch.

## 8. Join key

Records for requests carrying a per-request id MUST emit it at
`unmapped."cmf.request.request_id"` on a CMF host and `unmapped."aid.request_id"`
on any other (section 1.2), inside the hashed bytes.

This is the reconciliation key between a record stream and externally issued
settlement artifacts: a signed draw receipt naming `correlation_id` reconciles
against the OCSF stream via
`receipt.correlation_id == event.unmapped."cmf.request.request_id"` (or
`event.unmapped."aid.request_id"`). It is
deliberately NOT `metadata.correlation_uid` (reserved for the run-stable id) —
a per-request id correlates nothing across events. A token's `revocation_id`
needs no event field; the receipt names it, and the join key connects the two.

## 9. Decision records

A decision record renders the executor's finalized `DecisionLog` — the ruling
and every step that produced it. The distinctions below are the point of the
format; an implementation that collapses any of them does not conform.

### 9.1 Verdict mapping

| Verdict | `action_id` / `action` | `disposition_id` / `disposition` | Status |
|---|---|---|---|
| Allow (clean) | 1 Allowed | 1 Allowed | — |
| Allow after payload or extensions modification | 4 Modified | 1 Allowed | — |
| Deny | 2 Denied | 2 Blocked | `status_id 2`, violation at `status_code` / `status_detail` |

- `activity_*` and `type_uid` are untouched by the overlay: they describe the
  operation observed; the action describes what the control did about it.
- The violation **code** MUST survive to `status_code` intact. In particular
  `plugin_panic` (a fail-closed panic) MUST arrive distinguishable by code
  from an ordinary `plugin_error`.
- A modified-allow MUST NOT be re-coded as a plain allow.

### 9.2 Step vocabulary

The ordered per-plugin steps ride at `unmapped."aid.decision".steps`, inside
the hashed bytes, using this fixed snake_case vocabulary (stable across
upstream enum renames — SIEM queries key on these strings):

`allowed` · `denied` · `modified_payload` · `modified_extensions` ·
`deny_ignored` · `aborted` · `error`

Two distinctions MUST be preserved:

- **`deny_ignored` is not `allowed`.** A suppressed deny — a policy fired and
  was overridden — is the record analysts actually ask for. The step keeps the
  action `deny_ignored`, and the record additionally carries the flat flag
  `unmapped."aid.decision".deny_ignored: true` so "every suppressed deny" is
  one query. The record's top-level action still reflects the enforcement
  outcome (allow), never the other way around.
- **`aborted` is not `error`.** An intentional cancellation (a concurrent
  sibling short-circuited the phase) must not read as a crash. `error`
  carries its message beside the action, not inside it.

A `denied` or `deny_ignored` step MAY carry a `detail` member naming the
violation that produced it: `code` and `reason` always, `description` and
`details` only when the plugin set them (the same shape the PPE reference
`audit-logger` emits). It is present when the host seam binds the violation to
the step (praxis-proxy/policy PR #84 and later) and absent when the seam
records the step without it (cpex PR #166, where only the terminal verdict
names a violation, at `status_code` / `status_detail`). A verifier MUST NOT
require `detail`, and MUST NOT infer from its absence that no violation
occurred — the step's action is the claim, `detail` is its provenance. For
`deny_ignored` it is the only place the objection's code survives, since no
verdict names a suppressed deny. Added in 1.1.0 (additive, inside the hashed
bytes like every other step member — so the vector for the decision demo
differs by exactly this member between the two hosts, §12).

Decision records also carry the terminal verdict (`unmapped."aid.decision"`),
the invocation span (`unmapped."aid.span"`), the entry-taint labels
(`unmapped."aid.taint.input_labels"`) and content provenance hashes
(`unmapped."aid.content"`), all inside the hashed bytes, so the decision facts
are tamper-evident, not advisory.

**Content digest form (informative, added in 1.1.1).** When the host captured
content provenance, a decision record carries `unmapped."aid.content"` with
two members, `input_hash` (the payload at pipeline entry) and `output_hash`
(the payload the caller receives, or the one refused on a deny). Both are the
host's values, carried as opaque strings inside the hashed bytes; the emitter
does not define the digest scheme and a verifier MUST NOT require one or
recompute either value. The form is self-describing:

- `hmac-sha256:<key_id>:<hex>`: a keyed digest under a deployment secret the
  host holds (praxis-proxy/policy PR #84 `2d717e8` and later, where the engine
  takes both digests and the sink never sees the key). `<key_id>` is a
  fingerprint of the key, stable across restarts and different after a
  rotation. Two digests are comparable only when their key ids match; a
  reader seeing different ids knows the key changed, not the content.
- `sha256:<hex>`: an unkeyed digest. This is what cpex PR #166 records (the
  emitter computes the output digest there, with the same function the host
  used at entry) and what PPE records under its explicit `unkeyed`
  development setting. A plain digest of short or templated content is
  guessable, which is why the keyed form exists; a reader should treat an
  unkeyed digest of redacted content as a confirmation oracle, not a secret.

Equal digests under one scheme and key mean the pipeline did not alter the
content; different ones mean it did. `output_hash` is `null` when nothing was
digested at emission (no payload, or one that does not opt in); a verifier
MUST NOT read null as "unchanged". The member is absent from the committed
vectors (section 12), which do not enable provenance.

### 9.3 Denial coverage

A conforming emitter attached in decision-sink mode (§10) MUST produce a
record for **denied** dispatches. This is the structural difference from a
post-hook observer, which only ever sees allowed traffic.

## 10. Host registration contract

A conforming host seam MUST support both attachment modes with these
semantics:

1. **Decision-audit sink (no `hooks:` configured).** The emitter auto-attaches
   as a decision-audit sink (`AuditHandler`) and is invoked at every pipeline
   verdict with the finalized `DecisionLog` — denials included.
2. **Post-hook observer (`hooks:` listed).** The emitter attaches to the
   listed post-hooks only, sees allowed traffic only, and MUST NOT also
   auto-attach as a sink — one dispatch never emits twice from one configured
   instance.

The emitter is observation-only in both modes: it MUST always return
success/continue to the host and MUST NOT alter payloads, extensions, or
verdicts.

## 11. Verification procedure

Given nothing but an emitted record, the authority's published public key, and
this document, a verifier:

1. Reconstructs the covered bytes per §4 (strip
   `attestation_list[0].fingerprint` / `.signatures`, strip
   `unmapped.signature_b64` / `signature_key_id`, dropping `unmapped` if
   emptied; canonicalize per RFC 8785).
2. Recomputes SHA-256 over those bytes; it MUST equal
   `attestation_list[0].fingerprint.value` (compared per the declared
   `encoding_id`).
3. Verifies the base64/DER ECDSA-P256 signature at `unmapped.signature_b64`
   over the DSSE PAE (§5) of the same bytes, using the key identified by
   `unmapped.signature_key_id`.
4. For chain verification, additionally checks that each record's
   `prev_event.uid` and `prev_event.fingerprint.value` match the predecessor's
   `metadata.uid` and recomputed fingerprint, and that `stream_seq` is dense
   per `(epoch, stream_id)` and opens at `0` (§7). A mismatch, a gap, or a
   missing head is a finding to surface, never to repair silently.

The reference implementation ships this rule as running code
(`sign::signing_input`, exercised by the `signed_event_verifies_offline` test
and printed as the `// verify` lines of `cargo run --example emit_sample`).
Even if a verifier knows the post-1.9.0 `digital_signature.value` field,
the v1 procedure still reads `unmapped.signature_b64` and
`unmapped.signature_key_id`; changing their placement requires a new
signing-input rule, validator, and conformance vectors.

## 12. Conformance and test vectors

**Emitter conformance:** produces records satisfying §3–§9 that pass the §11
procedure. The committed, deterministic outputs of the reference emitter are
the initial conformance vectors:

- [`SAMPLE-OUTPUT.md`](../../integrations/cpex-ocsf-audit/SAMPLE-OUTPUT.md) —
  dispatch records with chain + DSSE signatures (`emit_sample`).
- [`SAMPLE-OUTPUT-DECISIONS.md`](../../integrations/cpex-ocsf-audit/SAMPLE-OUTPUT-DECISIONS.md)
  — the five decision shapes: clean allow, modified-allow, denial with the
  violation surfaced, suppressed-deny + aborted branch, and the
  delegated-mandate record carrying the join key (`decision_sink_demo`).
  Generated on the PPE host; the cpex host produces the same bytes minus the
  `detail` member on the denying steps of records 3 and 4 (§9.2), and the
  file shows that delta.

- [`SAMPLE-OUTPUT-PROVENANCE.md`](../../integrations/cpex-ocsf-audit/SAMPLE-OUTPUT-PROVENANCE.md)
  (`provenance_demo`), added in 1.1.2: the content digest form of section
  9.2 in four records: unchanged content, a redaction (different digests,
  same key id, the redacted value in neither), the same content under a
  rotated key (a different key id), and the explicit unkeyed form. The keys,
  the key-id label and the canonical audit bytes are printed with the
  records, so every digest recomputes with nothing but HMAC-SHA256 and
  SHA-256. Generated on the PPE host; on cpex records 1 to 3 carry the
  unkeyed form, since that seam has no provenance key, and the file shows
  that delta.

**Where the `aid` names are pinned.** The three files above are the vector
set; a verifier that follows this list alone covers every member in section
1.2. The reference emitter's home is the in-tree port in praxis-proxy/policy
(`reference/plugins/ocsf-audit/`), and from 1.2.0 that tree's copies of the
three files carry the `aid` names, regenerated from the same examples and
pinned to this specification by commit from the crate's README. The copies
under `integrations/cpex-ocsf-audit/` in this repository are the pre-1.2.0
vectors and carry the retired `cpex` names until they are synced; the
validator accepts both (section 1.1). Only the decision and provenance
vectors change under the rename: the dispatch vector carries no `aid.*` or
`cpex.*` member, so its fingerprints and signatures are unchanged.

A standalone validator ships at
[`scripts/aid_emit1_validator.py`](../../scripts/aid_emit1_validator.py) —
Python standard library only, including pure-Python ECDSA P-256 signature
verification, so it runs anywhere `python3` does:

```bash
python3 scripts/aid_emit1_validator.py records.ndjson --key pubkey.pem
```

It implements §11 (fingerprint, signature, chain, and stream checks), the
§3/§5/§6 well-formedness rules, and the §4 value-space enforcement; stream
gaps are surfaced as findings per §7 (errors with `--strict-gaps`), and
non-6003 records receive the integrity checks with class-level checks
skipped. Its test suite exercises the §12 verifier-conformance cases:
accept the vectors; reject a flipped payload byte, a reordered record, a
swapped `authority_uid`, and a renumbered `stream_seq`.

**Host-seam conformance:** the registration contract (§10), the decision and
step vocabularies delivered intact (§9), stream stamps and the per-request id
delivered for inclusion in the hashed bytes (§7–§8), and the **additive
guarantee**: an existing out-of-tree emitter builds and passes its full test
suite against the host with zero source changes, and the host's behavior does
not change without explicit configuration. This is the claim verified against
cpex PR #166
([`SEAM-PORT-RESULTS.md`](../../integrations/cpex-ocsf-audit/SEAM-PORT-RESULTS.md));
each subsequent host port re-verifies it per
[`PRAXIS-PORT-PLAN.md`](../../integrations/cpex-ocsf-audit/PRAXIS-PORT-PLAN.md).
Any deviation a port surfaces is a conformance finding to report upstream, not
something for an emitter to silently absorb.

**Verifier conformance:** implements §11 exactly; accepts every vector;
rejects any vector with a flipped payload byte, a reordered record, a swapped
`authority_uid`, or a renumbered `stream_seq`.

## 13. Versioning

- The spec version is `MAJOR.MINOR.PATCH`. Wire-visible changes to the
  covered-bytes rule, the canonical form, the envelope, or the vocabularies
  are MAJOR. Additive, ignorable fields are MINOR — 1.1.0 added the optional
  step `detail` (section 9.2). A future move of signature bytes to
  `digital_signature.value` needs its own format/version decision and
  conformance updates; #1709's merge does not migrate v1. Editorial fixes
  are PATCH: 1.1.1 added the informative note on the content digest form
  (section 9.2), and 1.1.2 the provenance vector that exercises it
  (section 12); neither changes a covered byte or an existing vector.
- 1.2.0-draft renames the format's own members from `cpex.*` to `aid.*`
  (section 1.1) and widens the section 4 value space to the whole of RFC
  8785. By the rule above a change to wire names is MAJOR. This revision
  keeps the 1.x line because no released emitter and no consumer exists for
  the `cpex` names: the only records ever produced under them came from
  pre-release builds, and the first release to ship this format is the
  praxis port's 0.5.0, which ships the `aid` names. The rename therefore
  changes what a future consumer will see, not what any consumer has seen.
  A verifier written for 1.1 reads the renamed members through the retired
  name map in section 1.1 and needs no other change; the widened value space
  requires a verifier to canonicalize with a full RFC 8785 implementation
  rather than sorted-keys JSON, which a verifier built on a real JCS library
  already does. The vectors for the decision and provenance demos change
  under the rename; the dispatch vector does not.
- Records do not carry a spec-version field in v1; the emitted enum
  descriptors (`fingerprint.serialization_id`, `digital_signature.*`) are the
  wire-level self-description, and the OCSF schema version rides at
  `metadata.version`. A MAJOR revision that changes covered bytes will add an
  explicit marker.
- Known conformance caveats in this draft, tracked openly: OCSF schema
  validation in CI is structural-only today (open WS-E item);
  `AuditHandler::on_effect` lifecycle events await a richer OCSF class than
  6003; token identifiers on the delegation extension are an open upstream
  ask.

## 14. References

- OCSF schema — API Activity (6003), `ai_operation` / `security_control` /
  `record_integrity` profiles; attestation shape per ocsf-schema #1661
  (merged in 1.9.0); optional signature-bytes field added after 1.9.0 by
  [#1709](https://github.com/ocsf/ocsf-schema/pull/1709), with no generic
  key-id field.
- RFC 8785 — JSON Canonicalization Scheme (JCS).
- DSSE — Dead Simple Signing Envelope, v1 PAE.
- RFC 6979 — Deterministic ECDSA.
- RFC 2119 / RFC 8174 — conformance key words.
- Reference implementation and vectors:
  [`integrations/cpex-ocsf-audit`](../../integrations/cpex-ocsf-audit).
- Host seam: cpex PR #166 (canonical until the praxis seam lands — see the
  sequencing rule in
  [`PRAXIS-PORT-PLAN.md`](../../integrations/cpex-ocsf-audit/PRAXIS-PORT-PLAN.md)).
