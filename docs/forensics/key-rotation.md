# Forensic signer key rotation runbook

**Status:** v1 — operator runbook for the forensic signing key.
**Owner:** CTO
**Last reviewed:** 2026-04-17
**Audience:** on-call operator or anyone authorized to rotate the
forensic signing key.

Companion documents:

- [`attestation-format.md`](attestation-format.md) — signed payload format
- [`trust-model.md`](trust-model.md) — what the signature does and does
  not prove; emergency-compromise response

## What this runbook covers

The GCP KMS asymmetric key used to sign forensic attestations. Three
procedures:

1. **Planned rotation** — you want to move to a new key version on a
   schedule. Low-urgency, done during business hours.
2. **Emergency rotation** — you suspect the current version is
   compromised. Do it *now*; worry about tidying up later.
3. **Post-rotation verification** — how to confirm the new version is
   being used for signing and resolvable in JWKS.

This runbook does **not** cover: revoking an org's HMAC audit key
(that's a different key, different procedure, different blast radius);
creating the keyring or service account from scratch (see
[`scripts/setup-forensic-signer.sh`](../../scripts/setup-forensic-signer.sh)).

## Prerequisites

- `gcloud` authenticated as the forensic-signer admin principal
  (see the setup script for which principal)
- `kubectl` pointed at the production cluster (if you need to restart
  the API to pick up env-var changes — usually you don't)
- Write access to the secret store holding `FORENSIC_SIGNING_KEY_ID`

## Planned rotation

1. **Create a new key version.**
   ```bash
   gcloud kms keys versions create \
     --location=us-east1 \
     --keyring=ai-identity-forensic \
     --key=session-attestation \
     --primary
   ```
   The `--primary` flag makes new signing operations use this version;
   older versions remain `ENABLED` for historical verification.

2. **Capture the new key-version resource path.** It looks like:
   ```
   projects/<PROJECT>/locations/us-east1/keyRings/ai-identity-forensic/cryptoKeys/session-attestation/cryptoKeyVersions/<N+1>
   ```
   Read it from `gcloud kms keys versions list` output.

3. **Update the `FORENSIC_SIGNING_KEY_ID` environment variable** on
   every service that signs (currently: the API server). Deploy the
   change as usual — no downtime; the old env var was valid until the
   restart, the new one takes effect after.

4. **Wait for the JWKS cache to refresh.** The endpoint has a 1-hour
   `Cache-Control: public, max-age=3600` — customers may see stale
   keys for up to an hour. If a customer needs the new key immediately,
   tell them to bust cache (`curl -H "Cache-Control: no-cache" ...`).
   The old key version stays `ENABLED` so previously-signed
   attestations still verify.

5. **Verify** — see [Post-rotation verification](#post-rotation-verification).

6. **Do NOT destroy the old version.** Old versions remain `ENABLED`
   indefinitely so historical attestations stay verifiable. The only
   legitimate reason to *destroy* a version is confirmed compromise of
   that specific version's private key material — and even then, see
   the caveat in the Emergency section below.

## Emergency rotation

**Context:** you have reason to believe the current key version's
private material is compromised. Move fast; explain later.

1. **Disable the compromised version** (stops it from signing but
   keeps the public key resolvable for verification of past work):
   ```bash
   gcloud kms keys versions disable <COMPROMISED_VERSION_RESOURCE_PATH>
   ```
   As soon as this completes, KMS will reject any `AsymmetricSign`
   calls against that version — the API attestation endpoint will
   start returning 502 for new signs, which is correct behavior.

2. **Create a new version** as primary (see Planned §1).

3. **Update `FORENSIC_SIGNING_KEY_ID`** and redeploy. New signs resume
   against the uncompromised version.

4. **Post a customer-facing notice.** Any attestation signed during
   the compromise window must be flagged as "adversarially influenced
   — re-verify the HMAC chain directly." The HMAC chain uses a
   different key (the org's `audit_hmac_key`, held in the application
   database) so the chain is still sound even if the attestation
   signature is suspect — customers can walk the chain with the CLI's
   `chain` command to confirm row integrity.

5. **Do NOT destroy the compromised version.** Disabling is
   sufficient. Destruction would make historical attestations
   signed with that key unverifiable — which is *worse* than leaving
   the public key resolvable, because an auditor would not be able to
   tell whether the signature was valid at sign time. The goal is to
   prevent new signs, not to erase the past.

6. **File the incident.** Postmortem template lives in
   `docs/incident-response/`. The customer-facing trust model
   ([`trust-model.md`](trust-model.md), "Emergency: suspected key
   compromise") is the narrative; this runbook is the mechanics.

## Post-rotation verification

After any rotation (planned or emergency), confirm end-to-end:

1. **JWKS lists the new version.**
   ```bash
   curl https://api.ai-identity.co/.well-known/ai-identity-public-keys.json \
     | jq '.keys[].kid'
   ```
   Every enabled + disabled version must appear. Missing versions mean
   the KMS list call failed at JWKS build time — check API logs for
   `ai_identity.api` warnings.

2. **Signing works.** Trigger a test attestation (any closed session
   in a test org):
   ```bash
   curl -X POST https://api.ai-identity.co/api/v1/attestations \
     -H "X-API-Key: $TEST_OWNER_KEY" \
     -H "Content-Type: application/json" \
     -d '{...valid attestation body...}'
   ```
   The response's `signer_key_id` must match the new key-version
   resource path.

3. **Verification works.** Run the CLI offline:
   ```bash
   ai_identity_verify attestation test_envelope.json \
     --jwks <(curl -s https://api.ai-identity.co/.well-known/ai-identity-public-keys.json)
   ```
   Exit code must be `0`.

4. **Metrics are healthy.** Watch
   `ai_identity_attestation_signs_total{outcome="error"}` — a spike
   right after deploy means the new env var didn't take effect.

If any step fails, the rotation did not land cleanly; investigate
before leaving the console.

## Key destruction

**Default posture: never.** A destroyed KMS key version cannot have
its public key fetched; any attestation signed with it is permanently
unverifiable. This is almost always worse than leaving the key
disabled.

The only narrow case where destruction might be appropriate:

- The key version was used briefly and signed **no** attestations
  that were exported to customers (check the `forensic_attestations`
  table for any rows with that `signer_key_id`).
- Legal or regulatory instruction requires purging the key material
  itself, not just the signing capability.

In that case:

1. Confirm `SELECT COUNT(*) FROM forensic_attestations WHERE
   signer_key_id = '<version>';` returns zero.
2. Disable the version first, wait at least 24 hours, confirm no
   attestations appear during that window.
3. `gcloud kms keys versions destroy <VERSION_RESOURCE_PATH>`.
4. Document the decision in the incident tracker with the legal/
   regulatory reference that required the destruction.

GCP defers actual destruction by 24 hours by default — that window is
the last chance to reverse a mistake via `gcloud kms keys versions
restore`.

## Rotation cadence

There is currently **no scheduled rotation**. GCP's documented
guidance for asymmetric signing keys treats rotation as an
operator-triggered event, not a periodic one, because:

- Each rotation creates a new `kid` that verifiers must learn about.
- Operational risk of a botched rotation outweighs the marginal
  security benefit of scheduled rotation on a low-use key.
- We rotate when we have a reason to: suspected compromise, policy
  change, or an auditor asking.

If that posture changes (for example, a customer's compliance
framework requires annual rotation), update this section and post a
briefing.

## Escalation

- Cryptographic questions → CTO
- GCP IAM / KMS permission issues → see setup script for the admin
  principal; failures here usually mean a role binding was removed
- Customer-facing impact from a botched rotation → file incident in
  `docs/incident-response/`, page on-call
