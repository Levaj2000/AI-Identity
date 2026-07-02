# AI Identity — Implementation Examples for the Agentic IAM Cookbook

**A candidate entry for the implementation index alongside Auth0 / Entra / Okta.**
Not a bridge to an enterprise IdP — a self-contained stack (agent keys + Mandate
Service + OCSF) that implements the same layered pattern end to end. Offered as
one more concrete, machine-checkable option for teams that don't run one of
those three.

> Companion to `practical-guides/Identity-Architecture-Patterns-for-Agentic-Systems.md`
> (PR #116) and `docs/cosai-ws4-ocsf-mapping/MAPPING.md`.

## How this maps to the three-layer pattern

| Layer | AI Identity artifact | Status |
|---|---|---|
| 1. Cryptographic identity | Agent key issuance + mTLS hardware attestation at registration | **Shipped** |
| 2. Verifiable agent credential | Mandate Service (signed, scoped delegation grant) | **Shipped** |
| 3. Federated identity bridge | OIDC / Workload Identity Federation | Design spike — not shown here (no route/persistence yet) |
| Observable trust | OCSF signed, hash-chained event export + offline verifier CLI | **Shipped** |

Each example below is a real field shape from running code, not a mockup — file
references included so anyone can check it against source.

---

## 1. Cryptographic identity — attestation at registration

`common/attestation/schemas.py` — an agent may present an mTLS client
certificate at registration. It's verified against a configured trusted CA and
the result is bound to the agent record.

```json
{
  "attestation_type": "mtls_cert",
  "verified": true,
  "reason": "cert chains to trusted CA, within validity window",
  "subject": "spiffe://ai-identity.co/agent/demo-agent-mn7msq4n",
  "issuer": "CN=AI Identity Trusted CA",
  "public_key_sha256": "e3b0c44298fc1c149afbf4c8996fb92...",
  "not_before": "2026-06-29T00:00:00Z",
  "not_after": "2027-06-29T00:00:00Z"
}
```

- `verified` is only `true` when the evidence cryptographically checks out
  **and** chains to a configured trust anchor — no overclaiming when no trust
  anchor is set.
- `subject` prefers a SPIFFE URI (SAN) if present, falling back to the cert's
  subject DN.
- This is the concrete implementation of the OCSF workload-attestation gap
  proposed alongside PR #1661 — kept distinct from record-integrity (below),
  since "is the credential trustworthy" and "is the record intact" are
  different questions.

## 2. Verifiable agent credential — a Mandate

`mandate/app/schemas.py` — a signed, scoped delegation grant, MongoDB-backed,
with a defined lifecycle (`active → revoked → expired`).

```json
{
  "mandate_id": "mnd_a1b2c3d4",
  "schema_version": "1.0",
  "status": "active",
  "issuer": { "org_id": "f3576cf6-87ff-4c07-b446-e6ac526236a5", "user_id": "usr_abc" },
  "subject": { "agent_id": "274a3fcf-480c-4630-a4a6-9f67c3ccf0cc", "org_id": "f3576cf6-87ff-4c07-b446-e6ac526236a5" },
  "scope": ["read:audit", "write:policies"],
  "valid_from": "2026-07-02T00:00:00Z",
  "valid_until": "2026-12-29T00:00:00Z",
  "signatures": [
    { "algorithm": "ecdsa-p256-sha256", "key_id": "local:...", "signature": "..." }
  ]
}
```

- `signatures` is an array by design — classical (ECDSA-P256, live today) and
  post-quantum (ML-DSA, reserved slot) can co-exist for hybrid signing.
- `scope` is a flat permission list; `conditions` (not shown) carries ABAC-style
  constraints when present.

## 3. Observable trust — a signed, hash-chained OCSF event

`docs/cosai-ws4-ocsf-mapping/case-file-org-f3576cf6-2026-06-16.ocsf.ndjson` —
real (synthetic-data) export, one OCSF event per line. This is the same agent
and org as the two examples above, continuing the story: attested at
registration, granted a mandate, and now its actions are on the record.

```json
{
  "activity_id": 1, "category_uid": 6, "class_uid": 6003, "type_uid": 600301,
  "action": "Allowed", "time": 1774539159723,
  "metadata": { "version": "1.9.0-dev", "profiles": ["ai_operation"] },
  "ai_agent": { "uid": "274a3fcf-480c-4630-a4a6-9f67c3ccf0cc", "name": "demo-agent-mn7msq4n" },
  "attestation": {
    "entry_hash": "ccc5caa486356183049476cc88c6da990d4fd970a0da7f0cb5e114ffe95fce45",
    "prev_entry_hash": "GENESIS",
    "chain_uid": "f3576cf6-87ff-4c07-b446-e6ac526236a5"
  }
}
```

- `prev_entry_hash` chains each event to the one before it — a break anywhere
  in the chain is detectable without needing to trust the exporter.
- Independently, offline: `pip install` nothing extra, single stdlib-only file.

```bash
AI_IDENTITY_HMAC_KEY="<org signing key>" \
  python3 cli/ai_identity_verify.py report case-file-org-f3576cf6-2026-06-16.json
```

Exit code `0` = chain intact and signature valid; `1` = tampered or broken;
`2` = usage error. Suitable for CI.

---

## Notes for whoever picks this up

- Full field-by-field walkthrough (7-event agent lifecycle) already exists at
  `docs/cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle/README.md` — link
  there for the deep version, keep this doc as the short index entry.
- The federation/bridge layer is intentionally not shown with a JSON example —
  it's a tested pattern sketch (`common/auth/federation.py`), not wired to a
  route yet. Don't add a JSON shape for it until that changes.
- Demo data (agent/org UIDs, hashes) is synthetic, generated for this bundle —
  fine to say so if asked.
