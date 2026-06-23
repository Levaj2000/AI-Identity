# Evidence Anchor — Reference Implementation Notes

**Public-key-verifiable inclusion proofs for OCSF audit events.**
Prepared for the OCSF data-storage-patterns discussion · AI Identity · 2026-06-23

> **The one-line relevance to the storage debate:** integrity verification here reads *no database and no storage layout* — only an exported signed checkpoint and a proof. So how you store OCSF events (one wide table vs. per-class / per-source tables) is **orthogonal** to how you prove them. You can choose storage purely on query performance.

---

## 1. The problem it solves

Our OCSF audit events form a per-org, append-only **hash chain**: each event carries a per-event hash (`entry_hash`) computed over its canonical record and the previous event's hash. That gives tamper-evidence, but **independent** verification of a single event is awkward:

- To prove one event is committed, you re-walk the chain from a trusted tip → **O(N)**.
- The chain hash is **keyed** (secret-dependent), so the only party who can recompute it is one you'd also be trusting with the power to forge it.

For a storage discussion, the salient point: a linear-chain verification model couples *proving* an event to chain length **and** secret custody. We wanted verification that depends on neither — and, in particular, doesn't care how the events are stored.

## 2. The anchor (design in one paragraph)

A scheduled worker batches the per-event `entry_hash` values and builds a **Merkle tree (RFC 6962** domain separation), then signs the **root once** with **ECDSA-P256** in a **DSSE** envelope; the public key is published via **JWKS**. A small signed *checkpoint* now commits an entire batch of events. Any single event gets an **O(log N) inclusion proof** that a third party verifies with **only SHA-256 + the public key** — zero database access, zero shared secret. It is a verification layer *on top of* the existing chain, not a replacement for it.

```
events --> entry_hash[] --> Merkle tree (RFC 6962) --> root
                                                       |  sign once (ECDSA-P256, DSSE, JCS)
                                                       v
                                             signed checkpoint --> JWKS public key

verify one event:  SHA-256(inclusion proof) + ECDSA(public key) = committed?   (O(log N), offline)
```

## 3. Signed checkpoint format (`MerkleCheckpointV1`)

The signed payload is JSON, canonicalized with **RFC 8785 (JCS)**, wrapped in a **DSSE** envelope. Payload fields:

| Field | Meaning |
|-------|---------|
| `schema_version` | `1` (verifiers reject unknown versions) |
| `org_id` | tenant whose chain the batch was drawn from (per-org root) |
| `tree_size` | number of leaves (events) under the root |
| `merkle_root` | SHA-256 hex of the RFC 6962 root over the batch's `entry_hash` values |
| `first_audit_id` / `last_audit_id` | inclusive id range of the committed batch |
| `signed_at` | RFC 3339 (`…Z`) signing time |
| `signer_key_id` | KMS key-version resource path (pins the key across rotations) |

DSSE envelope (the thing in `checkpoints.json`):

```json
{
  "merkle_root": "<sha256-hex>",
  "envelope": {
    "payloadType": "application/vnd.ai-identity.anchor-checkpoint+json",
    "payload": "<base64(JCS-canonical checkpoint JSON)>",
    "signatures": [{ "keyid": "<signer_key_id>", "sig": "<base64(DER ECDSA-P256)>" }]
  }
}
```

The signature is over `PAE(payloadType, payload)` (DSSE pre-auth encoding), giving length-prefixed domain separation — a checkpoint signature can never be replayed as another payload type.

## 4. Inclusion-proof format

`inclusion-proofs.json`:

```json
{
  "proofs": [
    {
      "audit_id": 84213,
      "entry_hash": "<sha256-hex>",        // the leaf value
      "index": 17,                          // position in the tree
      "tree_size": 256,
      "merkle_root": "<sha256-hex>",        // which checkpoint this proves against
      "proof": ["<sha256-hex>", "..."]      // RFC 6962 audit path, log2(N) hashes
    }
  ],
  "pending": [ /* exported events not yet anchored to a checkpoint */ ]
}
```

