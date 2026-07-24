# Evidence Anchor — Public Checkpoint Feed & Mirror

**Making "someone else already holds the checkpoint" true by default.**
Companion to [evidence-anchor-reference-notes.md](evidence-anchor-reference-notes.md) · 2026-07-24

## 1. The gap this closes

A signed checkpoint only constrains us if a copy exists *outside* our
infrastructure — otherwise nothing stops the operator from re-signing a
rewritten history and serving the new version everywhere. Until now the only
way a checkpoint left our systems was inside an exported Case File bundle
(`evidence-anchor/checkpoints.json`), so the "outside our infrastructure"
claim was only as strong as bundle distribution: no export, no witness.

Two additions make the commitment public by default:

1. **A public, unauthenticated feed** of the full signed-checkpoint history.
2. **An off-infrastructure mirror** that snapshots that feed on a schedule,
   keeps every snapshot in git history, and alarms if the feed ever stops
   *extending* the history the mirror already holds.

## 2. The feed

Same trust posture as the JWKS (`/.well-known/ai-identity-public-keys.json`):
public by design, no auth, CDN-cacheable.

### `GET /evidence-anchor/checkpoints`

Paginated history of signed checkpoint DSSE envelopes, **oldest first**.
Because history is append-only, ascending pages are stable — an offset walk
never shifts under the consumer, and a poller can resume with `since` set to
the newest `signed_at` it holds.

| Param | Meaning |
|-------|---------|
| `org_id` | restrict to one org's checkpoints (opaque UUID) |
| `since` / `until` | `signed_at` range (`>= since`, `< until`) |
| `limit` / `offset` | pagination, `limit` ≤ 500 (default 100) |

Each entry is the exact artifact a Case File bundle ships — `merkle_root` +
the DSSE `envelope`, byte-comparable with a `checkpoints.json` entry — plus
mirrored indexing fields (`org_id`, `tree_size`, `first_audit_id`,
`last_audit_id`, `signer_key_id`, `signed_at`) so consumers can filter
without decoding payloads. The raw batch internals (`leaves`,
`audit_log_ids`) are **not** served; the signed root is the commitment.

### `GET /evidence-anchor/checkpoints/{merkle_root}`

The split-view spot check. A bundle holder takes the root their bundle
verifies against and asks the public history for it:

```bash
curl https://api.ai-identity.co/evidence-anchor/checkpoints/<merkle_root-from-your-bundle>
```

- **200 with the identical envelope** → the checkpoint you hold is the same
  one everyone else can see.
- **404 for a root your bundle verifies against offline** → you were shown a
  checkpoint the public was not. That is the red flag; escalate
  (security@ai-identity.co) and keep the bundle.

## 3. The mirror

`.github/workflows/evidence-anchor-mirror.yml` runs every 6 hours (and on
manual dispatch — use that for the first run to bootstrap the branch):
`scripts/evidence_anchor_mirror.py` pages through the feed and commits the
full history to the dedicated **`evidence-anchor-mirror` branch** of this
public repo as `checkpoints.ndjson` (one canonical-JSON entry per line) plus
`mirror-state.json`.

Properties that make it a witness rather than a cache:

- **Held off our serving infrastructure.** The branch lives on GitHub, not
  GKE — it survives an API outage, and the newest snapshot is always
  fetchable at
  `https://raw.githubusercontent.com/<owner>/<repo>/evidence-anchor-mirror/checkpoints.ndjson`.
- **Append-only, enforced.** Before writing, the script verifies the fresh
  fetch *extends* what the mirror holds: every mirrored `merkle_root` must
  still be served byte-identically, and no `(org_id, first_audit_id)` batch
  slot may reappear under a different root. A violation refuses the update,
  fails the run loudly (GitHub's failure email), and leaves the existing
  branch as the evidence.
- **Timestamped custody.** Every snapshot is a git commit; GitHub's commit
  history dates each state of the history independently of our clocks.

## 4. The detection story (CT-style, honestly scoped)

The attack family this addresses is **split view / rollback**: an operator
(or an attacker with the signing key) who rewrites a batch, re-signs it, and
presents the forged history to one audience while others saw the original.
Signatures alone cannot catch this — both views verify. What catches it is
*multiple parties comparing the commitments they hold*, which is the core
idea of Certificate Transparency.

Who detects what:

| Party | Check | Catches |
|-------|-------|---------|
| Bundle holder | root lookup (§2) against feed or mirror | being shown a private fork |
| Mirror job | append-only check every 6 h | feed-side rewrite, deletion, or mutation of any published checkpoint |
| Third-party watcher | clone/watch the mirror branch; diff snapshots | the same, without trusting our GitHub actions |

What this is **not**:

- **Not a single CT log.** Checkpoints are a sequence of independent per-org
  Merkle trees, not one growing tree — there are no RFC 6962 consistency
  proofs between checkpoints. Append-only is enforced at the
  checkpoint-slot level (contiguous, non-overlapping `(org_id,
  first_audit_id)` batches), which is the equivalent guarantee for this
  structure.
- **A mirror in our own GitHub org is a raised bar, not full independence.**
  We could delete the branch or force-push — visibly, against GitHub's audit
  trail, and any third party who has cloned or watches the branch keeps the
  evidence. True independence is exactly that: external parties cloning the
  branch or polling the feed. The design makes becoming a witness a
  one-liner; IBM/CoSAI-style partners running their own copy of
  `evidence_anchor_mirror.py` against the feed is the intended end state.
- **A window exists.** Events are `pending` until anchored (~15 min cadence)
  and a checkpoint is unmirrored until the next snapshot (≤ 6 h). A rewrite
  inside that window beats the mirror but still has to beat every bundle
  exported in it.

## 5. Metadata exposure (deliberate, bounded)

Publishing the history publishes commitment metadata: opaque org UUIDs,
per-org batch counts/sizes (`tree_size`), audit-id ranges, and signing
times — i.e. *that* tenants produce events and roughly how many, never event
content, hashes of individual events, or anything reversible. This is the
same trade CT logs make and is inherent to a public witness. If a future
enterprise contract requires opting out of the public feed, that is a
product decision to take knowingly — an opted-out org's checkpoints fall
back to bundle-distribution-only witnessing.

## 6. Copy this enables

The technology-up-close PDF and the exec demo's Evidence Anchor beat can
move from "checkpoints ship in every exported bundle" to: **"the checkpoint
history is public — anyone can hold a copy, and our own mirror alarms if the
history is ever rewritten."** Architecture page copy updated in the same
change; regenerate the PDF at the next collateral pass.
