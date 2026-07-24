# OCSF #1661 Sync Plan — aligning emission to the merged schema

**Status:** PR [ocsf/ocsf-schema#1661](https://github.com/ocsf/ocsf-schema/pull/1661)
**MERGED 2026-07-17** (commit `2a244bc9`, ships in OCSF 1.9). Our OCSF emission
layer predates the final review round and must catch up. **Execution window:
after the 2026-07-20 IBM demo** (demo freeze — the demo runs on the proven
deployed build). Draft branch: `feat/ocsf-1661-merged-shape`.

> **Status 2026-07-21:** A+B done on `feat/ocsf-1661-merged-shape` (pushed,
> commit `021ae944`, tests green per 7/17 session) — awaiting PR + merge (demo
> freeze lifted 7/20). C done in the same worktree (uncommitted — plugin home
> still undecided). D pends deploy. F flips ALL executed: pipeline + badge
> shipped 7/17 (PRs #387/#388); 30-min runbook say-lines + Ian close,
> cross-runtime doc+PDF (regenerated), and positioning-note flipped locally
> 2026-07-21. Cross-runtime PDF: re-share to the David Pierce DM only if the
> old "final review" version was posted there — verify before sending.

## What changed in the final merged shape (vs. what we emit)

| We emit today | Merged #1661 shape |
|---|---|
| `event["attestation"] = {…}` (singular) | `event["attestation_list"] = [ {…} ]` — array of `attestation` |
| `entry_hash` (fingerprint obj) | `fingerprint` |
| `prev_entry_hash` (fingerprint obj) | `prev_event` object: `{ uid, type_uid, fingerprint }` — **`uid` required**, `type_uid` recommended, `fingerprint` optional (we always set it) |
| no `metadata.uid` | each event needs `metadata.uid`; `prev_event.uid` references the previous event's `metadata.uid` |
| — | `fingerprint.encoding_id: 1` (Hex — #1684) now available; our values are hex |
| — | `fingerprint.serialization_id` / `digital_signature.serialization_id` exist; **Flat = 1, JCS = 2** (renumbered late — JCS is 2, not 1) |
| `signatures[]` w/o serialization | our ECDSA signs raw hash bytes → `digital_signature.serialization_id: 1` (Flat) |

Unchanged and still correct: HMAC chain fingerprint as `algorithm_id: 99`
(`HMAC-SHA-256` — keyed, so claiming SHA-256 would misstate it);
`chain_uid`; `authority_uid` (not yet emitted — optional add, identifies the
attesting authority; our stable signer identity per the key-epoch design);
`attestation.uid`; signature bytes + key id in `unmapped` (schema still has
no field — John's follow-on PR).

## Punch list

### A. Emitter — `common/ocsf/api_activity.py` (+ its export callers)
1. Emit `metadata.uid` (= audit row id) on every event.
2. `attestation` → `attestation_list: [attestation]`.
3. `entry_hash` → `fingerprint`; add `encoding_id: 1` (Hex).
4. `prev_entry_hash` → `prev_event: {uid, type_uid, fingerprint}`.
   **Design decision (resolved: option a):** in agent-scoped slice exports the
   chain predecessor may be outside the slice; the exporter looks up the
   predecessor row's id/method to populate `uid`/`type_uid` (echoes PR #377's
   slice-awareness). If the predecessor row no longer exists (retention), omit
   `prev_event` for that boundary event rather than emit a uid-less object.
5. `signatures[]`: add `serialization_id: 1` (Flat) — ECDSA over raw hash bytes.
6. Consider `authority_uid` (stable signer identity, key-epoch design) — optional.
7. Update module docstring (it documents the pre-final shape).

### B. Tests
`api/tests/test_ocsf_export.py` + any test asserting `event["attestation"]` /
`entry_hash` keys — update to the merged shape.

### C. CPEX plugin — `integrations/cpex-ocsf-audit/` (Rust)
Same renames (`attestation_list`, `fingerprint`, `prev_event`), plus
`serialization_id` for its canonicalization (verify whether it is true RFC 8785
before claiming JCS = 2; otherwise 99/Other with the sibling naming it).
Note: Teryl reviewed the old shape — the update note to him is a natural
"now matching the merged schema" touchpoint.

### D. Regeneration + re-share (post-merge of the branch, prod)
1. Re-export reference bundle + shop-agent walk ndjson in the new shape.
2. Re-share with Fred/Teryl: "regenerated against the merged 1.9 shape."
3. Rides along: key-epoch prod follow-ups (migration + backfill + Case File
   re-export) already queued.
4. `OCSF_VERSION` bumps `1.9.0-dev` → `1.9.0` when OCSF tags the release.

### E. Explicitly NOT affected
- Verifier CLI `chain`/`report` — native case-file rows, not OCSF shape.
- Evidence Anchor checkpoints / DSSE attestations — own payload formats.
- Write-time HMAC chain writer — internal construction unchanged.
- Dashboard Case File UI — consumes native export, not OCSF ndjson.

### F. Positioning flips (independent of code; some pre-demo)
- forensics-pipeline.html: "PR #1661, in review" → "merged into OCSF 1.9".
- 30-min runbook say-lines + Ian close ("in final review" → "merged").
- Cross-runtime visibility doc/PDF: "in final review for 1.9" → "merged".
- ocsf-positioning-note copy: "contributing to" → "merged into" for #1661.
