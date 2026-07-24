# Forensic attestation trust model

**Status:** v1.1 — documents the trust guarantees shipped in Milestone #33;
adds the tamper-evident vs. tamper-proof threat model.
**Owner:** CTO
**Last reviewed:** 2026-07-17
**Audience:** SOC 2 auditors, customer compliance teams, incident
responders, and anyone who needs to reason about what a signed AI
Identity attestation does and does not claim.

Companion documents:

- [`attestation-format.md`](attestation-format.md) — the signed payload
  wire format and verification algorithm
- [`key-rotation.md`](key-rotation.md) — operator runbook for key
  rotation and emergency revocation

## TL;DR for auditors

A valid AI Identity forensic attestation proves:

1. **AI Identity possessed a specific KMS key** at a specific moment
   in time, and
2. **used that key to commit to a specific range of audit log rows**
   whose integrity chain resolves to a specific `evidence_chain_hash`.

That is the entire cryptographic claim. Everything else — what the
agent "did," whether a policy was "correct," whether a denial was
"justified" — is a *content* question about the rows themselves. The
attestation guarantees you are looking at the rows AI Identity was
looking at; it does not vouch for what those rows say.

## Trust root

The attestation signature is produced by **GCP Cloud KMS** using an
asymmetric key with algorithm `EC_SIGN_P256_SHA256`. Trust in an
attestation reduces to trust in three things, in order:

1. **The GCP KMS key material stayed within KMS.** Google's FIPS 140-2
   Level 3 hardware security modules hold the private key; no AI
   Identity process or operator has ever seen the private half.
   [`scripts/setup-forensic-signer.sh`](../../scripts/setup-forensic-signer.sh)
   is the authoritative provisioning script — review it to see the IAM
   bindings and key-import settings exactly as deployed.
2. **The public key you used to verify matches the one AI Identity
   published.** The JWKS endpoint
   (`/.well-known/ai-identity-public-keys.json`) publishes every
   non-destroyed key version. An auditor who wants an independent
   trust anchor can fetch the same public key *directly* from GCP KMS
   via `gcloud kms keys versions get-public-key` and compare — the
   two must agree.
