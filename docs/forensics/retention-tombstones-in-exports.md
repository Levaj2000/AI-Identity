# Retention tombstones in exports (v1)

**Status:** Shipped. The platform writes the file (reaper phase 5); the
offline verifier consumes it from CLI 1.5.0 (`chain --tombstones`).
**Owner:** CTO
**Last reviewed:** 2026-09-15

Retention policies prune `audit_log` rows on a schedule. Pruning is never
silent: every pruned row leaves a tombstone, every batch of tombstones is a
chained receipt anchored in the same audit log, and nothing is pruned before
the checkpoint that committed it has been witnessed on the public mirror.
This document specifies how that evidence travels inside a Case File bundle
and how an offline verifier uses it, so that a sequence gap caused by
retention verifies as retention and a gap with no receipt still fails.

The platform-side algorithm and the bundle writer live in the private
platform repository (`common/retention/tombstone_verify.py` and
`common/retention/export.py`). This file is the contract between them and
`cli/ai_identity_verify.py` in this repository.

## Where it lives

`retention/tombstones.json`, next to `evidence-anchor/checkpoints.json`, in
the ZIP that `GET /api/v1/audit/report/bundle` returns. It is present only
when at least one row inside the export's id range was pruned. Its absence
means no row in `[first exported id, last exported id]` has a tombstone.

## Format: `ai-identity-retention-tombstones/v1`

```json
{
  "format": "ai-identity-retention-tombstones/v1",
  "org_id": "0f2c...",
  "range": {"first_audit_id": 48151000, "last_audit_id": 48155999},
  "tombstones": [
    {
      "audit_id": 48151623,
      "org_chain_seq": 9001,
      "entry_hash": "3a7f...",
      "entry_hash_org": "71ab...",
      "checkpoint_id": "9c1e...",
      "merkle_root": "ab12...",
      "event_id": "5d0e...",
      "policy_version_id": "7d0b...",
      "rule_id": "rule_audit_dev_sampled",
      "reason": "sampling",
      "pruned_at": "2026-09-15T02:45:11.318204+00:00"
    }
  ],
  "receipts": [
    {
      "id": "5d0e...",
      "event_type": "tombstone",
      "payload": {"checkpoint_id": "9c1e...", "merkle_root": "ab12...", "count": 4211, "...": "..."},
      "created_by": "system:retention-reaper",
      "created_at": "2026-09-15T02:45:11.402911+00:00",
      "audit_log_id": 48160002
    }
  ],
  "checkpoints": [
    {
      "merkle_root": "ab12...",
      "envelope": {"payloadType": "...", "payload": "...", "signatures": ["..."]},
      "audit_log_ids": [48151000, 48151001, "..."],
      "leaves": ["c0ff...", "e4a1...", "..."],
      "mirror_commit": "3f9a..."
    }
  ]
}
```

Field notes:

- `range` is the export's `[min(id), max(id)]`. An exported slice can only
  have holes between its first and last row, so tombstones outside the range
  are not shipped.
- `tombstones[].entry_hash` is the platform-chain hash, which is also the
  checkpoint leaf. `entry_hash_org` is the per-org chain hash and exists
  nowhere else once the row is gone: it is what links the next surviving
  row's `prev_hash_org`.
- `receipts` are the `tombstone` retention events the tombstones point at.
  `audit_log_id` is the receipt's own chained anchor row. A receipt with no
  anchor is not a receipt.
- `checkpoints` carries every checkpoint any tombstone cites, including ones
  that `evidence-anchor/checkpoints.json` omits because all of their rows
  were pruned. The signed envelope commits to `merkle_root`; the frozen
  `audit_log_ids` and `leaves` are how a verifier ties a tombstone to that
  root. `mirror_commit` is the commit of the public mirror branch at which
  the checkpoint was witnessed before any of its rows were pruned.

## Verifier algorithm (offline, `chain --tombstones`)

Given the case file's `events` (surviving rows, per-org chain fields) and
this file, walk the org chain in `org_chain_seq` order exactly as today, and
at a sequence gap (expected `N`, got `M > N`):

1. Every sequence in `N .. M-1` must have an entry in `tombstones` with that
   `org_chain_seq` and this `org_id`. A missing sequence is a failure:
   report `sequence gap (rows deleted from this org's history)` with the
   first uncovered sequence, as today.
