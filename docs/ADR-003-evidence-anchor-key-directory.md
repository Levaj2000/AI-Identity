# ADR-003: Evidence Anchor key directory — per-org isolation, version pinning, JWKS hosting

**Status:** Accepted — Sprint 16 item #407 (gated on spike #406, PR [#343](https://github.com/Pacswil/AI-Identity/pull/343)).
**Date:** 2026-06-25
**Deciders:** Jeff Leva (CEO/CTO)
**Consumes:** spike #406 (`common/forensic/merkle.py`, `anchor_checkpoint.py`), feature #408 / PR [#344](https://github.com/Pacswil/AI-Identity/pull/344) (`anchor_service.py`, `audit_checkpoints` table), [`docs/strategy/design-evidence-anchor.md`](strategy/design-evidence-anchor.md), [`docs/forensics/key-rotation.md`](forensics/key-rotation.md).
**Builds on:** ADR-002 (one signing root for all evidence).

## Context

The Evidence Anchor signs a Merkle root over a batch of audit entries with an asymmetric key, so any third party can verify a single past action offline — with only a published public key + SHA-256, **zero** access to `AUDIT_HMAC_KEY`. The #406 spike de-risked the crypto and #408 productionized it (checkpoint model, anchor service, cron endpoint, Case File proof bundle, CLI verifier).