3. **AI Identity did not sign a falsified statement.** The attestation
   commits to a range of `audit_log` rows; if AI Identity fabricated
   rows before signing, the signature is still cryptographically
   valid. The protection against this is the HMAC chain, which is
   signed by a *different* key (the org's `audit_hmac_key`) held in
   the application database — so forging an attestation covering
   fabricated events would require **both** the KMS private key *and*
   the HMAC key. Concentrating both secrets in a single compromised
   path is the threat model this design exists to defeat.

## What a valid attestation proves

Given (a) an envelope, (b) the matching public key, (c) the audit log
rows for `[first_audit_id, last_audit_id]`, and (d) the org's HMAC
verify key, if the CLI reports `VALID` then **all** of the following
hold:

- The envelope was produced by the key identified in `signer_key_id`.
- At the moment of signing (`signed_at`), AI Identity had those
  specific audit rows in the state they appear now.
- The rows form a contiguous HMAC chain with no insertions, deletions,
  or modifications since `signed_at`.
- The chain's tail hash matches the payload's
  `evidence_chain_hash` — so even re-ordering or swapping rows is
  detectable.
- The range is self-consistent: `last_audit_id - first_audit_id + 1
  == event_count`, all rows belong to `org_id`.

## What a valid attestation does NOT prove

| Not proven | Why | What you need instead |
|---|---|---|
| The *agent* did anything in particular | Attestation binds audit rows; rows record gateway decisions, not agent intent | Upstream telemetry, agent-side logging |
| A denial was "correct" by policy | The attestation captures *what the gateway decided*, not whether the policy was right | Policy review, customer sign-off on policy changes |
| Timing within the session | `session_start` / `session_end` are producer-reported; `signed_at` is the only timestamp the signer attests to | Independent timing (gateway logs, upstream timestamps) |
| Events outside the committed range | The attestation says nothing about `audit_log.id < first_audit_id` or `> last_audit_id` | A separate attestation covering the other range |
| That AI Identity itself is trustworthy | Attestation only proves the chain is intact — it cannot prove AI Identity didn't fabricate the whole session before signing | The HMAC chain uses a *different* key than the attestation (see Trust root §3) |

## Tamper-evident, not tamper-proof

The audit chain is **tamper-evident**, deliberately — not
tamper-proof. Records *can* still be altered by an actor with enough
access; the guarantee is that the alteration becomes **detectable** at
the next verification, not that it is physically impossible. The
honest one-liner:

> Nothing prevents a sufficiently privileged attacker from touching
> the bytes — what the chain guarantees is that they cannot do it
> without breaking verification, they cannot repair verification
> without the HMAC key, and they cannot hide truncation once a
> checkpoint has left the building.

Each qualifier in that sentence maps to a specific control:

| Qualifier | Threat it names | Control |
|---|---|---|
| "touching the bytes" | A DBA, superuser, or anyone with disk/backup access can rewrite rows — `GRANT`-level append-only is policy, not physics | Append-only grants raise the bar; they are not the guarantee |
| "without breaking verification" | Any edit to a stored payload | Chained HMACs — one changed byte breaks `entry_hash` at that row and every `prev_hash` link after it |
| "without the HMAC key" | An attacker who edits a row *and* recomputes every downstream hash produces a chain that verifies. HMAC is symmetric: the verify key is the forge key | Two chains, two custody domains. The per-org key (`organizations.forensic_verify_key`) lives in the application database and is dashboard-visible to org admins — it can verify *and* forge the org chain, which is why the dashboard warns never to hand it to an external auditor. The platform-wide key (`AUDIT_HMAC_KEY`) is runtime configuration, never stored in the database — every row carries both hashes, so a re-forged org chain still fails platform-chain verification |
| "once a checkpoint has left the building" | Truncation: deleting the tail of the chain leaves a shorter chain that is internally valid. The gap-free per-org sequence catches holes in the middle, not a clean cut at the end | External anchors — signed Merkle checkpoints (Evidence Anchor) and exported, signed Case Files held outside our infrastructure. A rolled-back chain cannot match a head the verifier already holds |

The privileged insider is the ceiling of the HMAC layer. An org admin
can read the org verify key from the dashboard *by design* — so
against your own administrators (or a compromised admin account), the
per-org chain proves nothing by itself. That adversary is answered by
the layers whose keys an insider cannot hold: the KMS attestation key
(non-extractable from the HSM — Trust root §1) and external anchors —
signed Merkle checkpoints and Case Files already exported to third
parties. A dual-key insider can rewrite the database into perfect
self-consistency; they cannot make it match the copy of history
someone else already holds.

One further boundary: the chain seals whatever the audit writer is
handed. If an event is falsified *upstream* of the writer, the chain
faithfully and verifiably records the falsehood. Chain integrity
proves a record has not changed *since it was written*; authenticity
at capture time is the job of the signing layers above (agent
identity, signed mandates, attestations).

## What to show a SOC 2 auditor

A complete SOC 2 Type II forensics package for a given session
comprises:

1. **The attestation envelope** — fetch from
   `GET /api/v1/sessions/{session_id}/attestation`. This is the ~1 KB
   DSSE JSON.
2. **The audit log rows for the committed range** — from
   `/api/v1/audit/export` with `first_id` / `last_id` scoped to the
   range in the payload.
3. **The public key set (JWKS)** — fetch from
   `/.well-known/ai-identity-public-keys.json`. Save a copy at
   evidence-collection time; do not rely on live fetch during audit.
4. **The org's HMAC verify key** — the same
   `AUDIT_HMAC_KEY` configured on the AI Identity server at the time
   the rows were written. For customers who self-host, this lives in
   their own secret store.
5. **This document** — the trust model so the auditor understands what
   the signature does and does not cover.

Then run:

```bash
# Verify the attestation signature
python cli/ai_identity_verify.py attestation envelope.json --jwks keys.json

# Verify the HMAC chain covers the committed range
AI_IDENTITY_HMAC_KEY='...' \
  python cli/ai_identity_verify.py chain audit_export.json
```

Both must pass for the package to be trustworthy.

## Known limitations

- **Retention erases evidence.** If `audit_log` rows in a committed
  range are pruned by retention policy, the attestation envelope
  remains cryptographically valid but becomes unverifiable — a
  verifier cannot walk a chain they cannot read. See the "Retention
  coordination" section of [`attestation-format.md`](attestation-format.md)
  for the guardrails. We also freeze the resolved row IDs at sign
  time (`audit_log_ids` column), so a verifier can detect "the chain
  existed at sign time but N rows are missing now" rather than failing
  silently.
- **Destroyed keys cannot be verified.** If a signing key version is
  destroyed in KMS, attestations it signed stay cryptographically
  intact but the public key is no longer resolvable. KMS key
  destruction is a deliberate, irreversible operator action — the
  rotation runbook forbids it for active keys.
- **Clock skew.** `signed_at` is the signer's wall clock, not a
  trusted third-party timestamp. A large skew between `signed_at` and
  `session_end` is worth investigating but does not invalidate the
  cryptographic claim.
- **No blinding.** The attestation reveals `event_count`, `org_id`,
  and `session_id`. Organizations that consider these counts
  sensitive should scope session windows accordingly.

## Emergency: suspected key compromise

If you believe a signing key has been compromised:

1. **Stop using it.** The on-call operator follows
   [`key-rotation.md`](key-rotation.md), Emergency Rotation section,
   to move traffic to a new version *immediately*.
2. **Notify affected customers.** Any attestation signed between the
   compromise window and the rotation must be assumed adversarially
   influenced. Customers should re-verify those sessions by walking
   the HMAC chain against `audit_log` directly — the chain uses a
   different key, so the HMAC check is still sound.
3. **Preserve evidence.** Do **not** destroy the compromised key
   version. Disable it in KMS (so it can't sign) but keep the public
   key resolvable so historical attestations remain verifiable.
4. **Root-cause and publish.** Postmortem is customer-facing; see
   `docs/incident-response/` for the template.

## Questions or corrections

File an issue against the `docs/forensics/` directory or contact the
CTO directly. This document is versioned — material changes bump the
status line at the top.
