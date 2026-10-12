# aid-emit: Python emitter library for AID-EMIT-1

| Field | Value |
|---|---|
| **Status** | Draft, design only. Nothing built. |
| **Proposed home** | `integrations/aid-emit-py/`, not yet created (distribution `aid-emit`, import `aid_emit`) |
| **Implements** | AID-EMIT-1 1.1.2-draft, emitter conformance class (section 12), with the proposed 1.2.0 `aid` vocabulary (section 4.1) |
| **Adapter number** | #2 (`cpex-ocsf-audit` is #1) |
| **First consumer** | LiteLLM adapter, see [`litellm-aid-emit.md`](litellm-aid-emit.md) |
| **Runtime deps** | Python >= 3.11, `cryptography` >= 44 (for `deterministic_signing`); stdlib otherwise |
| **Date** | 2026-10-12 |

---

## 1. Why this exists

AID-EMIT-1 has one implementation, in Rust, bound to the CPEX audit seam. Every
Python host (LiteLLM, the LangChain SDK, future LangGraph work) would otherwise
re-derive the covered-bytes rule, the DSSE envelope and the chain bookkeeping by
hand, and drift. This library is that logic, once, behind a small API.

The second payoff is standards-facing: an independent implementation that
reproduces the section 12 vectors byte for byte is evidence that AID-EMIT-1 is a
specification and not a description of one crate's behavior.

Feasibility is already checked (section 10): stdlib `json` plus `cryptography`
reproduces both signed records of `SAMPLE-OUTPUT.md` byte for byte, and
`scripts/aid_emit_py_vector_check.py` re-runs that check.

## 2. Scope

In scope:

- Canonical signing input (AID-EMIT-1 section 4), fingerprint object, DSSE PAE
  and ECDSA P-256 signature envelope (section 5).
- Chain state and record identity (section 6), stream stamps (section 7).
- A durable local spool, and recovery of chain head and epoch from it.
- A reference HTTPS shipper for `POST /api/v1/audit/ingest`.
- Shared OCSF builders for the parts every host emits the same way: the 6003
  skeleton, the verdict overlay (section 9.1), the step list (section 9.2).

Out of scope:

- **Host mapping.** Each adapter builds its own pre-chain event from its own
  host's data. The library never guesses what a host meant.
- **Key custody.** The library takes a `Signer`. A PEM-file signer ships for
  dev and POC use; a KMS signer is a later adapter. Rotation, JWKS publication
  and HSM residency belong to the authority (AID-EMIT-1 section 2).
- **Settlement.** Draw settlement is an authority-plane call the host makes. The
  library only carries the join key the host hands it (section 8).

## 3. Package layout

```
aid_emit/
  canonical.py   covered_bytes(), canonical_bytes(), value_space_violations()
  envelope.py    dsse_pae(), fingerprint_obj(), Signer protocol, PemSigner
  stamps.py      epoch allocation, per-stream counters
  chain.py       Emitter: the atomic allocate, hash, sign, append step
  spool.py       append-only NDJSON spool, head and epoch recovery
  ship.py        IngestShipper: spool tail to /api/v1/audit/ingest
  ocsf.py        shared builders: 6003 skeleton, verdict overlay, steps
  verify.py      verify_record(), verify_chain(): the section 11 procedure
```

## 4. Public API (sketch)

```python
from aid_emit import Emitter, EmitterConfig, PemSigner

emitter = Emitter(
    EmitterConfig(
        chain_uid="edge-litellm-poc-0",
        authority_uid="org-f3576cf6",
        product_name="AI Identity OCSF Audit (LiteLLM)",
        spool_dir="/var/lib/aid-emit",
        signer=PemSigner.from_file(
            "/mnt/secrets/AID_EDGE_SIGNING_KEY",
            key_id="edge-litellm-poc-0-2026-10",
        ),
    )
)

record = emitter.emit(event, stream_id="litellm/decision")
```

- `emit(event, stream_id=None)` takes a **pre-chain** event: a 6003 dict with
  no `attestation_list`, no `metadata.uid`, no stream stamps and no signature
  fields. It returns the final signed record and has already appended
  it to the spool. It is synchronous and thread-safe.
- `await emitter.aemit(...)` is `asyncio.to_thread(emit, ...)` for async hosts.
  No await happens under the chain lock.
