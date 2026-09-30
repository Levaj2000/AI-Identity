# AI Identity Case File bundle format (v1)

**Status:** Implemented. The verifier side shipped in CLI 1.6.0: the
`bundle` command, the standalone-command rules and the online witness check
(section 10.2). The platform side (section 10.1) shipped on 2026-09-30: the
bundle endpoint signs `manifest.json` and embeds CLI 1.6.0, and the README and
`verify.command` run `bundle`. An export whose scope carries no org still has
no manifest and reads as pre-v1 (section 8.2), as do all bundles issued
before that date.
**Owner:** CTO
**Last reviewed:** 2026-09-30

"Self-contained exports" appears in product and strategy copy, but until now it
has not been defined precisely enough to test. This document is the contract
that makes it testable. It:

1. Defines the Case File ZIP that `GET /api/v1/audit/report/bundle` returns,
   and the format of each artifact inside it (sections 3 to 6).
2. Defines "self-contained" as a checkable property, not an adjective
   (section 2).
3. Defines the ordered, fail-closed procedures a third party runs against a
   bundle, and what each one establishes (sections 7 and 9).
4. Names the boundary: which checks need only public tools, which need a
   secret, which need the network, and which no third party can run at all.

Companion documents, all in `docs/forensics/`:

- [`attestation-format.md`](attestation-format.md): the DSSE session-attestation wire format
- [`trust-model.md`](trust-model.md): what a valid attestation proves and does not prove
- [`retention-tombstones-in-exports.md`](retention-tombstones-in-exports.md): the `retention/tombstones.json` contract
- [`evidence-anchor-reference-notes.md`](evidence-anchor-reference-notes.md): the checkpoint and inclusion-proof formats
- [`evidence-anchor-public-feed.md`](evidence-anchor-public-feed.md): the public checkpoint feed and mirror
- [`key-rotation.md`](key-rotation.md): signer key versions and the JWKS

## 1. The two chains and why they matter here

Every audit row carries two HMAC chains (see `trust-model.md`):

| Field pair | Chain | Key | Who holds the key |
|---|---|---|---|
| `entry_hash` / `prev_hash` | platform chain | `AUDIT_HMAC_KEY` | AI Identity only (runtime configuration, never in the database) |
| `entry_hash_org` / `prev_hash_org` | per-org chain | the org's `forensic_verify_key` (plus retired epoch keys) | the org's admins, via the dashboard |

The evidence-anchor Merkle leaf is `entry_hash`, the **platform-chain** hash.
Nobody outside AI Identity can recompute it from a row's content. This one fact
shapes the whole spec: an inclusion proof shows that a 32-byte value was
committed under a signed root, and on its own says nothing about what the row
beside it contains. Section 9.3 states the consequence; the signed manifest
(section 4) is how v1 binds content to something a stranger can check.

## 2. What "self-contained" means (normative)

**Definition.** A Case File bundle is *self-contained* iff a verifier holding
**only** the bundle file and **public tools** can establish every Tier P claim
in section 9.1, with **zero network calls** and **zero secrets**.

**Public tools** means: a Python 3.9+ interpreter, the `cryptography` package
from PyPI (needed for ECDSA verification), and the published JWKS
(`/.well-known/ai-identity-public-keys.json`) or a copy saved at collection
time (section 7.6). "Public" does not mean "dependency-free".

**Three tiers.** The bundle carries independent integrity layers with different
trust inputs. The tiers are reported separately, never blended (section 7.5):

| Tier | Name | Checks | Inputs | Network | Secrets |
|---|---|---|---|---|---|
| **P** | Public | Manifest signature and inventory; checkpoint signatures; inclusion proofs bound to exported rows; as-issued org-slice structure; tombstone accounting | Bundle + JWKS | None | None |
| **K** | Key-holder | Per-row HMAC recomputation on the org chain; report signature | Bundle + org verify key(s) | None | `forensic_verify_key` and retired epoch keys |
| **W** | Witness (optional) | Every checkpoint the bundle relies on appears, byte-identical, in the public feed or mirror | Bundle + network | Public feed or mirror | None |

Each tier fixes the evidence at a different moment:

- **Tier P** fixes the bundle at **issuance**: every file is byte-identical to
  what the platform signed at `generated_at`. It also fixes anchored hashes at
  **anchoring** time.
- **Tier K** fixes each row's content at **write** time, for rows written under
  a key the holder has.
- **Tier W** shows the checkpoints were **public**, so the holder was not shown
  a private fork.

Tier K is key-holder verifiable, not publicly verifiable: the HMAC verify key
is also a forge key. "Self-contained" therefore always means Tier P. Tier W is
a network call to AI Identity infrastructure (the feed) or its GitHub
organization (the mirror), so it sits outside the definition above: it
strengthens a result and is never required for one.

