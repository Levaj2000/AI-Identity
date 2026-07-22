# OCSF Agentic Telemetry — Production Reference Bundle

Reference logs from the **AI Identity gateway**, emitted as **OCSF API Activity (`class_uid` 6003)** events under the **`ai_operation` + `record_integrity`** profiles. Shared as concrete, schema-conformant artifacts to back the CMF↔OCSF alignment work (CoSAI WS4 / OCSF AI WG).

The point of this bundle: the OCSF agentic spec isn't theoretical here — it's the wire format of a running system. These are real exports, not hand-written examples.

This revision tracks the **final OCSF PR #1661 attestation shape** (as merged in review, schema commit `fa4003ad`): fingerprint-object hashes, a required `signatures` array, `attestation.uid`, and the `record_integrity` profile. The earlier draft shape (string `entry_hash`, singular `signature`, a `sequence` field) that the 2026-06-16 version of this bundle used is gone from both the schema and production.

> **Scope / disclosure (please read):** This is a **demo/QA org** (`org_id f3576cf6…`, agents named `demo-agent-*` / `QA-*`, one synthetic user). No customer data, PII, or secrets. Identifiers are opaque UUIDs. Two integrity mechanisms appear in each event, and they are different on purpose:
> - the **hash chain** is **HMAC-SHA-256 (keyed)** — values are real and internally consistent, but *recomputing* them requires the org's key (key-holder verifiable);
> - the **per-event signature** is **ECDSA-P256-SHA256, publicly verifiable** — the export path signs each event's `entry_hash` with the production KMS key, and the public key is published at `https://api.ai-identity.co/.well-known/ai-identity-public-keys.json` (`kid` = the event's `unmapped.signature_key_id`). `regenerate.py` in this directory verifies every signature in the bundle against that JWKS with no secrets.

---

## Files

| File | What it is | Use |
|---|---|---|
| `production-ocsf-excerpt.ocsf.ndjson` | **7-event annotated slice** (`org_chain_seq` 16–22), a single agent's lifecycle | Start here — read top to bottom with the walkthrough below |
| `production-ocsf-full-export.ocsf.ndjson` | <!-- REGEN:STATS --> **Full org chain**, 193 events, seq 1→193, 34 agents (115 allowed / 78 denied) <!-- /REGEN:STATS --> | The real raw export from the `format=ocsf` endpoint |
| `regenerate.py` | Rebuilds this bundle from a fresh `format=ocsf` download: validates the final #1661 shape, verifies the chain, verifies every ECDSA signature against the public JWKS, refreshes this README | `python3 regenerate.py <fresh-export.ndjson>` |

> **Retired:** `signed-chain-ecdsa-example.json` (the hand-built ECDSA/JCS worked example from the 2026-06-16 bundle). It existed to show the *target* asymmetric shape while production only had the HMAC chain. Production now emits real per-event ECDSA signatures in the export itself (`attestation.signatures` + `unmapped.signature_b64`), so the mock was redundant — and it carried draft-era fields (`sequence`, singular `signature`) that no longer exist in #1661.

Format is **NDJSON** — one OCSF event per line, the de-facto SIEM ingestion shape (Splunk HEC etc.). Each event is produced by `audit_log_to_ocsf()` in `common/ocsf/api_activity.py`; the export path signs each event at download time (`_sign_export_entries()` in `api/app/routers/audit.py`).

---

## Walkthrough — `production-ocsf-excerpt.ocsf.ndjson`

One agent (`QA-eae97318`, uid `32928870…`), seven consecutive gateway events. Read as a story:

| seq | action | operation | why it matters |
|---|---|---|---|
| 16 | **Allowed** | `POST /api/v1/agents` | agent created |
| 17 | **Denied** | `POST /v1/chat/completions` | inference blocked — **no active policy** yet (`severity_id` 3) |
| 18 | **Allowed** | `POST /v1/chat/completions` | now permitted — note `unmapped.policy_version: 10` |
| 19 | **Denied** | `DELETE /v1/admin/secrets` | privileged op denied under the same policy |
| 20 | **Allowed** | `POST …/keys/rotate` | key rotation allowed |
| 21 | **Allowed** | `DELETE /api/v1/agents/…` | agent decommissioned |
| 22 | **Denied** | `POST /v1/chat/completions` | post-decommission call refused |