- `stream_id=None` emits without stream stamps. Hosts that have a decision
  stream (every adapter we plan) always pass one; the no-stamp path exists for
  the dispatch-record vector replay (section 10, T1).
- `EmitterConfig(vocabulary="aid")` is the default; `"cpex"` exists for
  CPEX-family hosts and for the vector replay (section 4.1).
- The library never raises into the host on spool or ship problems. It raises
  `EmitterValueError` only for a malformed pre-chain event (a programmer error
  in the adapter), and the adapter MUST catch it (section 7).

### 4.1 Vocabulary

AID-EMIT-1 1.1.2 pins its `unmapped` field names to the CPEX host family
(section 1.1). This library targets the AI Identity platform and OCSF, not a
particular gateway, so its default is an AI Identity vocabulary, proposed for
AID-EMIT-1 as a 1.2.0 vocabulary profile: the signing, chain and stream rules
are unchanged, only the names differ.

The rule for every field: if OCSF 1.9.0 has a native home, use it, and never
duplicate it under `unmapped`. Only facts with no native home use the
vocabulary:

| Fact | `aid` vocabulary (default) | `cpex` vocabulary |
|---|---|---|
| Stream stamps | `unmapped."aid.stream"` | `unmapped."cpex.stream"` |
| Decision steps and verdict | `unmapped."aid.decision"` | `unmapped."cpex.decision"` |
| Settlement join key | `unmapped."aid.request_id"` | `unmapped."cmf.request.request_id"` |
| Invocation span | `unmapped."aid.span"` | `unmapped."cpex.span"` |
| Content provenance | `unmapped."aid.content"` | `unmapped."cpex.content"` |
| Host-specific gap fields | `unmapped."aid.<host>.*"`, e.g. `aid.litellm.deployment` | host-defined |

The structure inside each member is identical across vocabularies, so a
verifier needs only the name map. A consumer that reads stream stamps (the AI
Identity ingest endpoint, `scripts/aid_emit1_validator.py`) has to accept
`aid.stream` as well as `cpex.stream` before an `aid` emitter ships.

## 5. The emit step (normative for this library)

All of the following happens under one `threading.Lock`, so allocation,
predecessor read and chain advance are atomic (AID-EMIT-1 section 6,
"Concurrency"):

1. **Value-space check.** Reject non-ASCII keys and any `float` (section 4).
   Also reject integers outside +/-(2^53 - 1). That is stricter than the
   validator, which only rejects floats, and it is the safe reading of
   "representable per RFC 8785's ES6 rules": Python serializes large ints
   exactly, an RFC 8785 implementation in JavaScript would not.
2. **Allocate.** `stream_seq = counters[stream_id]` (starts at 0 in every
   epoch), `emission_seq` (starts at 0 in every epoch), and the record ordinal.
3. **Identity.** `metadata.uid = f"{chain_uid}-{epoch}-{ordinal:06d}"`,
   attestation uid `f"{chain_uid}-{epoch}-att-{ordinal:06d}"`. The epoch is in
   the uid on purpose; see section 11, finding 1.
4. **Stamp.** Add `"record_integrity"` to `metadata.profiles`, set the
   vocabulary's stream member (`unmapped."aid.stream"` by default) to
   `{epoch, stream_id, stream_seq, emission_seq}`,
   and set `attestation_list[0]` = `{uid, chain_uid, authority_uid,
   prev_event?}`, where `prev_event` is `{uid, type_uid, fingerprint}` of the
   current head and is absent only on a true genesis record.
5. **Hash and sign.** Covered bytes per section 4; SHA-256 lowercase hex;
   ECDSA P-256 over the DSSE PAE with payload type
   `application/vnd.ocsf.event+json`, `deterministic_signing=True` (RFC 6979),
   DER, base64.
6. **Envelope.** Attach the fingerprint object (`algorithm_id 3`,
   `encoding_id 1`, `serialization_id 2`), the signature descriptor
   (`algorithm_id 3` ECDSA, `serialization_id 5` DSSE), and
   `unmapped.signature_b64` / `unmapped.signature_key_id`.
7. **Advance.** The head becomes this record and the counters stay consumed,
   **before** the spool write.
8. **Append** one line to the spool and flush. The fsync policy is configurable
   (`always` | `interval`, default `interval` at 250 ms).