A multi-class incident is simply **N entries in `proofs`** — one inclusion proof per event, each O(log N). `pending` makes coverage explicit for events newer than the last checkpoint.

## 5. Case File bundle layout

Every forensic Case File export ships an `evidence-anchor/` folder:

```
evidence-anchor/
  checkpoints.json        # one or more signed checkpoints (DSSE envelopes)
  inclusion-proofs.json   # per-event proofs + pending list
```

## 6. Offline verification (re-implementable in any language)

RFC 6962 hashing with CT domain separation:

```
leaf_hash(d)      = SHA-256(0x00 || d)        # d = bytes.fromhex(entry_hash)
node_hash(l, r)   = SHA-256(0x01 || l || r)
```

Two steps, both offline:

1. **Checkpoint signature** — verify the DSSE/ECDSA-P256 signature over `PAE(payloadType, payload)` with the JWKS public key, and bind the signed `merkle_root` to the root the proof references. (A valid signature over a *different* root is useless.)
2. **Inclusion** — run the RFC 6962 §2.1.1 audit-path check: fold `leaf_hash(entry_hash)` up through the `proof` hashes and confirm it equals `merkle_root`. **O(log N)**, SHA-256 only.

Our reference verifier ships **inside every bundle** (Python stdlib + `cryptography`; no network, no DB, no secret):

```bash
ai_identity_verify inclusion-proof \
  --checkpoints evidence-anchor/checkpoints.json \
  --proofs      evidence-anchor/inclusion-proofs.json \
  --jwks        ai-identity-public-keys.json      # or --pubkey signer.pem
# → "INCLUSION VERIFIED — N event(s) provably committed."
```

The public key is at `/.well-known/ai-identity-public-keys.json` (JWKS); the checkpoint `keyid` is matched against it.

## 7. Why this is relevant to the storage-patterns discussion

The verification path in §6 **never touches storage** — not the table layout, not an index, not a join. It consumes only the exported checkpoint + proof. Therefore:

- The **single-wide-table vs. per-class/per-source** decision is independent of integrity verification.
- Splitting tables for query performance does **not** weaken or complicate proof-of-custody.
- You don't have to walk a linear DB chain to prove an event is genuine.

It does **not** make multi-table queries faster — it's orthogonal to that trade-off. The value is that it *removes integrity verification as a constraint* on the storage decision.

## 8. Scope — what it does and doesn't claim

- **Does:** prove inclusion + integrity of each event (committed under a signed root, untampered), independently, with a public key, O(log N) per event.
- **Doesn't:** by itself attest the *causal ordering* between events — that linkage is the underlying hash chain. A multi-class incident is verified as a set of independent inclusion proofs.
- Recent events are `pending` until the next checkpoint (anchoring runs on a cadence, not synchronously).
- Roots are **per-org** (tenant isolation).
- The anchor sits **on top of** the existing keyed chain; it doesn't replace it, and it needs none of the chain's secret to verify.

## References

- RFC 6962 — Certificate Transparency (Merkle tree + audit paths)
- RFC 8785 — JSON Canonicalization Scheme (JCS)
- DSSE — Dead Simple Signing Envelope
- OCSF — Open Cybersecurity Schema Framework

---

## ⚠️ Internal note — REMOVE before sending to Paul

- **Public-safe check:** nothing here exposes `AUDIT_HMAC_KEY`, infra, or internal endpoints. Every artifact described (checkpoint format, proof format, verifier) already ships in customer Case File bundles, and the verifier is the open `ai_identity_verify.py`. Safe to share.
- **Don't let it drift into a performance claim** — it's orthogonal to their query/join trade-off (§7). Lead with that or you'll invite "that's not what we're solving."
- **Maturity:** Evidence Anchor is merged to `main` and runs on a ~15-min anchoring CronJob — say "we built/run this," not "battle-tested at scale" (it's recent).
- **Ordering nuance (§8)** is the one a sharp reader will probe — keep that paragraph if you publish, it pre-empts the objection.
