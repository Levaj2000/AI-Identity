# OIDC / Workload Identity Federation for Agent Credentials — Design + Spike

*Sprint 17 #422 · 2026-06-29 · status: design + spike (not wired to routes)*

## Problem

AI Identity issues agents a static bearer secret (`aid_sk_...`). Even with the
default TTL added in #413, a stored long-ish-lived secret is an unattractive
credential for a federated customer: it must be stored, it is a standing
liability if leaked, and it does not ride the customer's own identity system.

Anthropic shipped **Workload Identity Federation (WIF)**: an agent presents a
short-lived OIDC JWT minted by *its own* identity provider and receives a
short-lived, scoped token in exchange — no stored secret (Insight #101). To stay
credible as the agent record/identity layer, AI Identity should accept the same
pattern.

## The exchange

```
agent ──OIDC assertion──▶  AI Identity
                           1. verify_assertion   signature + iss + aud + exp (PyJWT + issuer JWKS)
                           2. resolve_agent       verified claims ──▶ AI Identity agent_id
                           3. issue_token         short-lived, scoped AI Identity token
                  ◀──short-lived token──
```

This is the same verification primitive the Clerk **user**-auth path already
uses (`PyJWT` + `PyJWKClient`, RS256) — generalized to per-issuer config with an
audience, a claim→agent mapping, and a subject allowlist.

### Registered issuer (`FederatedIssuer`)

| Field | Purpose |
|---|---|
| `issuer`, `jwks_uri`, `audience` | Standard OIDC trust anchors; all three are enforced. |
| `agent_id_claim` | If set, the agent_id is read directly from this claim. |
| `subject_to_agent` | Otherwise, map the `sub` claim to an agent_id. |
| `allowed_subjects` | Optional allowlist — defence in depth beyond a valid signature. |
| `algorithms` | Accepted signature algorithms (default `RS256`). |
| `default_scopes` | Scopes granted to the minted token. |

### Minted token

A **self-contained, short-lived signed JWT** (default 5-minute TTL), *not* a
stored `aid_sk_` key — nothing to persist, and the credential cannot outlive its
TTL. That is the entire point of federation.

## What the spike proves (`common/auth/federation.py`, `test_federation.py`)

Pure, injectable functions (`verify_assertion` / `resolve_agent` / `issue_token`
/ `federate`) exercised end-to-end with a local RSA keypair standing in for the
IdP. 10 tests cover the happy path (valid assertion → verifiable short-lived
token), claim-based and subject-map agent resolution, and rejection of tampered,
expired, wrong-audience, wrong-issuer, unmapped, and non-allowlisted assertions,
plus tamper/wrong-secret rejection of the issued token.

## What productionizing requires (deferred)

1. **Issuer registry + admin** — persist `FederatedIssuer` configs per
   org/customer (currently constructed in-process). New endpoints to register,
   list, and revoke issuers.
2. **HTTP exchange route** — e.g. `POST /api/v1/agents/token` that accepts an
   OIDC assertion and returns the short-lived token; integrate into
   `agent/serve.py` and the gateway auth dependency so a federated token is
   accepted alongside `aid_sk_` keys.
3. **Asymmetric token signing** — the spike signs the minted token with HS256
   (shared secret). Production should sign with an asymmetric key (reuse the
   KMS-backed forensic signer / JWKS) so verifiers need no shared secret —
   consistent with the Evidence Anchor public-verifiability model.
4. **JWKS caching + rotation + clock skew** — `PyJWKClient` caches keys; add a
   refresh/rotation policy and a small `leeway` for clock skew.
5. **Scope model** — reconcile `default_scopes` with the existing agent
   capability/scope model rather than a free-form string.
6. **Audit** — record each federation exchange (issuer, subject, agent, scopes)
   as an OCSF event in the evidence chain, same as key issuance.

## Why this fits the strategy

This is the portable, record-layer answer to the static-key liability: agents
authenticate via their own IdP, AI Identity verifies and records the exchange,
and the credential that flows is short-lived and scoped. It composes with the
hardware-attestation-at-registration work (#423) — federation handles the
*software* identity assertion; attestation handles the *hardware* root of trust.

---

### Reviewer's note — what to watch for

- **Spike vs shipped:** this is a design + spike. The exchange functions are
  real and tested, but there is **no route, no persistence, and no
  `agent/serve.py` wiring** — do not describe federation as a live capability.
- **HS256 in the spike** is a deliberate shortcut for a self-contained test; the
  shared-secret token is *not* the production design (item 3 above). Don't ship
  HS256 token signing.
- **Claim→agent mapping is a trust boundary:** whoever can register an issuer or
  influence its claims can assert an agent identity. The issuer registry admin
  path (deferred) needs the same scrutiny as key issuance.
- **Strategic claim check:** "mirrors Anthropic WIF" is accurate at the pattern
  level (OIDC assertion → short-lived scoped token); it is not a claim of
  feature parity with their implementation.
