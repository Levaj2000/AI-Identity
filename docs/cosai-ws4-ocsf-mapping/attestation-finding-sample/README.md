# Sample: `attestation_finding` (PR #1689) populated from a production system

A working sample of the `Attestation Finding` class proposed in
[ocsf/ocsf-schema#1689](https://github.com/ocsf/ocsf-schema/pull/1689)
(at commit `cffd386e`), populated from a real production audit trail — plus a
one-field experiment showing why the finding's references need event hashes.

## What's here

| File | What it is |
|---|---|
| `source-events.ocsf.ndjson` | 8 real production OCSF API Activity events (from the previously shared 174-event reference bundle; per-event signatures verify against the production JWKS) |
| `evidence-anchor-checkpoint.dsse.json` | A signed Merkle checkpoint (RFC 6962 tree over the 8 events' attestation hashes, DSSE envelope, ECDSA-P256) |
| `checkpoint-public-key.pem` | The public key that verifies the checkpoint |
| `inclusion-proofs.json` | O(log N) inclusion proof for each event |
| `attestation-finding.as-1689.json` | The checkpoint expressed as an `attestation_finding` event, **strictly the #1689 schema**: `related_events` carry `uid`/`type_uid` only |
| `attestation-finding.with-hashes.json` | The **same finding with one added field**: each reference also carries `record_hash` |
| `verify_finding.py` | Standalone offline verifier (Python 3.10+, `pip install cryptography`; re-implements RFC 6962 + DSSE in-file, imports nothing from the producer) |

## The experiment

```
python3 verify_finding.py                      # both variants verify
python3 verify_finding.py --tamper delete      # drop one referenced event
python3 verify_finding.py --tamper substitute  # edit one event, rewriting its stored hash consistently
python3 verify_finding.py --prove 3            # prove one event's inclusion in O(log N)
```

Results:

| Tamper | refs = `uid`/`type_uid` only (#1689 as drafted) | refs + `record_hash` (one added field) |
|---|---|---|
| delete a referenced event | detected | detected |
| edit/substitute a referenced event | **verifies falsely** | **detected, at the exact reference index** |

With uid-only references there is no hash anywhere in the finding or its
`attestation_list`, so a verifier has nothing to bind references to content
and nothing to recompute the signed Merkle root from — member integrity is
unverifiable *by construction*, not by implementation choice. Adding a single
content-binding hash per reference restores both checks.

The reference field name/shape (`record_hash` here) is not the point and can
follow whatever the group settles on (e.g. the `prev_event {uid, type_uid,
hash}` shape discussed on #1661/#1689); the point is that a hash rides with
each reference.

## Provenance notes

- The 8 events are verbatim from the production export previously shared
  (174 events, 174/174 signatures verified against the production JWKS). They
  carry the per-event `attestation` object from #1661 — field naming tracks an
  earlier revision of that PR (`entry_hash`/`prev_entry_hash`).
- The Merkle tree, checkpoint canonicalization (RFC 8785), and DSSE envelope
  are produced by the production Evidence Anchor code path. The checkpoint
  signing key in this sample is a demo key generated at build time (production
  signs with a KMS-backed key published via JWKS); the public key is included
  so everything verifies offline.
- `attestation_authority_uid` (added to #1689 in `cffd386e`) is populated on
  both the class and the `attestation_list` element, with matching values, per
  that commit's linkage rule.