2. For each tombstone in the gap, in sequence order:
   - Find its checkpoint in `checkpoints` by `merkle_root`. Missing: fail.
   - Verify the checkpoint envelope with the published JWKS public key (the
     same check `inclusion-proof` performs) and confirm the signed payload's
     `merkle_root` equals the entry's `merkle_root`. Fail on either.
   - Recompute the Merkle root over `leaves` and confirm it equals
     `merkle_root`. This is what makes the unsigned `leaves` list
     trustworthy.
   - Let `i` be the index of `audit_id` in `audit_log_ids`. Confirm
     `leaves[i] == entry_hash`. This proves the pruned row existed with that
     hash under a signed anchor.
   - Confirm the tombstone's `event_id` appears in `receipts` with
     `event_type == "tombstone"` and a non-null `audit_log_id`.
3. Set the expected `prev_hash_org` for row `M` to the last tombstone's
   `entry_hash_org`, then continue the walk normally. Row `M` fails on
   `prev_hash_org mismatch` if the tombstones do not actually bridge the gap.
4. Report pruned counts next to verified counts. `valid with 4211 tombstoned
   rows` must be distinguishable from `valid`; a JSON result carries
   `tombstoned_entries` and the human output says how many rows were
   accounted for by receipts.

Without `--tombstones`, behavior is unchanged: a gap is a failure. The flag
never weakens the check; it only supplies the receipts the check requires.

Agent-scoped exports re-anchor at gaps today (other agents own the sequence
numbers in between) and keep doing so; tombstones are consulted only in the
org-scope walk, where completeness is claimed.

## Attestation cross-check (server side)

The same evidence backs `GET /api/v1/sessions/{id}/attestation`. The
attestation's frozen `audit_log_ids` list is reconciled on every read: each
id is present, tombstoned (a tombstone passing the checks above covers it),
or unaccounted. The response's `retention` block carries the three counts,
the unaccounted ids, and `complete`. See `attestation-format.md`, "Retention
coordination".

## OCSF export (`format=ocsf`)

The platform's OCSF export (`GET /api/v1/audit/report?format=ocsf`, NDJSON)
renders one event per surviving `audit_log` row. A tombstone
receipt's anchor row is one of those rows, and it exports as **Datastore
Activity** (`class_uid` 6005, `activity_id` 7 Delete, `type_uid` 600507)
rather than the generic API Activity `Create` it rendered as before. Ids are
the OCSF 1.9.0 schema's (`events/application/datastore_activity.json`).

| OCSF attribute | Value |
| --- | --- |
| `actor.app_name` | `retention-service` (the class requires an actor; no user acted) |
| `type_id` / `table.name` | 3 (Table) / `audit_log` |
| `count` | rows pruned by this receipt |
| `time` | the anchor row's `created_at` |
| `metadata.uid` | the anchor `audit_log` row id, unchanged, so `prev_event` references from the next row still resolve |
| `metadata.correlation_uid` | the retention event id: the key into `retention/tombstones.json` |
| `attestation_list` | the anchor's chain fingerprint, predecessor and export signature, same as any other row |
| `unmapped.retention_tombstone` | `checkpoint_id`, `merkle_root`, `mirror_commit`, `policy_version_id`, `rule_id`, `reason`, `audit_id_range`, `org_chain_seq_range` |
| `unmapped.org_chain_seq` | the anchor's own position, same key as every other exported row |

`action_id` is not an attribute of Datastore Activity and is not emitted.
Per-row `entries` stay out of the event: a receipt can cover 5000 rows and
every SIEM copy would carry them; they live in `retention/tombstones.json`.

A row whose chain predecessor is a receipt anchor carries
`prev_event.type_uid` 600507, pointing a consumer at the Datastore Activity
store for the predecessor.

**Consumer rule.** Order an org's API Activity events by
`unmapped.org_chain_seq`. A hole with no 600507 event whose
`unmapped.retention_tombstone.org_chain_seq_range` covers it is an
unaccounted deletion. A hole covered by one is retention, and the receipt
names the checkpoint, policy version and rule that authorized it. The
offline proof (leaf and signature checks) remains the CLI's
`chain --tombstones`; the OCSF event is the pointer a SIEM can alert on.

## Verifier support

`cli/ai_identity_verify.py chain --tombstones retention/tombstones.json`
implements the algorithm above (CLI 1.5.0). `--jwks` or `--pubkey` adds the
checkpoint signature check; without a key the structural checks still run
and the output says the signatures were not verified. Bundles embed the
verifier at export time, so a bundle exported before 1.5.0 carries a CLI
that reports the gap; run the current CLI against it, or reconcile the gap
against the file by hand as its README describes.
