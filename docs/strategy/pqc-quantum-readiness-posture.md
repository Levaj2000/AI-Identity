# AI Identity — Quantum-Readiness Posture

*One-page statement · v1.0 · 2026-06-29 · Audience: IBM / CoSAI WS4 / OCSF collaborators + prospective customers*

## Summary

AI Identity's signing surfaces are **crypto-agile by design** — the signature
algorithm is a parameter, not a hard-coded assumption — and we have already
implemented and tested a **post-quantum (ML-DSA-87) verification path**. We are
ahead of the federal timeline, and we say precisely what is shipped versus
designed versus enabled, so nothing here is aspirational marketing.

## Why now

- **Federal PQC Executive Order (2026-06-22)** directs agencies and their
  vendors toward post-quantum cryptography; the federal digital-signature
  migration target is **2031**.
- **CISA "CBOM minimum elements"** are due ~December 2026 — vendors will be
  expected to enumerate their cryptography in a machine-readable bill of
  materials.
- NIST finalized the PQC signature standard **FIPS 204 (ML-DSA)** in 2024.

## Our posture (crypto-agile by design)

- **Algorithm-as-parameter.** Every signature carries an explicit algorithm
  identifier (`SignatureAlgorithm` enum); the verifier dispatches on it rather
  than assuming one algorithm.
- **Deterministic, versioned payloads.** Signed content is canonicalized with
  **RFC 8785 (JCS)** and stamped with a `schema_version`, so an algorithm
  upgrade is detectable and verifiable, not a silent break.
- **Hybrid-tolerant verifier.** A mandate may carry multiple signatures
  (e.g. classical ECDSA-P256 **and** ML-DSA-87); verification accepts a hybrid
  or a single-algorithm envelope without code changes.
- **Cryptographic Bill of Materials.** We publish a **CycloneDX 1.6 CBOM**
  enumerating every algorithm, key, and library across our signing,
  verification, integrity, and encryption surfaces — already aligned to the
  format the CISA rule is being built around.

## What is true *today* (verified)

| Capability | Status |
|---|---|
| Classical signing (ECDSA-P256 / SHA-256), KMS-backed | **In production** (mandates + Evidence Anchor checkpoints) |
| ML-DSA-87 (FIPS 204) **verification** path | **Implemented and tested** — verify-only |
| Machine-readable CBOM (CycloneDX 1.6) | **Published** in-repo, drift-guarded by tests |
| Crypto-agility primitives (enum, JCS, schema_version, hybrid verifier) | **In production** |

## What we are **not** claiming (no vaporware)

- We do **not** issue PQC-signed artifacts. ML-DSA-87 is **verify-only; there is
  no PQC signing/issuance** yet.
- The ML-DSA-87 verifier is **opt-in and inert by default** — it activates only
  when an operator configures a trusted PQC key, and it is **not enabled in any
  deployed environment** today.
- Production signatures remain **classical ECDSA-P256**. We are *ready* to
  verify post-quantum signatures, not *running* on them.

## Direction (not a commitment of dates)

Hybrid issuance (classical + ML-DSA-87) is the natural next step once a real
verifier-side need exists; the agility design means it is an additive change,
not a migration project. We track the FAR contractor-PQC rule and CISA CBOM
minimum elements (~Dec 2026) and will align the CBOM format when the draft
lands.

---

### Reviewer's note — what to watch for

- **Code-state claims:** "implemented and tested" for ML-DSA-87 refers to the
  *verify* path landed in the Mandate Service (opt-in, not deployed). If this
  one-pager is reused after further work ships, re-confirm the "true today"
  table against the codebase — do not let "verify-only / not enabled" drift into
  an implied "running in production."
- **The 2031 / EO framing** is accurate as of 2026-06-29; if cited later, verify
  the dates haven't been superseded.
- **"Ahead of the timeline"** is a defensible posture claim (agility + verify
  capability), *not* a claim of PQC-signed production traffic. Keep that
  distinction intact in any sales adaptation.
- **Audience calibration:** for IBM/CoSAI/OCSF (technical), the honesty is the
  credibility asset — lead with it. For sales, the same facts hold; do not
  upgrade "ready to verify" into "quantum-proof."
