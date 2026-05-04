# AI Identity — Command-Line Tools

Two CLIs live here, with overlapping audiences but different purposes:

| Tool | Network | Purpose |
|------|---------|---------|
| `ai_identity_verify.py` | **Offline** | Auditors / customers verify a forensic export without trusting the AI Identity server |
| `aid.py` | **Online** | Operators / founders review live audit activity for an agent — "what did persona X do this week?" |

If you want to verify a forensics export you were handed, jump to [Offline Verification CLI](#ai-identity--offline-verification-cli).
If you want to read live audit logs from the running platform, see [aid — Live Audit Review CLI](#aid--live-audit-review-cli).

---

## `aid` — Live Audit Review CLI

`aid.py` queries the live AI Identity API and prints a per-agent audit table plus an optional chain-integrity check. Designed for the daily dogfood loop and for evaluators who want to see "yes, every action this agent took is signed and chained."

### Bootstrap

```bash
# Auth: today the API still accepts the legacy "email-as-key" path on the
# X-API-Key header. A first-class developer-key flow is on the roadmap; until
# then the value to use is your account email.
export AI_IDENTITY_ADMIN_KEY="you@example.com"

# Optional: point at a non-prod API
export AI_IDENTITY_API_URL=https://api.ai-identity.co   # default

# httpx is the only runtime dependency
pip install httpx
```

If `AI_IDENTITY_ADMIN_KEY` is unset the CLI exits with a hint that includes the bootstrap example, so a fresh operator can self-serve in one step.

### Commands

```bash
# Discover the canonical agent names + UUIDs (good first call on any new env)
python cli/aid.py agents

# Read the last 7 days of audit entries for an agent (alias OK)
python cli/aid.py audit --agent cto --since 7d
python cli/aid.py audit --agent cto-agent --since 7d   # exact name OK
python cli/aid.py audit --agent <UUID> --since 24h     # UUID also OK

# Add an integrity check
python cli/aid.py audit --agent ada --since 14d --verify-chain

# Wider window
python cli/aid.py audit --agent pm --since 30d --limit 200
```

### Persona name aliases

Skill-style names map to the registered agent names automatically:

| You type | Resolves to |
|---|---|
| `cto` | `cto-agent` |
| `pm` | `pm-agent` |
| `marketing` | `marketing-agent` |
| `security` | `security-agent` |
| `sales` | `sales-agent` |
| `ceo` | `ceo-agent` |
| `ada` | `ada` (no suffix) |
| `webhook-receiver` | `webhook-receiver` (no suffix) |

When an alias is applied the CLI prints `note: resolved 'cto' → 'cto-agent'` to stderr so you know what was matched. For agents without a known alias, `aid` will also try `<name>-agent` as a fallback before erroring.

### Notes

- Webhook-driven briefings (e.g. CEO Dashboard → AI Identity audit forwarder) appear under the `webhook-receiver` agent **by design**. See Insight #71.
- `--since` accepts compact durations: `7d`, `24h`, `30m`, `90s`.
- Exit codes: `0` success, `1` HTTP/network error, `2` usage / not-found / ambiguity.

### Testing

```bash
cd cli
python -m pytest test_aid.py -v
```

Tests are network-free — `httpx.Client` is mocked.

---

# AI Identity — Offline Verification CLI

Standalone tool for auditors, incident responders, and customers to verify AI Identity forensic exports **completely offline** — no database, no API, no network access required.

## Why This Matters

AI Identity maintains a cryptographic chain of custody over every API request an AI agent makes. When you export a forensics report, it includes an HMAC-SHA256 signature that proves the report has not been tampered with since it was generated. The audit log entries are individually chained — each entry's hash incorporates the previous entry's hash, so any insertion, deletion, or modification of a single entry is detectable.

This CLI lets you verify both of those guarantees **independently**, without trusting the AI Identity server or having any network access. You only need the exported file and the HMAC secret key.

## Installation

No installation required. Copy a single file:

```bash
cp cli/ai_identity_verify.py /usr/local/bin/ai_identity_verify
chmod +x /usr/local/bin/ai_identity_verify
```

**Requirements:**

- **`report` and `chain` commands:** Python 3.9+, stdlib only — no `pip install` needed.
- **`attestation` command:** additionally requires the [`cryptography`](https://cryptography.io) package for ECDSA verification. Install with `pip install cryptography`. The other two commands continue to work without it.

## Quick Start

```bash
# Set the HMAC key (same key used by the AI Identity server)
export AI_IDENTITY_HMAC_KEY='your-hmac-secret-key'

# Verify a forensics report's chain-of-custody certificate
python ai_identity_verify.py report forensics_report.json

# Verify the full HMAC chain of audit log entries
python ai_identity_verify.py chain audit_export.json

# Get detailed output
python ai_identity_verify.py chain audit_export.json --verbose

# Machine-readable JSON output (for CI/automation)
python ai_identity_verify.py report forensics_report.json --json
```

## Commands

### `attestation` — Verify a Forensic Attestation Envelope

Verifies the ECDSA-P256 signature on a DSSE envelope returned by
`GET /api/v1/sessions/{session_id}/attestation`. This is the
crypto-signed equivalent of the HMAC `report` certificate — it proves
AI Identity signed a specific statement about a specific audit range,
verifiable offline with only the public key.

```bash
# Using a locally-pinned PEM public key
python ai_identity_verify.py attestation envelope.json --pubkey signer.pem

# Using a JWKS file (fetched once from /.well-known/ai-identity-public-keys.json)
curl https://api.ai-identity.co/.well-known/ai-identity-public-keys.json > keys.json
python ai_identity_verify.py attestation envelope.json --jwks keys.json
```

**What it checks:**

1. `payloadType` equals the AI Identity attestation MIME type
2. Exactly one signature is present
3. `schema_version == 1` (rejects v2+ loudly rather than silently)
4. `(first_audit_id, last_audit_id, event_count)` are consistent
5. Reconstructs the DSSE pre-authentication encoding and verifies the
   ECDSA-P256 signature against the supplied public key

**Example output (valid):**
```
AI Identity — Attestation Verification
═════════════════════════════════════════
  File:         envelope.json
  Schema:       v1
  Key ID:       projects/.../cryptoKeyVersions/1
  Session:      b8f2c1a0-4e6d-4e2a-9f1a-3c2b0d4e8f7a
  Org:          f1e2d3c4-b5a6-4798-8877-66554433abcd
  Audit range:  104821..104827 (7 events)
  Chain hash:   3b7e0a6f4a9d8c2e5b1f0d3c6a8b9e2d1f4c7a0b3d6e9f2a5c8b1d4e7a0b3c6d
  Signed at:    2026-04-17T13:47:30+00:00

  Signature:    VALID ✓
```

**What this does NOT do:** walking the HMAC audit chain to confirm the
committed `evidence_chain_hash` matches the actual rows. That's the
`chain` subcommand's job — run both for full end-to-end verification.

### `report` — Verify Chain-of-Custody Certificate

Verifies the HMAC-SHA256 signature on an exported forensics report. This confirms that the report metadata (report ID, timestamp, chain verification result) has not been altered since the report was generated.

```bash
python ai_identity_verify.py report <file.json>
```

**What it checks:**
- Reads `report_id`, `generated_at`, `chain_valid`, `total_entries`, `entries_verified`, and `report_signature` from the file
- Recomputes the HMAC-SHA256 signature over the canonical payload
- Compares using constant-time comparison

**Example output:**
```
AI Identity — Report Verification
══════════════════════════════════
  Report ID:    fr-a1b2c3d4-20260310
  Generated:    2026-04-08T21:10:37+00:00
  Entries:      1248 total, 1248 verified
  Chain Valid:  ✓

  Signature:    VALID ✓
```

### `chain` — Verify Full HMAC Audit Chain

Walks the sequential HMAC chain from first to last entry and verifies each link. This confirms that no entries have been added, removed, or modified.

```bash
python ai_identity_verify.py chain <file.json>
```

**Accepts:**
- A JSON array of audit log entry objects
- A forensics report JSON (entries are extracted from the `events` key)

**What it checks for each entry:**
1. `prev_hash` matches the previous entry's `entry_hash` (or `GENESIS` for the first)
2. Recomputed HMAC-SHA256 over the canonical payload matches the stored `entry_hash`

**Example output (valid):**
```
AI Identity — Audit Chain Verification
═══════════════════════════════════════
  File:         audit_export.json
  Entries:      1248

  Verifying chain...  [████████████████████████████████] 1248/1248

  Result:       CHAIN INTACT ✓
  Verified:     1248/1248 entries
```

**Example output (broken):**
```
  Result:       CHAIN BROKEN ✗
  Verified:     847/1248 entries
  Break at:     Entry #848
    Entry ID:   42
    Expected:   af0f7d4a2b3c8e91...
    Got:        c3b8e91f7d4a2b3c...
```

## Flags

| Flag | Description |
|------|-------------|
| `--verbose`, `-v` | Show detailed output (full hash values, per-entry info) |
| `--json` | Output results as JSON for CI/automation pipelines |
| `--no-color` | Disable colored terminal output |
| `--version` | Print tool version and exit |

## JSON Output

When using `--json`, the tool outputs a structured JSON object:

```json
{
  "tool": "ai-identity-verify",
  "version": "1.0.0",
  "command": "report",
  "timestamp": "2026-04-10T20:15:00Z",
  "result": "valid",
  "details": {
    "report_id": "fr-a1b2c3d4-20260310",
    "generated_at": "2026-04-08T21:10:37+00:00",
    "total_entries": 1248,
    "entries_verified": 1248,
    "chain_valid": true,
    "signature_valid": true
  }
}
```

## How It Works

### Chain-of-Custody Certificate (Report Signature)

The report signature is an HMAC-SHA256 computed over a canonical JSON payload containing five fields:

```
HMAC-SHA256(key, '{"chain_valid":true,"entries_verified":1248,...,"total_entries":1248}')
```

The payload is JSON-serialized with sorted keys and compact separators (`sort_keys=True, separators=(",", ":")`) to ensure deterministic output regardless of platform.

### HMAC Audit Chain (Entry Linkage)

Each audit log entry contains:
- `entry_hash` — HMAC-SHA256 of the entry's data fields + `prev_hash`
- `prev_hash` — the `entry_hash` of the immediately preceding entry (`GENESIS` for the first)

This creates a sequential chain: modifying, inserting, or deleting any entry causes all subsequent hashes to mismatch. The canonical payload for each entry includes: `agent_id`, `cost_estimate_usd`, `created_at`, `decision`, `endpoint`, `latency_ms`, `method`, `prev_hash`, and `request_metadata`.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Verification passed — signature valid or chain intact |
| `1` | Verification failed — invalid signature or broken chain |
| `2` | Usage error — missing file, invalid JSON, missing HMAC key |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AI_IDENTITY_HMAC_KEY` | Yes | The HMAC secret key used by the AI Identity server. Must match the server's `audit_hmac_key` setting. |
| `NO_COLOR` | No | Set to any value to disable colored output (respects [no-color.org](https://no-color.org) convention). |

## Running Tests

```bash
cd cli
python -m unittest test_verify -v
```

All tests use only the Python standard library.
