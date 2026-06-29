# Cryptographic Bill of Materials (CBOM)

A machine-readable inventory of every cryptographic algorithm, key, and
implementing library across AI Identity's signing, verification, integrity,
and encryption surfaces.

- **Artifact:** [`cbom.json`](./cbom.json) — CycloneDX 1.6
- **Generator:** [`generator.py`](./generator.py) — the source of truth
- **Drift guard:** [`../tests/test_cbom.py`](../tests/test_cbom.py)

## Why CycloneDX 1.6

CycloneDX is the OWASP standard with first-class `cryptographic-asset`
components, and CISA's forthcoming **CBOM minimum elements** (~Dec 2026, the
rule Sprint 17 #424 is watching) is being built around it. Aligning now means
"revisit when CISA lands" is a tweak, not a rewrite — and it's the format a
partner (IBM / CoSAI WS4 / OCSF) can ingest with existing tooling.

## Why curated, not auto-derived

Crypto usage is not reliably detectable by static analysis, and a CBOM is a
deliberate *attestation* of what the system uses. So the inventory lives as
structured data in `generator.py`, with each asset carrying `file:line`
occurrences a reviewer can check against the code. The test suite fails if any
cited file is missing or if the committed `cbom.json` drifts from the
generator.

## Coverage (8 crypto assets, 5 libraries)

| Asset | Primitive | Surface | Status |
|---|---|---|---|
| ECDSA P-256 / SHA-256 | signature | Mandate signing; Evidence Anchor checkpoints | live |
| ML-DSA-87 (FIPS 204) | signature | Mandate verification (PQC slot) | **verify-only, opt-in, no issuance** |
| HMAC-SHA256 | mac | Audit integrity chain; internal service auth | live |
| SHA-256 | hash | ECDSA digest; agent-key storage; Merkle; HMAC input | live |
| RFC 6962 Merkle (SHA-256) | hash | Evidence Anchor inclusion proofs | live |
| RS256 (RSA-PKCS1v1.5 / SHA-256) | signature | Clerk user-session JWTs (**not** agent auth) | live |
| Fernet (AES-128-CBC + HMAC-SHA256) | ae | Upstream credential encryption at rest | live |
| CSPRNG (`secrets.token_urlsafe`) | drbg | Agent API key generation | live |

**Out of scope by design:** base64/base64url (encoding, not crypto). RFC 8785
(JCS) is recorded as a *dependency* of the signature assets — the canonical
pre-image is security-relevant — but is not itself a crypto asset.

## Regenerate

```bash
python -m common.cbom.generator          # rewrite cbom.json
python -m common.cbom.generator --check  # CI: fail if cbom.json is stale
```

The output is deterministic — no timestamp or `serialNumber` (both optional in
CycloneDX), sorted keys, stable `bom-ref`s — so regenerating an unchanged
inventory never churns the file. Update the data in `generator.py` whenever a
crypto surface changes, regenerate, and commit both.