Why the head advances before the write: if the append fails, the record still
existed, signed, and may be partly on disk. Making the next record claim the
earlier one as predecessor would be a false statement. The cost is that a lost
write surfaces at ingest twice: as a `stream_seq` gap and as a chain
discontinuity. Both are true, and the spec says to surface loss, not to tidy it.
A failed append also increments `aid_emit_spool_write_failures_total` and logs
at ERROR.

Set-derived arrays (roles, groups, labels) are the adapter's responsibility to
sort (section 3 of the spec). The `ocsf.py` builders sort everything they build.

## 6. Epoch, restart and the spool

- **Epoch** = Unix time at process start in whole seconds, times 10^9. That is
  the same unit as the reference host (nanoseconds), and a whole-second value
  in nanoseconds needs about 52 significant bits, so it stays exactly
  representable as an IEEE double, inside the RFC 8785 value space. A
  full-precision `time.time_ns()` would not. If the computed epoch is not
  greater than the last epoch recorded in `spool_dir/state.json`, use
  `last + 10^9`, so two restarts in the same second, or a clock step backward,
  still produce a strictly newer epoch.
- **Counters** reset to 0 in each epoch, as section 7 requires.
- **Chain head** is recovered at start from the last complete line of the
  current spool segment. The chain continues across restarts, so ingest sees
  one chain with epoch boundaries, not a re-anchor per restart.
- **Torn tail.** A crash mid-write leaves a partial final line. Recovery
  truncates to the last newline and logs the byte count. **Known blind spot:**
  the record on that torn line is lost, and nothing on the wire says so. The
  new epoch resets the counters, and the next record chains to the last
  complete one, so ingest sees a clean boundary. Closing this needs an emitter
  lifecycle record ("recovered a torn tail of N bytes"), which is the same open
  item as AID-EMIT-1 section 13's `on_effect` lifecycle events. Proposed as an
  open question, not solved here.
- **Spool loss.** If `spool_dir` is lost (an emptyDir on a rescheduled pod),
  the next record is a genesis record, and ingest records
  `chain re-anchored: missing prev_event`. That is the correct report. Use a
  persistent volume in production; for the POC, expect re-anchors on reschedule.
- Segments rotate at a size cap. The shipper deletes a segment only after every
  record in it has a 202 result.

## 7. Process model

One `Emitter` per `chain_uid` per process. Two processes on one chain fork it:
both read the same head, and ingest reports a discontinuity on every
interleaving. The ingest endpoint also binds each `chain_uid` to exactly one
edge registration (`chain_uid` is globally unique).

Supported shapes:

- **In-process, single worker** (POC). The host runs one worker; the emitter
  and shipper are threads in it. The signing key is readable by the host
  process.
- **Sidecar emitter** (recommended for production). A small daemon per pod owns
  the key, chain, spool and shipper; host workers send pre-chain events over a
  Unix socket. Any number of workers, one chain per pod, and the signing key
  leaves the host process. Same library; the daemon is about 100 lines on top
  of `Emitter`.

Either shape gives **one chain per pod**, which means one edge registration per
pod. That is fine for a StatefulSet with stable names, and awkward for an
autoscaled Deployment. See open question 3 in the LiteLLM outline.

Observation-only (AID-EMIT-1 section 10): an adapter wraps every call into the
library in `try/except Exception`, counts the failure, and returns. An emitter
problem never fails or alters a host request. Enforcement, where an adapter has
any, is a separate component with its own fail-closed rule.

## 8. Shipper

- Tails the spool and sends NDJSON batches within the ingest endpoint's batch
  limits. Auth is `Authorization: Bearer aid_edge_...`, with
  the key read from a mounted file.
- At-least-once. Per-record results on the 202: `verified` and `duplicate`
  advance the offset. `quarantined` also advances it, because retrying a record
  that fails verification cannot fix it, but it logs at ERROR and increments
  `aid_emit_quarantined_total`. In this library a quarantine means a
  canonicalization bug, a key mismatch or a chain_uid mismatch, and should page.
- Network errors and 5xx: exponential backoff with jitter, capped at 60 s. The
  spool grows meanwhile; `aid_emit_spool_bytes` is exported for alerting.
  Records are never dropped to bound the spool. A full disk is an alert, not a
  silent drop.
