# Forensic attestation format (v1)

**Status:** Draft — locks the signed payload format for Milestone #33.
**Owner:** CTO
**Last reviewed:** 2026-04-17

A **forensic attestation** is a cryptographically signed statement that AI
Identity issues at session close. It commits to a specific range of audit
log entries so a third party — an auditor, a customer's compliance team,
a regulator — can verify after the fact that the chain has not been
tampered with, without having to operationally trust AI Identity.

This document defines the v1 wire format. It does *not* cover the
signing pipeline (#263), the retrieval API (#264), public key
distribution (#265), CLI verify (#266), or the trust model (#267) —
those ship as separate work and consume this format.

## Goals

1. **Third-party verifiable** — with nothing more than (a) the published
   public key, (b) the audit log rows for the committed range, (c) the
   org's HMAC verify key, a verifier can answer "did AI Identity sign
   this chain, and does it match what I have?" — offline, no API calls.
2. **Stable canonical bytes** — the signed payload must hash the same
   way on every machine, every Python version, every JSON library. A
   signature that fails on round-trip is worse than no signature.
3. **Forward-compatible schema** — a v2 verifier must be able to read a
   v1 attestation, and a v1 verifier must fail *loudly* (not silently
   accept) when it sees a v2. `schema_version` is the gate.
4. **Envelope is a standard, not a snowflake** — we use DSSE
   ([Dead Simple Signing Envelope][dsse]) so existing tooling (`cosign`,
   in-toto verifiers, the sigstore ecosystem) can validate our
   attestations without bespoke code.

[dsse]: https://github.com/secure-systems-lab/dsse/blob/master/envelope.md

## Non-goals

- **We do not re-hash the audit chain.** The existing HMAC chain
  (see [`common/audit/writer.py`](../../common/audit/writer.py)) already
  produces a tail `entry_hash` that transitively commits to every prior
  row via `prev_hash` linkage. The attestation simply *captures* that
  tail hash and signs over it.
- **We do not bundle the audit rows into the attestation.** The
  attestation is small (~500 bytes signed) and points at the rows by ID
  range. Bundling would inflate storage for no added guarantee — the
  verifier must still walk the chain to verify the committed hash.
- **We do not model a `Session` table here.** `session_id` is an
  opaque producer-supplied identifier. How sessions come to exist
  (explicit DB table, derived from agent_id + time window, etc.) is
  decided in #263.

## The payload

The signed content is a JSON object with these fields, **all required**:

| Field                 | Type              | Notes                                                                                             |
|-----------------------|-------------------|---------------------------------------------------------------------------------------------------|
| `schema_version`      | integer           | `1` for this format. A verifier MUST reject a version it does not understand.                     |
| `session_id`          | string (UUID)     | Opaque producer identifier for the session being attested.                                        |
| `org_id`              | string (UUID)     | The org whose HMAC key was used to build the audit chain. Needed for downstream chain verification. |
| `evidence_chain_hash` | string (hex)      | The `entry_hash` of the **last** audit log row in the committed range. 64 hex chars (SHA-256).     |
| `first_audit_id`      | integer           | First `audit_log.id` included in the committed range (inclusive).                                  |
| `last_audit_id`       | integer           | Last `audit_log.id` included in the committed range (inclusive). Its `entry_hash` == `evidence_chain_hash`. |
| `event_count`         | integer           | Number of audit rows in the range (`last_audit_id - first_audit_id + 1` if contiguous).             |
| `session_start`       | string (RFC 3339) | UTC, `Z` suffix (e.g. `2026-04-17T13:42:00Z`). Start of the session window.                       |
| `session_end`         | string (RFC 3339) | UTC, `Z` suffix. End of the session window (and the point at which the attestation was issued).    |
| `signed_at`           | string (RFC 3339) | UTC, `Z` suffix. The wall-clock time the signer produced the signature.                           |
| `signer_key_id`       | string            | Fully-qualified KMS key-version resource name. See below.                                          |

### `signer_key_id` format

We use the full GCP KMS key-version resource path as the key id:

```
projects/{PROJECT}/locations/{REGION}/keyRings/{KEYRING}/cryptoKeys/{KEY}/cryptoKeyVersions/{VERSION}
```

This is stable across key rotations (old versions stay enabled for
historical verification) and is directly consumable by the JWKS endpoint
defined in #265.

### Example payload (unsigned)

```json
{
  "schema_version": 1,
  "session_id": "b8f2c1a0-4e6d-4e2a-9f1a-3c2b0d4e8f7a",
  "org_id": "f1e2d3c4-b5a6-4798-8877-66554433abcd",
  "evidence_chain_hash": "3b7e0a6f4a9d8c2e5b1f0d3c6a8b9e2d1f4c7a0b3d6e9f2a5c8b1d4e7a0b3c6d",
  "first_audit_id": 104821,
  "last_audit_id": 104827,
  "event_count": 7,
  "session_start": "2026-04-17T13:42:00Z",
  "session_end": "2026-04-17T13:47:30Z",
  "signed_at": "2026-04-17T13:47:30Z",
  "signer_key_id": "projects/project-8bbb04f8-fda8-462e-bc2/locations/us-east1/keyRings/ai-identity-forensic/cryptoKeys/session-attestation/cryptoKeyVersions/1"
}
```

## Canonical serialization

**JCS — JSON Canonicalization Scheme ([RFC 8785][rfc8785])**.

The Python implementation uses the `rfc8785` package. Canonicalization
is deterministic (sorted keys, no insignificant whitespace, canonical
number format, NFC-normalized strings) so the same payload always
produces the same bytes, on any conforming implementation.

[rfc8785]: https://www.rfc-editor.org/rfc/rfc8785

Why not `json.dumps(..., sort_keys=True, separators=(",", ":"))` (which
is what the existing HMAC audit chain uses)? — Two reasons:

1. **Third-party verifiers** will expect JCS. Auditors verifying an
   attestation from Python/Go/Rust/JS should each get the same bytes.
2. **Edge cases.** Unicode escape forms, number formats (`1.0` vs `1`),
   and negative zero are not canonicalized by `sort_keys`. Our payload
   schema is tight enough that it wouldn't hit these cases in practice
   today, but hardcoding a brittle choice into a signed format is
   exactly the kind of decision that comes back to bite.

The HMAC audit chain keeps its existing sort-keys scheme — it's a
separate layer and changing it would break every existing row. JCS
applies only to the attestation envelope.

## Signing algorithm

**ECDSA with curve P-256 and SHA-256** — matches the KMS key algorithm
`EC_SIGN_P256_SHA256` provisioned in #261.

- **Signature encoding:** ASN.1 DER (as returned by GCP KMS
  `AsymmetricSign`). DSSE base64-encodes the DER bytes for transport.
- **Public key format:** PEM `SubjectPublicKeyInfo` (the format GCP KMS
  `GetPublicKey` returns).

## Envelope (DSSE)

The signed attestation is delivered as a DSSE envelope:

```json
{
  "payloadType": "application/vnd.ai-identity.attestation+json",
  "payload": "<base64(canonical-json-of-payload)>",
  "signatures": [
    {
      "keyid": "projects/.../cryptoKeys/session-attestation/cryptoKeyVersions/1",
      "sig": "<base64(DER-encoded ECDSA signature)>"
    }
  ]
}
```

### Pre-Authentication Encoding (PAE)

Per the DSSE spec, the bytes that get signed are NOT the payload bytes
directly — they are the Pre-Authentication Encoding:

```
PAE(type, body) = "DSSEv1" SP LEN(type) SP type SP LEN(body) SP body
```

Where `SP` is a single ASCII space (`0x20`) and `LEN(x)` is the ASCII
decimal representation of the byte-length of `x`. All strings are
UTF-8. Both `type` and `body` are included length-prefixed to prevent
a signature produced over one (type, body) from being replayed as
valid over a different (type', body') where the concatenations happen
to collide. This is the whole point of PAE: domain separation at zero
additional cryptographic cost.

## Verification algorithm

A verifier with access to (a) the DSSE envelope, (b) the signer's
public key PEM, (c) the audit log rows for `[first_audit_id,
last_audit_id]`, and (d) the org's HMAC verify key performs the
following, failing closed on any mismatch:

1. **Parse the envelope.** Confirm `payloadType ==
   "application/vnd.ai-identity.attestation+json"`. Base64-decode
   `payload` to get the canonical JSON bytes, parse to a dict.
2. **Schema check.** Confirm `schema_version == 1`. Reject any
   unexpected version — a verifier that silently accepts unknown
   versions defeats the purpose of versioning.
3. **Signature check.** Reconstruct `PAE(payloadType, payload_bytes)`,
   compute its SHA-256, verify the DER-encoded ECDSA signature against
   the public key. On failure → REJECT.
4. **Chain check.** Walk the audit log rows in the committed range and
   compute the HMAC chain as described in
   [`common/audit/writer.py`](../../common/audit/writer.py):`verify_chain`.
   The last row's computed `entry_hash` MUST equal
   `evidence_chain_hash` in the payload. On failure → REJECT.
5. **Range sanity.** `event_count == last_audit_id - first_audit_id +
   1` AND every row in the range has the claimed `org_id`. On failure
   → REJECT.

If all five pass, the attestation is **valid**. This means: AI
Identity committed to this exact set of audit rows at `signed_at`
using the key identified by `signer_key_id`, and the rows have not
been tampered with since.

## Key rotation & historical verifiability

KMS asymmetric signing keys are rotated operator-triggered (see
[`scripts/setup-forensic-signer.sh`](../../scripts/setup-forensic-signer.sh) —
no scheduled rotation for asymmetric keys). Old `cryptoKeyVersions/N`
stay in state `ENABLED` so their public keys remain resolvable.

The JWKS endpoint defined in #265 publishes **all** historical key
versions with their `created_at` / `not_before` / `not_after` metadata,
so a verifier processing an attestation signed five years ago can
still fetch the exact public key that signed it.

**This is why `signer_key_id` pins the specific version, not just the
key.** A key_id of `.../cryptoKeys/session-attestation` would be
ambiguous after the first rotation.

## What this format does NOT prove

Worth being explicit — an attestation is a claim about audit log
integrity, nothing more:

- It does **not** prove the events themselves were "correct" — only
  that they were recorded and not subsequently altered.
- It does **not** prove the *agent* did anything in particular — it
  proves the *gateway* saw a specific sequence of allow/deny decisions.
- It does **not** prove timing within the session; `session_start`
  and `session_end` are producer-reported.
- It does **not** cover events outside the `[first_audit_id,
  last_audit_id]` range, even if they belong to the same `session_id`.

These boundaries get expanded in the trust-model doc (#267) for an
audit-ready audience.

## Open questions (resolved in follow-on sprint items)

- **Session lifecycle** — when does a session close, and who calls the
  signer? → #263
- **Retrieval API shape** — REST endpoint, auth, query params. → #264
- **Public key distribution** — JWKS endpoint URL, rotation metadata. → #265
- **CLI UX** — `ai-identity verify-attestation <file>` flags and exit codes. → #266
- **Trust model prose for auditors** — what to show a SOC 2 auditor, emergency rotation runbook. → #267