**Each event's `attestation.prev_entry_hash.value` equals the previous event's `attestation.entry_hash.value`** — a tamper-evident chain. Verified structurally in this bundle (excerpt seq 16→22 link internally; the full export links genesis→end). Excerpt event 16's `prev_entry_hash` points at seq 15 in the full export (it starts mid-chain). The chain hashes are computed at **write time** and stored; they are identical to the values in the 2026-06-16 bundle — what changed is the *envelope* (fingerprint objects) and the *signatures* (added at export time).

### Anatomy of one event (the allowed inference)

<!-- REGEN:ANATOMY -->
```json
{
  "activity_id": 1,
  "category_uid": 6,
  "class_uid": 6003,
  "type_uid": 600301,
  "severity_id": 1,
  "time": 1776094414825,
  "metadata": {
    "uid": "99",
    "version": "1.9.0-dev",
    "profiles": [
      "ai_operation",
      "record_integrity"
    ]
  },
  "action": "Allowed",
  "action_id": 1,
  "api": {
    "operation": "/v1/chat/completions"
  },
  "http_request": {
    "http_method": "POST",
    "url": {
      "path": "/v1/chat/completions"
    }
  },
  "ai_agent": {
    "uid": "32928870-56a1-4518-be76-7e99bfcdeac4",
    "name": "QA-eae97318"
  },
  "duration": 182,
  "actor": {
    "user": {
      "uid": "a33fb1e9…",
      "type_id": 1
    }
  },
  "attestation_list": [
    {
      "uid": "99",
      "fingerprint": {
        "algorithm_id": 99,
        "algorithm": "HMAC-SHA-256",
        "encoding_id": 1,
        "serialization_id": 99,
        "serialization": "AI-Identity audit chain v1 (sorted-compact JSON + prev hash)",
        "value": "1d9548729d942e30…"
      },
      "prev_event": {
        "uid": "98",
        "type_uid": 600301,
        "fingerprint": {
          "algorithm_id": 99,
          "algorithm": "HMAC-SHA-256",
          "encoding_id": 1,
          "serialization_id": 99,
          "serialization": "AI-Identity audit chain v1 (sorted-compact JSON + prev hash)",
          "value": "90ba42f3b92586ff…"
        }
      },
      "chain_uid": "f3576cf6-87ff-4c07-b446-e6ac526236a5",
      "signatures": [
        {
          "algorithm_id": 3,
          "algorithm": "ECDSA-P256-SHA256",
          "serialization_id": 1,
          "serialization": "Flat",
          "created_time": 1784755487529,
          "digest": {
            "algorithm_id": 99,
            "algorithm": "HMAC-SHA-256",
            "encoding_id": 1,
            "serialization_id": 99,
            "serialization": "AI-Identity audit chain v1 (sorted-compact JSON + prev hash)",
            "value": "1d9548729d942e30…"
          }
        }
      ]
    }
  ],
  "unmapped": {
    "signature_b64": "MEUCIE7U6pS4ADjqn71SwQH6…",
    "signature_key_id": "projects/…/cryptoKeys/session-attestation/cryptoKeyVersions/1",
    "org_chain_seq": 18,
    "policy_version": 10
  }
}
```
*(long hex/base64 values truncated for display — the ndjson files carry full values; seq 18)*
<!-- /REGEN:ANATOMY -->

