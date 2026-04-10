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

**Requirements:** Python 3.9+ (stdlib only — no `pip install` needed).

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