The spike deliberately **deferred per-org key isolation to this item** (#407) and shipped with one platform key + `org_id` carried inside the signed payload. This ADR closes that deferral. Per the reframed card, it narrows to three questions:

- **(a)** per-**org** asymmetric key isolation vs. one platform key + `org_id` in the signed payload
- **(b)** key-version pinning across rotation in the checkpoint
- **(c)** JWKS hosting / caching for offline verifiers

It does **not** reopen whether to build a witness-cosigned transparency log from scratch — the managed-KMS + published-JWKS path is the chosen substrate (design doc, gate pre-check).

### What already exists (verified in code, 2026-06-25)

This matters because two of the three questions are already answered by shipped code:

- **Signing** — `common/forensic/signer.py`: KMS-backed ECDSA-P256 (`FORENSIC_SIGNING_KEY_ID` = full `…/cryptoKeyVersions/N` path) with a `local:<sha256>` PEM fallback for dev/tests. Both are mutually exclusive and config-validated.
- **Version pinning** — `common/forensic/anchor_checkpoint.py:91`: every checkpoint carries `signer_key_id` (the exact KMS key-version path or `local:<sha256>`), persisted to `audit_checkpoints.signer_key_id` (`common/models/audit_checkpoint.py:88`) **and** to the DSSE envelope's `keyid`. The kid is captured at sign time, so rotation never invalidates an old checkpoint.
- **JWKS** — `common/forensic/jwks.py` + `api/app/routers/forensic_keys.py`: served at `/.well-known/ai-identity-public-keys.json`, `Cache-Control: public, max-age=3600`. `_kms_jwks()` lists **every non-destroyed** key version, so historical kids stay resolvable; destroyed versions are omitted and a verifier that meets one correctly **fails closed** ("kid not published").
- **Per-org forgery resistance already lives one layer down.** Each org has its own symmetric `forensic_verify_key` (`common/models/organization.py:39`). The audit chain is HMAC'd per org; the Merkle leaves are those per-org `entry_hash` values. The asymmetric checkpoint key signs the *root* for public verifiability — it is **not** the thing that stops cross-tenant forgery. That is the crux of decision (a).

## Decision summary

1. **(a) Keep one platform key + `org_id` in the signed payload as the shipped default.** Per-org asymmetric keys are **not** built now. The custody upgrade is specified below as a forward-compatible, opt-in path gated on a real trigger.
2. **(b) Ratify the existing version-pinning design as the standard, and lock it with an invariant test.** No new build beyond a regression guard.
3. **(c) Ratify the existing JWKS hosting, and document an offline-verifier snapshot-pinning practice for air-gapped / court use.** No new endpoint.
4. **This is a two-way door.** The current wire format already carries `signer_key_id` per checkpoint, so a verifier resolves *whatever* kid signed a given checkpoint. Introducing per-org kids later is additive — old platform-key checkpoints keep verifying, new per-org ones resolve their own kid from the same JWKS. We are not painting ourselves into a corner; we are deferring infra we do not yet need.

## (a) Per-org key isolation — the live decision

### What single-platform-key actually exposes

If the platform signing key is compromised, an attacker can sign an **arbitrary Merkle root** and claim it as any org's checkpoint. But to make that root *consistent with real, claimable entries*, the attacker also needs the victim org's `forensic_verify_key` to forge the underlying `entry_hash` chain that the inclusion proof checks against. So a platform-key compromise alone yields a checkpoint over a root nobody can produce a matching inclusion proof for. The forgery-resistance boundary is the **per-org HMAC key**, and that is already isolated.

What per-org asymmetric keys *would* add is a **custody / non-repudiation** property: an org could assert "only my key signs my evidence; the platform operator cannot unilaterally produce a signature attributable to me." That is a real, court-relevant property — but it is a defense-in-depth and custody story, not a gap that lets cross-tenant forgery happen today.

### Considered alternatives

#### One platform key + `org_id` in payload — **chosen (default)**

- **One** key-rotation procedure, **one** JWKS, **one** verifier story. Matches how per-session attestations already work (ADR-002: "one signing root for all evidence").
- `org_id` is authenticated (inside the signed canonical JSON) — verifiers can confirm which org a checkpoint claims, just not via key isolation.
- Honors the card's "prefer the managed-KMS path; do not build key-transparency from scratch."
- **Cost:** weaker custody story for an adversarial-operator threat model. Acceptable until a customer or court actually requires operator-exclusion, because forgery resistance is already per-org at the HMAC layer.

#### Per-org KMS keys + single federated JWKS (org-indexed kid) — **chosen as the deferred upgrade path**

The right shape *if/when* triggered, because it reuses everything already built:

- Provision one ECDSA-P256 KMS key **per org**; `SignerHandle` selects by `org_id`.
- The **same** `/.well-known/…` JWKS publishes all orgs' versions — the kid (full KMS resource path) is already globally unique and already carried in each checkpoint, so offline resolution needs **no** new lookup protocol.
- Per-org rotation is independent (each checkpoint pins its own kid).
- **Cost:** N keys to provision/rotate, larger JWKS, key-provisioning hook at org creation. Real but bounded — and zero wire-format change, which is why deferring is safe.

#### Per-org keys + per-org JWKS endpoints — **rejected**

N separate `/.well-known/` endpoints to host, cache, and CDN-invalidate; N verifier configurations. All the cost of the federated option with worse operability and no extra security. Only attractive if an org demanded to *self-host* its own key directory — a hypothetical we will not pre-build for.

#### Build a witness-cosigned transparency log now — **out of scope / rejected here**

The design doc's full vision (append-only, witness-cosigned tlog). Deferred deliberately: managed KMS + published JWKS already delivers offline third-party verifiability. A cosigned log adds *operator-can't-equivocate* guarantees and is a separate, larger bet — track independently, do not fold into #407.

### Trigger to revisit (a)

Promote the federated per-org-key path from "specified" to "build" when **any** of:

- A design partner / customer contract requires operator-exclusion ("the vendor must not be able to sign our evidence").
- Counsel reviewing a Case File flags single-operator-key custody as an admissibility weakness.
- A regulated-tier SKU lists per-org key custody as a gating feature.

Until then, the seam stays unbuilt by design.

## (b) Key-version pinning — ratify + guard

Already correct: `signer_key_id` pins the exact version at sign time; JWKS publishes all non-destroyed versions; destroyed → fail closed. **Decision:** declare this the standard and add a regression test asserting the invariant *a verifier never needs a key newer than the one named in the checkpoint, and a rotation does not break verification of pre-rotation checkpoints.* No other work.

## (c) JWKS hosting + offline caching — ratify + document

Already correct: cached well-known endpoint, all historical versions, fail-closed on missing kid. **Decision:** keep as-is. Add operator/verifier guidance to [`docs/forensics/`](forensics/): for true air-gapped or court use, a verifier should **pin a local JWKS snapshot** captured at (or after) the checkpoint's `signed_at`, rather than depend on live fetch — this removes any network dependency from the verification story and freezes the key set used, which is the posture a court wants. The 1-hour cache is safe precisely because old versions are never silently dropped.

## Consequences

- **Build now:** (b) invariant test, (c) offline-snapshot doc note, and a code-comment/CHANGELOG update pointing the `#407` deferral markers at this ADR. No schema change, no new endpoint, no new prod secret.
- **Deferred (specified, not built):** per-org KMS keys via federated JWKS, gated on the triggers above.
- **Forward compatibility preserved:** because the kid is per-checkpoint, today's platform-key checkpoints and any future per-org checkpoints coexist under one JWKS and one verifier path.
- **Verifier story stays singular:** fetch JWKS → match `signer_key_id` → verify root → verify inclusion. One path, whether the key is platform-wide or (later) per-org.

## Follow-on items

- (b) regression test for rotation-safe verification — small, this sprint.
- (c) offline JWKS snapshot-pinning note in `docs/forensics/` — small, this sprint.
- Repoint the `#407` deferral comments (`common/forensic/anchor_service.py:18-20`, `anchor_checkpoint.py:16`) and `CHANGELOG.md` at this ADR.
- (Separate, not #407) evaluate witness-cosigned transparency log as its own horizon bet.