**The disappearance test.** Suppose AI Identity (the company, the API, the
JWKS endpoint, the dashboard) vanished tomorrow. Then:

- A bundle plus a saved JWKS still verifies at **Tier P**, in full. A stranger
  can establish that the bundle is exactly as issued, that its anchored hashes
  were committed under signed roots, and that the as-issued org slice is
  structurally complete with every pruned row accounted for.
- **Tier K** still verifies iff the org verify key(s) were saved with the
  bundle, and only for rows written under an org key. Rows written under the
  platform key before the org key existed are beyond Tier K permanently.
- **Tier W** degrades to the GitHub mirror, if it survives, or to the Tier W
  result recorded at collection time (section 7.6).
- **What does not survive:** platform-chain verification, which is
  recomputing `entry_hash`. After disappearance nobody can run it, so the
  protection `trust-model.md` describes ("a re-forged org chain still fails
  platform-chain verification") is gone. The signed manifest covers the case
  it covered after issuance (section 9.3).

## 3. Bundle layout (normative)

`GET /api/v1/audit/report/bundle` returns a ZIP named
`ai-identity-case-file-<short>-<date>.zip` with this layout:

```
ai-identity-case-file-<short>-<date>.zip
  manifest.json                     signed manifest (section 4)
  case-file-<short>-<date>.json     forensic report (section 5.1)
  ai_identity_verify.py             embedded verifier (section 5.5)
  verify.command                    macOS runner, mode 0755 (section 5.6)
  README.md                         human verification guide (section 5.6)
  evidence-anchor/                  present iff >= 1 exported event is anchored
    checkpoints.json                signed Merkle checkpoints (section 5.2)
    inclusion-proofs.json           per-event proofs and pending list (section 5.3)
  retention/                        present iff >= 1 row in the id range was pruned
    tombstones.json                 tombstones, receipts, cited checkpoints (section 5.4)
```

Layout rules:

- **The verifier MUST be embedded.** A bundle without its verifier is
  unverifiable by the people most likely to receive it. The builder MUST fail
  loudly (HTTP 500, never a silent omission) if `cli/ai_identity_verify.py` is
  unavailable at build time. This is current behavior; the spec locks it in.
- **The manifest MUST be signed.** The builder MUST fail loudly (HTTP 500) if
  the manifest cannot be signed. An unsigned v1 bundle is never issued.
- **Every file is inventoried.** Every file in the ZIP except `manifest.json`
  itself appears exactly once in `manifest.files`. An extra file or a missing
  file is a REJECT.
- **Empty optional folders MUST NOT ship.** Absence is meaningful: no
  `retention/` folder means no row in `[first_audit_id, last_audit_id]` has a
  tombstone, and no `evidence-anchor/` folder means no exported event is
  anchored yet. In v1 the absence is authenticated, because the signed
  inventory (and `manifest.counts`) says what should be there. Deleting a
  folder from a v1 bundle is a REJECT, not a downgrade.
- **Coverage MUST be explicit.** When `evidence-anchor/` is present, every
  exported event id appears in exactly one of `proofs[].audit_id` or `pending`.
  A verifier MUST NOT infer completeness from silence.
- **Filenames are fixed** except the case file. A v1 verifier locates it by
  its manifest `role` (`report`); a pre-v1 verifier locates it by the glob
  `case-file-*.json`, as `verify.command` does. Never by a hardcoded name.
- **ZIP hygiene.** Entry paths MUST be relative, MUST NOT contain `..`
  segments, and MUST NOT be symlinks or duplicates. A verifier MUST reject a
  ZIP that violates any of these before extracting anything.
- **Extracted directories.** A verifier MAY accept the directory a bundle was
  extracted into. The same inventory rule applies, except that desktop
  metadata files named `.DS_Store` are ignored, because opening the folder is
  enough to create one. Symlinks in the directory are a REJECT.

## 4. `manifest.json` (signed)

`manifest.json` is a DSSE envelope, in the same shape as a checkpoint or
attestation envelope:

```json
{
  "payloadType": "application/vnd.ai-identity.case-file-manifest+json",
  "payload": "<base64(JCS-canonical manifest JSON)>",
  "signatures": [{"keyid": "<kms-key-version-path>", "sig": "<base64(DER ECDSA-P256)>"}]
}
```

The decoded payload:

```json
{
  "schema_version": 1,
  "format": "ai-identity-case-file/v1",
  "bundle_id": "9f2c...",
  "generated_at": "2026-09-29T15:04:11Z",
  "generator": "ai-identity-platform/0.5.0",
  "signer_key_id": "<kms-key-version-path>",
  "org_id": "0f2c...",
  "scope": {"type": "org", "org_id": "0f2c..."},
  "range": {"first_audit_id": 48151000, "last_audit_id": 48155999},
  "counts": {"events": 4990, "anchored": 4800, "pending": 190, "tombstoned": 10},
  "verifier_version": "x.y.z",
  "files": [
    {"path": "case-file-0f2c-2026-09-29.json", "sha256": "...", "role": "report"},
    {"path": "ai_identity_verify.py", "sha256": "...", "role": "verifier"},
    {"path": "verify.command", "sha256": "...", "role": "runner"},
    {"path": "README.md", "sha256": "...", "role": "readme"},
    {"path": "evidence-anchor/checkpoints.json", "sha256": "...", "role": "checkpoints"},
    {"path": "evidence-anchor/inclusion-proofs.json", "sha256": "...", "role": "proofs"},
    {"path": "retention/tombstones.json", "sha256": "...", "role": "tombstones"}
  ]
}
```

Rules:

- **Signature.** ECDSA P-256 over SHA-256, DER-encoded, base64 in the envelope,
  over `PAE(payloadType, payload)`. It is made by a KMS forensic-signer key
  published in the JWKS, resolved by `keyid`, and there is exactly one
  signature. PAE binds the `payloadType`, so a manifest signature cannot be
  replayed as a checkpoint or attestation signature, even from the same key.
- **Verify the bytes received.** The signature covers the base64-decoded
  `payload` bytes exactly as shipped. A verifier MUST NOT re-canonicalize
  before verifying, and MUST NOT act on any payload field before the signature
  verifies.
- **Versions.** A verifier MUST reject `schema_version` other than `1` and any
  `format` it does not understand. It must fail loudly, never accept silently.
- **Inventory.** `files[].sha256` is the lowercase hex SHA-256 of the file's
  uncompressed bytes. Exactly one file has role `report` and exactly one has
  role `verifier`. Roles `checkpoints`, `proofs` and `tombstones` are present
  iff their folders are.
- **Cross-binding.** The manifest's `org_id`, `scope` and `range` MUST equal
  the case file's. The case file's `range` is `[min(id), max(id)]` over its
  events, or `null` when there are none. Every checkpoint payload's `org_id`
  MUST equal the manifest's. `retention/tombstones.json`'s `org_id` and `range`
  MUST equal the manifest's. Any mismatch is a REJECT.
- **Counts.** `counts.events` is the number of exported events.
  `counts.anchored` and `counts.pending` are the lengths of `proofs` and
  `pending`, and they sum to `counts.events`. Without `evidence-anchor/`,
  `counts.anchored` is 0 and every event is pending. `counts.tombstoned` is
  the number of tombstones shipped, 0 without `retention/`. Each MUST equal
  what the verifier counts.
- **Scope.** `scope.type` is one of `org`, `agent` or `incident`. Any other
  value is a REJECT: a verifier that guesses the scope guesses the
  completeness rule (section 7.1 step 6).

**What the signature establishes:** every file in the bundle is byte-identical
to what the platform issued at `generated_at`. That includes the case file's
events, the proofs, the tombstones, and the embedded verifier. It does not
establish that the content was correct when issued (section 9).

## 5. Artifacts

### 5.1 `case-file-*.json`: the forensic report

The platform's forensic report for the export scope. It holds the audit rows
(`events`), the scope, the chain-verification result the platform computed at
export time, and the report signature.

- **Events.** Each row carries:
  - `id`: the audit id
  - `entry_hash` and `prev_hash`: platform chain; `entry_hash` is the Merkle leaf
  - `entry_hash_org` and `prev_hash_org`: per-org chain
  - `org_chain_seq`
  - `key_fingerprint`: the first 16 hex characters of SHA-256 of the HMAC key
    that hashed the row; absent on legacy rows
  - the payload fields listed in section 6.
- **Scope.** The `scope` object: `type`, `org_id`, and `agent_id` or the
  incident id as applicable.
- **Chain verification block.** `chain_verification` (or the same fields
  flat): `chain_valid` (or `valid`), `total_entries`, `entries_verified`. This
  is the platform's claim about its own chain at export time. A verifier does
  not trust it; it recomputes (section 7.2).
- **Report signature (Tier K).** HMAC-SHA256 under the org verify key, in the
  `report_signature` field, over the canonical payload
  `{chain_valid, entries_verified, generated_at, report_id, total_entries}`
  (section 6). This mirrors `common.audit.writer.generate_report_signature`,
  and the CLI recomputes it in `_compute_report_signature`. It covers **only
  those five summary fields**. It does not cover the events, the scope, the
  org or the range; the manifest (Tier P) and the chain walk (Tier K) bind
  those.
- **Reliability statement.** `reliability_statement` is a plain-English,
  FRE 702 / Daubert-oriented account of the integrity method and its limits.
  Its wording MUST stay consistent with section 9.

### 5.2 `evidence-anchor/checkpoints.json`: signed Merkle checkpoints

`[{"merkle_root": "<hex>", "envelope": {<DSSE>}}, ...]`: one entry per
distinct checkpoint covering at least one exported event. The format is
`MerkleCheckpointV1`, specified in `evidence-anchor-reference-notes.md`
section 3:

- `payloadType` is `application/vnd.ai-identity.anchor-checkpoint+json`, with
  exactly one signature: ECDSA P-256 / SHA-256 by the KMS forensic-signer key,
  resolved by `keyid` against the JWKS.
- The payload is JCS-canonical (RFC 8785) on the producer side. Its fields are
  `schema_version` (1), `org_id`, `tree_size`, `merkle_root`,
  `first_audit_id`, `last_audit_id`, `signed_at` and `signer_key_id`.
- The key is non-extractable (KMS HSM) and asymmetric: the public key verifies
  but cannot forge. That is what makes Tier P publicly verifiable where Tier K
  is not.

### 5.3 `evidence-anchor/inclusion-proofs.json`: per-event proofs

`{"proofs": [...], "pending": [...]}`, as specified in
`evidence-anchor-reference-notes.md` section 4.

- Each proof is `{audit_id, entry_hash, index, tree_size, merkle_root,
  proof: [<hex>, ...]}`: the RFC 6962 audit path for the leaf `entry_hash` at
  `index` in a tree of `tree_size` leaves under `merkle_root`. It is
  O(log N).
- `pending` lists the `audit_id`s of exported events not yet covered by any
  checkpoint. Together with `proofs` it accounts for every exported event
  exactly once (section 3).
- `audit_id`, `index` and `tree_size` are unsigned labels. Section 7.1 step 5
  binds them to signed data where possible.

### 5.4 `retention/tombstones.json`: pruned-row receipts

The format is `ai-identity-retention-tombstones/v1`, fully specified in
`retention-tombstones-in-exports.md`. This spec incorporates it by reference
and adds four v1 rules:

- The checkpoint signature check on cited checkpoints is **mandatory** for a
  Tier P result. In 1.5.0, `chain --tombstones` makes it optional (`--jwks`).
  The cited checkpoint also passes the section 7.1 step 4 checks
  (`schema_version`, `org_id`).
- The frozen `leaves` and `audit_log_ids` have the same length, and that
  length equals the checkpoint's signed `tree_size`. Each tombstone's
  `audit_id` lies within the checkpoint's signed
  `[first_audit_id, last_audit_id]`. The frozen lists are unsigned; these
  bind them to what was signed.
- `org_id` and `range` MUST equal the manifest's.
- A tombstone whose `org_chain_seq` is also a surviving exported row is a
  contradiction, and a REJECT.

Know what the offline checks reach:

- **Receipt check.** It confirms a receipt with `event_type == "tombstone"`
  and a non-null `audit_log_id` is present. It does not confirm that the
  anchor row exists in the chain, because that row usually falls after the
  export's range.
- **`mirror_commit`.** It is informational offline, and checkable only at
  Tier W (section 7.3).

### 5.5 `ai_identity_verify.py`: the embedded verifier

The standalone verifier, open source under MIT in this repository. `report`
and `chain` (without `--tombstones --jwks`) are stdlib-only. `attestation`,
`inclusion-proof`, `chain --tombstones --jwks` and the v1 `bundle` command
also need `cryptography`.

The bundle embeds the exact version that built it: its hash is in the signed
inventory and its version is `manifest.verifier_version`.

**The embedded copy is a convenience, not a trust anchor.** A bundle's own
verifier judging that same bundle is circular. A verifier SHOULD run an
independently obtained copy of the CLI, at the same version or later, from a
tagged release of this repository. The signed inventory lets anyone confirm
the embedded copy is the one that was issued, which is useful for
reproducing a result. It does not make that copy trustworthy.

What the CLI accepts or rejects is relied on by third parties. Changes to it
need maintainer sign-off (`AGENTS.md`, "Verifier semantics") and a CHANGELOG
entry, and they are versioned per section 8.

### 5.6 `verify.command` and `README.md`

`verify.command` is a turnkey macOS runner (mode 0755). It locates the case
file, runs the verifier, and prompts for the org key, the one input the bundle
cannot ship, by design. `README.md` is the human-readable guide. Both are
convenience, not trust anchors: the procedures in section 7 are normative and
the README is their plain-English rendering.

## 6. Canonicalization and hashing (normative)

Each layer keeps the scheme it shipped with, because changing a scheme breaks
every existing signature. This spec locks the schemes; it does not unify them.

| Layer | Scheme | Used by |
|---|---|---|
| Audit entry payload (both chains) | Python `json.dumps(payload, sort_keys=True, separators=(",", ":"))`, then UTF-8 | Tier K chain walk; platform chain |
| Report signature payload | Same | Tier K report check |
| Checkpoint, attestation and manifest DSSE payloads | JCS, RFC 8785 (producer side) | Tier P signature checks |
| DSSE signing input | `PAE = "DSSEv1" SP LEN(type) SP type SP LEN(body) SP body` | All DSSE verification |
| Merkle tree | RFC 6962 | Tier P inclusion and tombstone checks |
| File digests | SHA-256, lowercase hex, over uncompressed file bytes | Manifest inventory |

**Audit entry payload.** These are the exact fields. The key named `prev_hash`
carries the predecessor on whichever chain is being computed.

| Key | Value |
|---|---|
| `agent_id` | `str()` of the exported value |
| `cost_estimate_usd` | `str()` of the exported value, or `null` |
| `created_at` | the exported string with a trailing `Z` replaced by `+00:00`; no other normalization (precision, offset form and separators pass through unchanged) |
| `decision`, `endpoint`, `method` | as exported |
| `latency_ms` | integer or `null` |
| `prev_hash` | `prev_hash` for the platform chain; `prev_hash_org` for the per-org chain |
| `request_metadata` | object; `{}` when absent |

- `entry_hash = hex(HMAC-SHA256(AUDIT_HMAC_KEY, canonical))`, with the
  platform predecessor.
- `entry_hash_org = hex(HMAC-SHA256(org key for the row's epoch, canonical))`,
  with the per-org predecessor.

A non-Python implementation must reproduce Python's `json.dumps` defaults:

- keys sorted by code point
- non-ASCII characters escaped as `\uXXXX`, with surrogate pairs above U+FFFF
- floats in Python `repr` form
- no whitespace

"Close enough" parsing is a verification failure, not a compatibility feature.

**Report signature payload.**
`{chain_valid, entries_verified, generated_at, report_id, total_entries}`. It
is serialized the same way, with the same `Z` rule applied to `generated_at`.

**Merkle tree (RFC 6962 section 2.1).**

```
leaf_hash(d)    = SHA-256(0x00 || d)          d = bytes.fromhex(entry_hash), 32 bytes
node_hash(l, r) = SHA-256(0x01 || l || r)
MTH(D[0:n])     = node_hash(MTH(D[0:k]), MTH(D[k:n]))   k = largest power of 2 < n
```

Inclusion is the RFC 6962 section 2.1.1 audit-path check.

**DSSE.** Verify over `PAE(payloadType, payload bytes as decoded)`, with no
re-canonicalization (section 4).

## 7. Verification procedures (normative)

All procedures are **fail-closed**. Any mismatch is a REJECT, and the
verifier reports the first failing check together with the artifact and field
that failed. It MAY continue past that point to collect diagnostics, but the
result stays REJECT.

Each tier ends in exactly one of these outcomes:

| Outcome | Meaning |
|---|---|
| `VERIFIED` | Every applicable check passed |
| `REJECTED` | A check failed |
| `UNAVAILABLE` | An input the tier needs is absent: no key for Tier K, no network for Tier W. Never shown as VERIFIED, never counted as REJECTED |
| `PRE-V1` | Tier P only: the bundle has no manifest (section 8.2) |

### 7.1 Tier P: public verification (no secrets, no network)

Given only the bundle and the JWKS:

1. **Container.** Apply the ZIP hygiene rules (section 3). If `manifest.json`
   is absent, the bundle is pre-v1: continue per section 8.2.
2. **Manifest.** Confirm `payloadType ==
   "application/vnd.ai-identity.case-file-manifest+json"` and that there is
   exactly one signature. Resolve `keyid` in the JWKS to an EC P-256 key and
   verify the signature (section 4). Then check `schema_version` and `format`.
   Finally, confirm the inventory exactly matches the ZIP contents and every
   `sha256` matches.
3. **Cross-binding.** Check the manifest's `org_id`, `scope`, `range` and
   `counts.events` against the case file (section 4). Confirm `scope.type` is
   known.
4. **Checkpoints.** For each entry in `evidence-anchor/checkpoints.json`:
   - `payloadType` is the checkpoint type, with exactly one signature
   - `keyid` resolves in the JWKS
   - the signature verifies
   - the payload's `schema_version == 1`
   - the payload's `merkle_root` equals the entry's `merkle_root`
   - the payload's `org_id` equals the manifest's `org_id`
5. **Inclusion proofs.** For each proof:
   - Its `merkle_root` is a checkpoint that passed step 4.
   - `tree_size` equals that checkpoint's signed `tree_size`.
   - `audit_id` lies within the checkpoint's signed
     `[first_audit_id, last_audit_id]`.
   - The RFC 6962 audit path from `leaf_hash(entry_hash)` at `index`
     reproduces the root.
   - An exported event with `id == audit_id` exists, and its `entry_hash`
     equals the proof's `entry_hash`. The manifest signature makes this
     comparison meaningful: the event's `entry_hash` is the one issued.

   Then check accounting: every exported event id appears in exactly one of
   `proofs` or `pending`, and the lengths match `counts.anchored` and
   `counts.pending`. Pending events are reported as unanchored, not as
   failures.
6. **Org-slice structure.** The rule depends on `scope.type`:
   - `org` is the only completeness scope. Sort events by `org_chain_seq` and
     check two things over **stored** values. First, `org_chain_seq` is
     contiguous from first to last, except for gaps accounted for in step 7.
     Second, each row's `prev_hash_org` equals its predecessor's
     `entry_hash_org`. This proves structure as issued; recomputing the hashes
     is Tier K.
   - `agent` and `incident` scopes are sparse slices: other agents and
     unrelated activity own the intervening sequence numbers. A gap re-anchors
     the linkage check and is not evidence of deletion; retention is not
     consulted. These scopes make no completeness claim, and the verifier says
     so.
7. **Tombstone accounting** (`org` scope, at each gap). Run the algorithm in
   `retention-tombstones-in-exports.md`, "Verifier algorithm", with the v1
   rules of section 5.4. That includes the mandatory signature check on every
   cited checkpoint, applying the step 4 rules. Also check that the file's
   `org_id` and `range` match the manifest and that the number of tombstones
   equals `counts.tombstoned`. A gap with no covering tombstone, or a
   tombstone that fails any check, is an **unaccounted deletion**: REJECT,
   report it as tampering evidence, and keep the bundle.

If every step passes, the bundle is **verified at Tier P** (section 9.1).

### 7.2 Tier K: key-holder verification (org verify key, still offline)

Tier K runs after Tier P steps 1 to 3 have passed, or on a pre-v1 bundle.

1. **Org chain recompute.** For each event, pick the supplied key whose
   fingerprint matches `key_fingerprint`. For legacy rows without a
   fingerprint, accept a match under any supplied key. Recompute
   `entry_hash_org` (section 6) and compare. A row whose fingerprint matches no
   supplied key is **not covered**, which is not tampering. The structural
   checks of Tier P step 6 still apply to it. If no row is covered, Tier K is
   UNAVAILABLE, never VERIFIED.
2. **Report signature.** Recompute the section 6 report payload HMAC under the
   supplied keys and compare it with `report_signature`.
3. **Claim consistency.** Two checks against the platform's
   `chain_verification` block:
   - `total_entries` MUST equal the number of exported events.
   - A `chain_valid: false` claim is reported as a REJECT whatever the local
     result.

   `entries_verified` is reported, not compared, because the platform
   verifies under keys the holder may not have.

If all steps pass, the bundle is **verified at Tier K** (section 9.2). The
count of rows not covered travels with the result.

### 7.3 Tier W: witness check (optional, online)

For each checkpoint root the bundle relies on (step 4, plus the checkpoints
tombstones cite), query the public record. Ask the live feed first, and fall
back to the mirror only when the feed gives no usable answer (unreachable, a
5xx or other non-404 status, or an unreadable body). The fallback is what keeps
Tier W working in the disappearance case (section 2):

- the live feed: `GET https://api.ai-identity.co/evidence-anchor/checkpoints/<merkle_root>`
- the `evidence-anchor-mirror` branch of this repository: `checkpoints.ndjson`
  for the entries and `mirror-state.json` (`mirrored_at`) to date the snapshot

| Response | Result |
|---|---|
| Same root, byte-identical envelope | `WITNESSED` |
| Same root, different envelope | REJECT: split view. Report to security@ai-identity.co and keep the bundle |
| Live feed 404 for a root that verified offline | REJECT: split view (`evidence-anchor-public-feed.md` section 2) |
| Mirror lacks the root, and its `signed_at` is within one mirror interval (6 hours) of the mirror's newest snapshot | `NOT YET WITNESSED`: not a failure; re-check later |
| Mirror lacks the root, and its `signed_at` is older than that | REJECT |
| Source unreachable | UNAVAILABLE |

The tier's outcome sums these up: REJECTED if any checkpoint is a split view,
VERIFIED if every checkpoint is WITNESSED, and otherwise UNAVAILABLE, with the
counts of checkpoints not yet in the mirror and with no reachable source.

With a clone of the mirror, a verifier MAY also confirm that each tombstone
checkpoint is present at its `mirror_commit`, and that the commit predates the
tombstone's `pruned_at`. Mirror commit timestamps are set by a workflow in AI
Identity's GitHub organization, so this check raises the bar; it is not
independent proof (`evidence-anchor-public-feed.md`, limits).

### 7.4 Pre-v1 bundles

See section 8.2.

### 7.5 Result reporting

The verifier reports the tiers separately and never as a single blended
"valid":

```
Bundle:  ai-identity-case-file/v1   manifest signature VALID
Tier P:  VERIFIED     4800 anchored, 190 pending, 10 tombstoned
Tier K:  VERIFIED     4990/4990 rows under supplied keys
Tier W:  UNAVAILABLE  offline
```

- **Counts.** `valid with N tombstoned rows` MUST be distinguishable from
  `valid`, and `valid with N rows not covered` from full coverage. Counts
  travel in both human and JSON output. The JSON result carries a `tiers`
  object with each tier's outcome and counts.
- **Exit codes** for the `bundle` command:
  - `0`: Tier P VERIFIED and no tier REJECTED
  - `1`: any tier REJECTED
  - `2`: usage error
  - `3`: nothing REJECTED, but Tier P is not VERIFIED (PRE-V1)

  Existing subcommands keep their 0/1/2 codes.

### 7.6 Evidence-collection practice (normative guidance)

"Zero network calls" is measured at *verification* time, not collection time.
Whoever collects a bundle for long-term holding SHOULD, at collection:

1. Save a copy of the JWKS (`/.well-known/ai-identity-public-keys.json`) with
   the bundle. Key versions are never destroyed (`key-rotation.md`), but a
   saved copy removes even that dependency.
2. Save an independently obtained copy of the verifier CLI (section 5.5).
3. Run Tier W and keep its JSON output with the bundle, as a dated record that
   the checkpoints were in the public history when collected.
4. Save the org verify key and retired epoch keys, if Tier K must survive on
   its own. Anyone holding them can also forge Tier K, so where they are
   stored is the holder's custody decision, not the vendor's.

## 8. Versioning

### 8.1 Format and verifier versions

- **Format identifier.** The bundle format identifier is
  `ai-identity-case-file/v1`, in the manifest's `format` field. A major
  version bump is a breaking change. A verifier MUST fail loudly on an unknown
  version and never accept silently.
- **Signed envelopes.** The manifest, checkpoints and attestations each carry
  their own `schema_version`, and verifiers reject unknown values. The bundle
  format does not re-version them.
- **Unsigned artifacts.** They MAY add fields within v1, and readers MUST
  ignore fields they do not understand.
- **Verifier semantics.** A change to what the CLI accepts or rejects needs
  maintainer sign-off and a CHANGELOG entry. A change that would turn a
  conforming v1 bundle's VERIFIED into REJECTED, or the reverse, travels with
  a format version bump.

### 8.2 Pre-v1 bundles

Bundles issued before the manifest shipped have no `manifest.json`. They are
not backfilled or re-issued.

A v1 verifier reports them as `PRE-V1: bundle integrity unsigned`. It runs
Tier P steps 4 to 7 over the unsigned files, locating the case file by glob.
It reports Tier P as PRE-V1, never VERIFIED: without the manifest, nothing
binds the exported rows to the anchored hashes. Tier K runs as usual.

Two older shapes are handled the way the 1.5.0 `chain` command handles them:

- **No `scope` in the report:** treated as `org` scope, so a gap still needs
  a tombstone.
- **No per-org chain fields:** there is no org-slice structure to check. The
  result says so, and Tier K is UNAVAILABLE with a pointer to
  `chain --global`.

The existing subcommands (`report`, `chain`, `inclusion-proof`, `attestation`)
keep working on pre-v1 bundles exactly as in 1.5.0.

Stripping `manifest.json` from a v1 bundle makes it read as PRE-V1, never as
VERIFIED, so there is no downgrade to a passing result.

## 9. What a verified bundle proves, and does not prove

### 9.1 Tier P

**Proves:**

- Every file in the bundle is byte-identical to what the holder of the
  manifest signing key issued at `generated_at`.
- Each anchored event's `entry_hash` was committed under a Merkle root that
  the checkpoint's KMS key signed.
- For `org` scope, the issued slice is structurally complete: contiguous in
  `org_chain_seq`, linked by stored hashes, with every gap accounted for by a
  tombstone whose hash sits under a signed root.

**Does not prove:**

- that row content matches its anchored `entry_hash` (section 9.3)
- that the events are complete beyond the slice (see `pending` and the scope
  rules)
- that a tombstone's receipt is itself chained
- that the events are correct, or about what they claim to be about

### 9.2 Tier K

**Proves:** every covered row's content is exactly what the org key hashed at
write time, in chained order, with no insertions, deletions or modifications
since then.

**Does not prove:**

- anything about rows outside the supplied keys' epochs
- that the agent did anything in particular: rows record gateway decisions
- that a decision was correct
- timing within a session

The table in `trust-model.md` applies unchanged.

### 9.3 The link no third party can check

Nobody outside AI Identity can check that a row's content hashes to its
anchored `entry_hash`, because that takes `AUDIT_HMAC_KEY`. The three tiers
compose around the gap without closing it:

- Tier K fixes content at write time, under the org key.
- Tier P fixes the anchored hash at anchoring time, and the whole bundle at
  issuance.

What this means in practice:

- **After issuance.** Anyone editing a bundle breaks the manifest signature.
  That includes an org admin who holds the org key and re-forges the org
  chain. This is the case the signed manifest exists for.
- **Before issuance.** A party that can write rows and also holds the platform
  key is answered by the two-key custody split in `trust-model.md`, not by
  this format.
- **After disappearance.** Platform-chain verification is gone permanently
  (section 2).

Section 11 item 1 is the v2 candidate that would close the gap.

### 9.4 Neither tier proves

- anything about events outside the bundle's id range
- anything about the vendor's current state
- that AI Identity is trustworthy: only that the evidence is intact as
  described

## 10. Implementation delta

Everything below is required before any bundle is v1. The layout, checkpoint
format, tombstone format and canonicalization schemes are specified as they
exist today; the changes are these.

### 10.1 Platform (private repository)

1. **Signed `manifest.json`** per section 4, emitted by the bundle endpoint:
   one KMS sign per export, failing loudly if signing fails.
2. **Coverage accounting.** `proofs` and `pending` together account for every
   exported event exactly once, and every proof's `audit_id` lies within its
   checkpoint's signed id range. Confirm whether both already hold; if not,
   enforce them.
3. **README, `verify.command` and `reliability_statement`** invoke the
   `bundle` command and describe the tiers in section 9's terms.

### 10.2 Verifier (`cli/ai_identity_verify.py`, maintainer sign-off required)

All of items 1 to 7 shipped in CLI 1.6.0, with tests for each REJECT path
they add. The optional `mirror_commit` check in section 7.3 is not
implemented: it needs a clone of the mirror rather than its published files.

1. **`bundle` subcommand.** It accepts a ZIP or an extracted directory and
   implements sections 7.1 to 7.5. All new strictness lives here: the existing
   subcommands keep their 1.5.0 verdicts except items 3 and 4 below.
2. **Manifest verification and cross-binding** (section 4, section 7.1 steps 1
   to 3).
3. **`inclusion-proof`.**
   - Reject a checkpoint payload whose `schema_version` is not 1.
     `evidence-anchor-reference-notes.md` already states this rule. From
     1.6.0 the CLI enforces it wherever it verifies a checkpoint, which
     includes `chain --tombstones` with `--jwks` or `--pubkey`.
   - Bind `tree_size` to the signed payload.

   These change verdicts only for malformed inputs.
4. **`chain`.** Treat `scope.type == "incident"` as a sparse slice, like
   `agent`. Incident exports are sparse, and today a gap in one reads as a
   deletion.
5. **Key-free tombstone accounting inside `bundle`**, with the checkpoint
   signature mandatory. Today it exists only inside `chain`, which exits
   without `AI_IDENTITY_HMAC_KEY`.
6. **Tier W** behind an explicit `--online` flag. This is the only network
   code in the verifier, and it is off by default.
7. **Tests** for every REJECT path above, plus a CHANGELOG entry.

## 11. Open questions

1. **Anchor a public content digest (v2 candidate).** Committing a public,
   unkeyed content digest per row, alongside or inside the leaf, would close
   section 9.3 for everyone. An unsalted digest of low-entropy rows invites
   dictionary attacks wherever leaves are published. Leaves are not served on
   the public feed, but they do ship in bundles. So the digest needs a per-row
   salt carried in the row. This is a checkpoint-format change and needs its
   own spec.
2. **Manifest signing key.** Reusing the checkpoint signer's key version is
   safe, because PAE domain-separates by `payloadType`. A dedicated key in the
   same key ring isolates compromise and rotation. Recommendation: a dedicated
   key, published in the same JWKS.
3. **Builder facts to confirm before implementation.**
   - Does the section 10.1 item 2 accounting hold today?
   - What exact `scope` object does an incident export carry (`type` value and
     id field name)?
