# AID-EMIT-1 — AI Identity Evidence Emitter Format

| Field         | Value                                                            |
|---------------|------------------------------------------------------------------|
| **Name**      | AID-EMIT-1                                                       |
| **Version**   | 1.0.0-draft                                                      |
| **Status**    | Draft — open for conformance review                              |
| **Date**      | 2026-08-24                                                       |
| **License**   | Apache-2.0 (same as the reference implementation)                |
| **Reference implementation** | [`integrations/cpex-ocsf-audit`](../../integrations/cpex-ocsf-audit) (adapter #1) |
| **Conformance vectors** | [`SAMPLE-OUTPUT.md`](../../integrations/cpex-ocsf-audit/SAMPLE-OUTPUT.md), [`SAMPLE-OUTPUT-DECISIONS.md`](../../integrations/cpex-ocsf-audit/SAMPLE-OUTPUT-DECISIONS.md) |

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

### 1.1 Namespace note

Field names under `unmapped` use the `cpex.*` and `cmf.*` prefixes. These name
the **seam vocabulary of the reference host family** (the CPEX core, which
Praxis adopts as its policy engine, and its Common Message Format), not a
deployment of any particular gateway. Version 1 pins these strings as wire
names: hosts embedding the same core MUST NOT rename them, because consumers
and SIEM queries key on them. A future host with a genuinely different message
format would motivate AID-EMIT-2, not a silent rename.

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
2. Remove `unmapped.signature_b64` and `unmapped.signature_key_id` (signature
   bytes awaiting a schema home, see §5). If this leaves `unmapped` empty,
   remove `unmapped` itself.
3. Serialize canonically per RFC 8785 (JCS): object keys sorted, compact
   output, array order preserved.

Emitters MUST declare this by setting, in the `fingerprint` object,
`serialization_id 2` (JCS). That declaration is a promise that an
off-the-shelf RFC 8785 implementation reproduces the bytes. The promise holds
for the value space this format emits, which is therefore constrained:

- Object keys MUST be ASCII (byte order then equals the mandated UTF-16
  code-unit order).
- Numbers MUST be integers representable per RFC 8785's ES6 rules.

An emitter that cannot satisfy these constraints MUST NOT claim
`serialization_id 2`; it declares `99` (Other) and names its scheme.

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

- The signature bytes ride at `unmapped.signature_b64` and the key identifier
  (the JWKS `kid`) at `unmapped.signature_key_id`, **outside the hashed
  bytes** (§4 step 2). This placement is transitional pending
  [ocsf-schema#1709](https://github.com/ocsf/ocsf-schema/pull/1709); a future
  minor version will move both to their schema home when it lands.

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
MUST carry them at `unmapped."cpex.stream"`, **inside the hashed bytes**:

```json
"cpex.stream": {
  "epoch": 1755000000000000000,
  "stream_id": "decision",
  "stream_seq": 7,
  "emission_seq": 42
}
```

- `epoch` identifies one host process lifetime; it changes on restart. Chains
  and sequence claims are scoped to an epoch.
- `stream_seq` MUST be dense (increment by exactly 1) per
  `(epoch, stream_id)`. A gap in `stream_seq` is **evidence** — a crashed
  emitter, a dropped record, or tampering — and consumers MUST surface it,
  not renumber or discard around it. Post-hoc renumbering is impossible by
  construction: the stamps are inside the fingerprinted bytes.
- `emission_seq` orders emissions across streams within an epoch.

## 8. Join key

Records for requests carrying a per-request id MUST emit it at
`unmapped."cmf.request.request_id"`, inside the hashed bytes.

This is the reconciliation key between a record stream and externally issued
settlement artifacts: a signed draw receipt naming `correlation_id` reconciles
against the OCSF stream via
`receipt.correlation_id == event.unmapped."cmf.request.request_id"`. It is
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

The ordered per-plugin steps ride at `unmapped."cpex.decision".steps`, inside
the hashed bytes, using this fixed snake_case vocabulary (stable across
upstream enum renames — SIEM queries key on these strings):

`allowed` · `denied` · `modified_payload` · `modified_extensions` ·
`deny_ignored` · `aborted` · `error`

Two distinctions MUST be preserved:

- **`deny_ignored` is not `allowed`.** A suppressed deny — a policy fired and
  was overridden — is the record analysts actually ask for. The step keeps the
  action `deny_ignored`, and the record additionally carries the flat flag
  `unmapped."cpex.decision".deny_ignored: true` so "every suppressed deny" is
  one query. The record's top-level action still reflects the enforcement
  outcome (allow), never the other way around.
- **`aborted` is not `error`.** An intentional cancellation (a concurrent
  sibling short-circuited the phase) must not read as a crash. `error`
  carries its message beside the action, not inside it.

Decision records also carry, under `unmapped."cpex.decision"` /
`unmapped."cpex.span"`, the terminal verdict, the invocation span, entry-taint
labels, and content provenance hashes — all inside the hashed bytes, so the
decision facts are tamper-evident, not advisory.

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
   per `(epoch, stream_id)` (§7). A mismatch or gap is a finding to surface,
   never to repair silently.

The reference implementation ships this rule as running code
(`sign::signing_input`, exercised by the `signed_event_verifies_offline` test
and printed as the `// verify` lines of `cargo run --example emit_sample`).

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
  are MAJOR. Additive, ignorable fields are MINOR (the pending
  ocsf-schema#1709 relocation of the signature bytes will be the first).
  Editorial fixes are PATCH.
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
  (merged); signature-bytes home pending #1709.
- RFC 8785 — JSON Canonicalization Scheme (JCS).
- DSSE — Dead Simple Signing Envelope, v1 PAE.
- RFC 6979 — Deterministic ECDSA.
- RFC 2119 / RFC 8174 — conformance key words.
- Reference implementation and vectors:
  [`integrations/cpex-ocsf-audit`](../../integrations/cpex-ocsf-audit).
- Host seam: cpex PR #166 (canonical until the praxis seam lands — see the
  sequencing rule in
  [`PRAXIS-PORT-PLAN.md`](../../integrations/cpex-ocsf-audit/PRAXIS-PORT-PLAN.md)).