Field notes:
- **`action` / `action_id`** — the **policy decision** on the wire (Allowed=1, Denied=2). This is the same allow/deny that a CMF→PDP evaluation produces; here it's the durable record of it.
- **`metadata.profiles`** — `ai_operation` always; `record_integrity` is declared whenever the `attestation` object is emitted (that profile is what defines the object in #1661).
- **`ai_agent.uid`** — the agent's stable identity (merged `ai_agent` object, PR #1641 placement).
- **`actor.user`** — the human/principal behind the call (`type_id` 1 = User).
- **`duration`** — gateway latency in ms. This is its *native* OCSF home (base `duration`), per the CMF↔OCSF crossmap — resolved from the open question in the earlier bundle; it does not ride `unmapped`.
- **`attestation`** — record-integrity provenance, final #1661 shape:
  - `uid` — the audit row id (stable join key back to the source record);
  - `entry_hash` / `prev_entry_hash` — **fingerprint objects**, `algorithm_id` **99 (Other)** with `algorithm: "HMAC-SHA-256"`. Deliberate: the chain hash is *keyed* HMAC, and claiming plain `SHA-256` (`algorithm_id` 3) would misstate the construction. This is exactly the kind of honesty the fingerprint `algorithm` sibling exists for;
  - `chain_uid` — the org chain identifier;
  - `signatures[]` — required by the final schema. One ECDSA-P256-SHA256 signature per event, computed over `bytes.fromhex(entry_hash.value)` at export time (`created_time` is the export timestamp, not the event timestamp — the signature attests the record as downloaded). Same message convention as our Evidence Anchor Merkle leaves, so one public key + one message rule covers both.
- **`unmapped.signature_b64` / `unmapped.signature_key_id`** — the actual signature bytes (base64 DER) and the KMS key resource that made them. They ride `unmapped` because OCSF's `digital_signature` object **has no field for signature bytes or key id** — a live gap worth raising (see table below). `signature_key_id` matches a `kid` in the public JWKS, which is how a third party verifies without trusting us operationally.
- **`unmapped` (rest)** — producer facts with **no OCSF home today**: `org_chain_seq`, `policy_version`, `cost_estimate_usd`. These are exactly the signals the alignment work needs to give a first-class home.

### Verify it yourself (no secrets needed)

```bash
python3 regenerate.py production-ocsf-full-export.ocsf.ndjson --bundle-dir /tmp/check
# ✓ shape · ✓ chain linkage · ✓ every ECDSA signature against the public JWKS
```

---

## Where this maps to the CMF↔OCSF gaps we discussed

This export is the evidence behind the gap list — every gap below is something the gateway *already emits or decides* but OCSF has nowhere clean to put:

| Gap (from the 2026-06-16 sync) | Where it shows up here |
|---|---|
| **MCP tool/resource/prompt metadata** | tool-style endpoints (`…/keys/rotate`, `/v1/admin/secrets`) ride in `api.operation` today — no structured MCP slot. A `message_context` extension would home CMF's MCP slot. |
| **Agentic framework context** | nothing in OCSF carries it; would pair with the MCP addition. |
| **Workload attestation state** | distinct from the record-integrity `attestation` object shown here — that's a separate first-class signal (don't conflate record non-repudiation with workload/TEE attestation). |
| **Correlation ID / delegation path** | `metadata.correlation_uid` exists (not populated in this demo slice); delegation lineage is the bigger open mapping. |
| **Completion `stop_reason`** | absent from OCSF; would attach to the inference events (seq 17/18/22). |
| **Policy version / decision provenance** | currently in `unmapped.policy_version` — candidate for a real field. |
| **Signature bytes / key id** *(new since #1661 final)* | `digital_signature` describes a signature but can't carry it: no bytes field, no key-id field. Producers that actually sign (like this export) are forced into `unmapped.signature_b64` / `unmapped.signature_key_id`. |

*(Resolved since the last bundle: gateway latency — OCSF base `duration` is its native home; we now map it there.)*

---

## Honest limitations (no overclaim)

- **The chain and the signatures verify different things.** The ECDSA signature proves *AI Identity's signer attested to this entry hash* — publicly checkable via the JWKS. Recomputing the chain hash itself from raw row content still requires the org's HMAC key (key-holder verifiability). Structural linkage (`prev_entry_hash` → `entry_hash`) is checkable by anyone.
- **Signatures are export-time.** `signatures[0].created_time` stamps when the export was generated, not when the event occurred; event time is `time`, and the write-time integrity is the chain hash.
- **Demo data.** Throwaway org; volumes/agent names are synthetic.
- **`correlation_uid` / delegation** are present in the schema path but not exercised in this slice.
- **Genesis sentinel.** The chain's first event (seq 1) carries the literal string `GENESIS` in `prev_entry_hash.value` — the stored chain-start sentinel passed through verbatim. Strictly, a fingerprint object's `value` should be a hash; we're flagging this openly rather than editing the export. The likely producer fix is to omit `prev_entry_hash` on the genesis row (it has no predecessor to point at) — and it's a useful WG data point: sentinel values inside `fingerprint` are an anti-pattern the spec text could warn about.

---

*Generated for CoSAI WS4 / OCSF AI WG collaboration. Schema: OCSF 1.9.0-dev, API Activity 6003, `ai_operation` + `record_integrity` profiles (#1661 final shape @ `fa4003ad`; emitter: AI-Identity PR #370). Source: AI Identity gateway audit export (`format=ocsf`).*