- The shipper never blocks `emit()`.

## 9. Dependencies and supply chain

- `cryptography` is the only third-party runtime dependency. RFC 8785 is
  implemented in-tree (about 10 lines), because for this format's value space
  it is exactly sorted, compact `json.dumps`. This is the same equivalence the
  reference emitter and the validator rely on; a general JCS package adds a
  dependency for cases the format forbids.
- Publish with trusted publishing and build provenance (PyPI attestations), so
  the evidence library has verifiable provenance itself.

## 10. Conformance plan

**Feasibility, checked 2026-10-12.** A Python script re-derived the covered
bytes, the SHA-256 fingerprint and the RFC 6979 DSSE signature for both signed
records in `integrations/cpex-ocsf-audit/SAMPLE-OUTPUT.md`. It used stdlib
`json`, `cryptography` 50.0.1 with `deterministic_signing=True`, and the demo
scalar `0x42 * 32` that `examples/emit_sample.rs` generates at runtime. Result:
fingerprint and signature byte-identical for both records. To re-run it:

```bash
python3 scripts/aid_emit_py_vector_check.py integrations/cpex-ocsf-audit/SAMPLE-OUTPUT.md
```

Tests the library ships with:

| ID | Test | Passes when |
|---|---|---|
| T1 | Vector replay | Each `SAMPLE-OUTPUT.md` record, stripped of attestation, uid and signature fields and re-emitted with the vector's chain_uid, authority, key id and an injected uid source, is byte-identical to the vector. |
| T2 | Validator | Every record the library emits passes `scripts/aid_emit1_validator.py --strict-gaps`. |
| T3 | Negative cases | `verify_chain` rejects a flipped payload byte, a reordered record, a swapped `authority_uid` and a renumbered `stream_seq` (the section 12 verifier cases). |
| T4 | Concurrency | 32 threads x 1000 emits: one unforked chain, no duplicate uids, dense `stream_seq` per stream. |
| T5 | Restart | Kill between emits, restart: new strictly greater epoch, counters at 0, head recovered, no duplicate uid, validator clean. |
| T6 | Torn tail | Truncate mid-line, restart: recovery truncates and logs; the blind spot in section 6 is asserted, so a future lifecycle record changes this test on purpose. |
| T7 | Ingest round trip | Records posted to `POST /api/v1/audit/ingest` for a registered test edge come back all `verified`, with no anomalies except where a test deliberately loses a record. |

T1 needs the uid source to be injectable, because the reference vector uids are
`{chain_uid}-{seq:06}` without an epoch, and it runs under the `cpex`
vocabulary, because that is what the vectors use. The library defaults are the
epoch-scoped uid in section 5 and the `aid` vocabulary in section 4.1. T7 needs
the ingest endpoint to read `aid.stream` (section 4.1).

## 11. Findings while drafting

1. **The reference emitter's uids repeat after a restart.** `cpex-ocsf-audit`
   mints `metadata.uid` as `{chain_uid}-{seq:06}` from an
   in-memory counter that starts at 0 in every process (`src/emitter.rs`,
   `wrap_in_chain`). `chain_uid` is fixed per deployment, so a restarted
   emitter re-mints uids it already used on the same chain. AID-EMIT-1
   section 6 says `metadata.uid` MUST be unique within the chain, so this is
   a conformance gap in the reference emitter. It matters because section 6
   also tells consumers to deduplicate on `metadata.uid`: a consumer that
   treats any uid match as a replay drops every post-restart record until
   the counter passes the old maximum. Two changes:
   - **Reference emitter:** scope the uid by epoch, as this library does
     (section 5). The uid is inside the hashed bytes, so the vectors change.
     Uid format is not normative, so this is a vector regeneration, not a
     spec MAJOR, but the changelog should call it out.
   - **Consumers:** dedupe only an *identical* replay, as section 6 words
     it: a uid match is a duplicate only when the fingerprint matches too. A
     uid match with a different fingerprint is a collision, which is new
     evidence to verify, store and flag. Consider stating this explicitly in
     section 6 rather than leaving it to the word "identical".
2. **The validator does not bound integer magnitude.** It flags floats only.
   Consider a warning for integers outside +/-(2^53 - 1), with the section 4
   wording as the reason.
