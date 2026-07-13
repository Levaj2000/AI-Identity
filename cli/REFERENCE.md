# `ai-identity-verify` Reference

## Overview

`ai-identity-verify` is a standalone, offline tool for auditors and incident responders to verify the integrity of forensic exports from the AI Identity platform. It requires no database, API, or network access.

Three verification modes:

- `report` — Verify the HMAC chain-of-custody certificate on an exported report.
- `chain` — Verify the sequential HMAC audit chain from exported entries.
- `attestation` — Verify the ECDSA signature on a forensic-attestation DSSE envelope.

Requires Python 3.9+. The current tool version is `1.1.0` (see [`cli/ai_identity_verify.py:34`](ai_identity_verify.py#L34)).

For an overview of all CLIs in this directory, see [`cli/README.md`](README.md).

## Installation

The tool is a single Python script with no required external dependencies for its primary functions.

```bash
# Run it directly:
python3 cli/ai_identity_verify.py --version

# Or install it on your PATH:
cp cli/ai_identity_verify.py /usr/local/bin/ai-identity-verify
chmod +x /usr/local/bin/ai-identity-verify
ai-identity-verify --version
```

Dependencies:

- `report` and `chain` use only the Python 3.9+ standard library.
- `attestation` and `inclusion-proof` additionally require the `cryptography` package:
  ```bash
  pip install cryptography
  ```

## Authentication & key material

Verification requires cryptographic keys. The `report` and `chain` commands use a symmetric HMAC key; `attestation` uses a public key for an asymmetric signature.

| Subcommand | Key type | How to provide |
|---|---|---|
| `report` | HMAC secret | Set `AI_IDENTITY_HMAC_KEY` environment variable |
| `chain` | HMAC secret | Set `AI_IDENTITY_HMAC_KEY` environment variable |
| `attestation` | ECDSA public key | `--pubkey <file.pem>` **or** `--jwks <keys.json>` (mutually exclusive) |

The tool exits with usage error (exit code `2`) if the required key material is not provided.

## Subcommands

### `report`

#### Synopsis

```bash
ai-identity-verify report <file> [--verbose] [--json] [--no-color]
```

#### Description

Verifies the HMAC-SHA256 chain-of-custody certificate on an exported forensics report. Confirms that the report's metadata (report ID, generation timestamp, entry count) and its own chain-verification result have not been altered since the report was generated. It does this by recomputing the HMAC signature over the canonical report payload and comparing it to the `report_signature` field in the file.

#### Flags

| Flag | Type | Required | Description |
|---|---|---|---|
| `file` | string | yes | Path to the JSON report file to verify |
| `--verbose` | flag | no | Show the expected and received hash values on mismatch |
| `--json` | flag | no | Emit results in JSON instead of the human-readable format |
| `--no-color` | flag | no | Disable colored terminal output |

#### Exit codes

- `0` — Signature is valid.
- `1` — Signature is invalid or the report has been tampered with.
- `2` — Usage error (file not found, invalid JSON, HMAC key not set).

#### Example (success)

```bash
export AI_IDENTITY_HMAC_KEY='your-hmac-secret-key'
ai-identity-verify report forensics_report.json
```

```text
AI Identity — Report Verification
══════════════════════════════════
  Report ID:    fr-a1b2c3d4-20260310
  Generated:    2026-04-08T21:10:37+00:00
  Entries:      1248 total, 1248 verified
  Chain Valid:  ✓

  Signature:    VALID ✓
```

#### Example (failure)

```bash
ai-identity-verify report tampered_report.json --verbose
```

```text
AI Identity — Report Verification
══════════════════════════════════
  Report ID:    fr-tampered-id
  Generated:    2026-04-08T21:10:37+00:00
  Entries:      1248 total, 1248 verified
  Chain Valid:  ✓

  Signature:    INVALID ✗

  Expected:  2d3f8a91c4e7b6d50f1a8c3e9d7b4a02
  Got:       7b4ac1e0f9d83b5a6c2e1d4f7a8b9c0d
```

### `chain`

#### Synopsis

```bash
ai-identity-verify chain <file> [--expected-prev-hash <HEX>] [--verbose] [--json] [--no-color]
```

#### Description

Verifies the integrity of an exported audit chain. The tool automatically detects whether the export is a **full chain** (the first entry's `prev_hash` is `GENESIS`) or a **partial chain** (the first entry's `prev_hash` is an arbitrary value).

- **Full chain verification** walks the entire sequence, ensuring each entry's `prev_hash` links to the previous entry's `entry_hash`, and that recomputing the HMAC-SHA256 hash of each entry matches its stored `entry_hash`. This proves no entries were inserted, deleted, or modified.
- **Partial chain verification** verifies the internal integrity and linkage of the entries within the exported file. It cannot prove the slice itself is complete without the preceding entries — unless you supply `--expected-prev-hash` to anchor the first entry to a known prior `entry_hash`.

The command accepts either a bare JSON array of audit entries or a full forensics-report file (the `events` key is extracted automatically).

#### Flags

| Flag | Type | Required | Description |
|---|---|---|---|
| `file` | string | yes | Path to a JSON file containing audit log entries |
| `--expected-prev-hash` | string | no | For partial chains, anchor the first entry to a known prior `entry_hash` |
| `--verbose` | flag | no | Show full hash values on mismatch |
| `--json` | flag | no | Emit results in JSON instead of the human-readable format |
| `--no-color` | flag | no | Disable colored terminal output |

#### Exit codes

- `0` — Chain is intact (full or partial).
- `1` — Chain is broken, tampered, or an `--expected-prev-hash` mismatch occurred.
- `2` — Usage error (file not found, invalid JSON, HMAC key not set).

#### Example (success — full chain)

```bash
export AI_IDENTITY_HMAC_KEY='your-hmac-secret-key'
ai-identity-verify chain audit_export_full.json
```

```text
AI Identity — Audit Chain Verification
═══════════════════════════════════════
  File:         audit_export_full.json
  Entries:      1248
  Mode:         Full (chain starts at genesis)

  Verifying chain...  [████████████████████████████████] 1248/1248

  Result:       CHAIN INTACT ✓
  Verified:     1248/1248 entries
```

#### Example (success — partial chain, single entry)

```text
AI Identity — Audit Chain Verification
═══════════════════════════════════════
  File:         single_entry.json
  Entries:      1
  Mode:         Partial (chain starts at entry #96, not genesis)

  Verifying entry integrity...  [████████████████████████████████] 1/1

  Result:       ENTRY VERIFIED ✓
  Verified:     1/1 entries
  Note:         Entry hash matches HMAC computation.
                Chain linkage cannot be fully verified
                without preceding entries.
```

#### Example (failure — broken chain)

```bash
ai-identity-verify chain audit_export_broken.json
```

```text
AI Identity — Audit Chain Verification
═══════════════════════════════════════
  File:         audit_export_broken.json
  Entries:      1248
  Mode:         Full (chain starts at genesis)

  Verifying chain...  [█████████████████                 ] 847/1248

  Result:       CHAIN BROKEN ✗
  Verified:     847/1248 entries
  Break at:     Entry #848
    Entry ID:   evt_848_abcdef1234567890
    Expected prev_hash: af0f7d4a2b3c8e91d6a4b7c2e8f1d3a05
    Got:                c3b8e91f7d4a2b3c6e8a1b4f7d2c9e0a
```

### `attestation`

#### Synopsis

```bash
ai-identity-verify attestation <file> (--pubkey <PEM> | --jwks <JSON>) [--verbose] [--json] [--no-color]
```

#### Description

Verifies a forensic attestation DSSE (Dead Simple Signing Envelope). The envelope contains a payload and an ECDSA-P256 signature; the command verifies the signature against the supplied public key. The payload's `schema_version`, internal consistency, and `payloadType` are checked before the cryptographic verification step.

#### Flags

| Flag | Type | Required | Description |
|---|---|---|---|
| `file` | string | yes | Path to a JSON file: either a bare DSSE envelope or the full `GET /api/v1/sessions/{id}/attestation` response (unwrapped automatically) |
| `--pubkey` | string | one of | Path to a PEM-encoded ECDSA public key |
| `--jwks` | string | one of | Path to a JWKS file; the key is matched via the `kid` in the envelope |
| `--verbose` | flag | no | Show detailed info including payload bytes and signature encoding |
| `--json` | flag | no | Emit results in JSON instead of the human-readable format |
| `--no-color` | flag | no | Disable colored terminal output |

Exactly one of `--pubkey` or `--jwks` must be supplied.

#### Exit codes

- `0` — Signature is valid.
- `1` — Verification failed (invalid signature, schema mismatch, payload tampered).
- `2` — Usage error (file not found, neither/both of the key flags supplied, `cryptography` not installed).

#### Example (success)

```bash
ai-identity-verify attestation envelope.json --pubkey public_key.pem
```

```text
AI Identity — Attestation Verification
═════════════════════════════════════════
  File:         envelope.json
  Schema:       v1
  Key ID:       projects/ai-identity/locations/global/keyRings/prod/cryptoKeys/attest/cryptoKeyVersions/1
  Session:      b8f2c1a0-4e6d-4e2a-9f1a-3c2b0d4e8f7a
  Org:          f1e2d3c4-b5a6-4798-8877-66554433abcd
  Audit range:  104821..104827 (7 events)
  Chain hash:   3b7e0a6f4a9d8c2e5b1f0d3c6a8b9e2d1f4c7a0b3d6e9f2a5c8b1d4e7a0b3c6d
  Signed at:    2026-04-17T13:47:30Z

  Signature:    VALID ✓
```

#### Example (failure — wrong key in JWKS)

```bash
ai-identity-verify attestation envelope.json --jwks keys.json
```

```text
AI Identity — Attestation Verification
═════════════════════════════════════════
  File:         envelope.json
  Schema:       v1
  ...

  Signature:    INVALID ✗
                signature does not verify against the supplied public key
```

## Common patterns

### Running against an exported JSON file

All subcommands operate on a local JSON file specified as the first positional argument:

```bash
ai-identity-verify report path/to/report.json
ai-identity-verify chain path/to/chain.json
ai-identity-verify attestation path/to/envelope.json --pubkey signer.pem
```

### Using JWKS vs. raw PEM

For the `attestation` command you have two ways to provide the public key:

- `--pubkey` — best when you have pinned a specific public key for the signer. The tool trusts the supplied key as authoritative.
- `--jwks` — best when you have a set of valid keys (for example, the response from a `/.well-known/jwks.json` endpoint). The tool selects the right key by matching the `kid` in the envelope's signature against the `kid`s in the JWKS.

### Interpreting failures

Exit code `1` means the cryptographic link is broken:

- For `report`, the report file has been modified since generation.
- For `chain`, an entry is tampered, missing, or reordered. The output points to the entry number where the chain broke.
- For `attestation`, the signature does not verify — either the wrong key was used, or the payload was altered.

Exit code `2` means the command could not run because of a configuration issue: missing file, malformed JSON, missing `AI_IDENTITY_HMAC_KEY`, or neither/both of `--pubkey`/`--jwks` were supplied. The accompanying error message describes the specific problem.

## Exit code reference

| Code | Meaning | Subcommands |
|---|---|---|
| `0` | Verification passed | `report`, `chain`, `attestation` |
| `1` | Verification failed (invalid signature or broken chain) | `report`, `chain`, `attestation` |
| `2` | Usage error (missing file, bad JSON, missing key, etc.) | `report`, `chain`, `attestation` |
