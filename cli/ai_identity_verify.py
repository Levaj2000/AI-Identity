#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AI Identity (jeff@ai-identity.co)
"""AI Identity — Offline Verification CLI.

Standalone tool for auditors to verify AI Identity forensic exports
completely offline — no database, no API, no network.

MIT licensed: run it, read it, fork it, embed it in your own audit
tooling. Verification must never require trusting the vendor — this
tool is the proof. (Full text: LICENSE in this directory, or
https://opensource.org/license/mit when this file ships alone inside
a Case File bundle.)

Four verification modes:
  report           — verify the HMAC chain-of-custody certificate on an exported report
  chain            — verify the full sequential HMAC audit chain from exported entries
  attestation      — verify an ECDSA-signed forensic attestation DSSE envelope
  inclusion-proof  — verify Merkle inclusion proofs against signed checkpoints

Requires: Python 3.9+ for `report` and `chain` (stdlib only). The
`attestation` and `inclusion-proof` commands additionally require the
`cryptography` package (`pip install cryptography`) for ECDSA verification.

HMAC key (report/chain): set AI_IDENTITY_HMAC_KEY environment variable.
Public key (attestation/inclusion-proof): provide via --pubkey <pem> or --jwks <file>.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

__version__ = "1.4.0"
TOOL_NAME = "ai-identity-verify"
GENESIS = "GENESIS"

# Key fingerprint — first 16 hex chars of SHA-256(key). Must match
# common/audit/writer.py:key_fingerprint. Exported entries carry the
# fingerprint of the HMAC key they were hashed under, so this tool can
# tell a key-epoch boundary apart from tampering.
KEY_FINGERPRINT_LEN = 16

# DSSE constants — must match common/schemas/forensic_attestation.py
ATTESTATION_PAYLOAD_TYPE = "application/vnd.ai-identity.attestation+json"
ATTESTATION_SCHEMA_VERSION = 1
DSSE_PREAMBLE = b"DSSEv1"

# ── Colour helpers ──────────────────────────────────────────────────────

_NO_COLOR = False


def _supports_color() -> bool:
    if _NO_COLOR:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m" if _supports_color() else text


def _red(text: str) -> str:
    return f"\033[31m{text}\033[0m" if _supports_color() else text


def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m" if _supports_color() else text


def _dim(text: str) -> str:
    return f"\033[2m{text}\033[0m" if _supports_color() else text


# ── HMAC helpers (must match server exactly) ────────────────────────────


def _normalize_timestamp(ts: str) -> str:
    """Normalize ISO-8601 timestamps to match Python's datetime.isoformat().

    Converts trailing 'Z' to '+00:00' since the server uses
    datetime.isoformat() which always produces '+00:00'.
    """
    if ts.endswith("Z"):
        return ts[:-1] + "+00:00"
    return ts


def _get_hmac_key() -> bytes:
    """Read the HMAC key from the environment, returning raw bytes."""
    key = os.environ.get("AI_IDENTITY_HMAC_KEY")
    if not key:
        print(
            "Error: AI_IDENTITY_HMAC_KEY environment variable is not set.\n"
            "\n"
            "Set it to the same HMAC secret used by the AI Identity server:\n"
            "\n"
            "  export AI_IDENTITY_HMAC_KEY='your-hmac-secret-key'\n"
            "\n"
            "Then re-run this tool.",
            file=sys.stderr,
        )
        sys.exit(2)
    return key.encode("utf-8")


def _key_fingerprint(key: bytes) -> str:
    """SHA-256 hex of the key, truncated — matches the server's fingerprint."""
    return hashlib.sha256(key).hexdigest()[:KEY_FINGERPRINT_LEN]


def _get_hmac_keys(args: argparse.Namespace) -> list[bytes]:
    """All verification keys, primary (env) first, then any --key extras.

    An org's audit history can span key epochs (a regenerated key retires
    the old one; each epoch's rows verify only with that epoch's key).
    Supplying every key you hold lets one run cover every epoch.
    """
    keys = [_get_hmac_key()]
    for extra in getattr(args, "extra_keys", None) or []:
        key = extra.encode("utf-8")
        if key not in keys:
            keys.append(key)
    return keys


def _canonical_report_payload(
    report_id: str,
    generated_at: str,
    chain_valid: bool,
    total_entries: int,
    entries_verified: int,
) -> bytes:
    """Build the canonical JSON payload for report signature verification.

    Field order is determined by sort_keys=True; the dict literal order
    does not matter — json.dumps handles it.  This matches
    ``common.audit.writer.generate_report_signature`` exactly.
    """
    payload = {
        "entries_verified": entries_verified,
        "chain_valid": chain_valid,
        "generated_at": _normalize_timestamp(generated_at),
        "report_id": report_id,
        "total_entries": total_entries,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _compute_report_signature(
    key: bytes,
    report_id: str,
    generated_at: str,
    chain_valid: bool,
    total_entries: int,
    entries_verified: int,
) -> str:
    """Compute HMAC-SHA256 hex digest for a report certificate."""
    message = _canonical_report_payload(
        report_id,
        generated_at,
        chain_valid,
        total_entries,
        entries_verified,
    )
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _canonical_entry_payload(entry: dict[str, Any], prev_hash: str) -> bytes:
    """Build the canonical JSON payload for an audit chain entry.

    Mirrors ``common.audit.writer._canonical_payload`` exactly:
      - agent_id as string
      - cost_estimate_usd as string (or null)
      - created_at as ISO-8601 string
      - decision, endpoint, method as-is
      - latency_ms as int (or null)
      - prev_hash from chain (per-org chain uses prev_hash_org)
      - request_metadata as dict
    """
    cost = entry.get("cost_estimate_usd")
    payload = {
        "agent_id": str(entry["agent_id"]),
        "cost_estimate_usd": str(cost) if cost is not None else None,
        "created_at": _normalize_timestamp(entry["created_at"]),
        "decision": entry["decision"],
        "endpoint": entry["endpoint"],
        "latency_ms": entry.get("latency_ms"),
        "method": entry["method"],
        "prev_hash": prev_hash,
        "request_metadata": entry.get("request_metadata", {}),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _compute_entry_hash(key: bytes, entry: dict[str, Any], prev_hash: str) -> str:
    """Compute HMAC-SHA256 hex digest for an audit chain entry."""
    message = _canonical_entry_payload(entry, prev_hash)
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _entry_hash_matches_any(
    keys: list[bytes], entry: dict[str, Any], prev_hash: str, stored_hash: str
) -> tuple[bool, str]:
    """Recompute the entry hash with each key; return (matched, last recomputed).

    Entries without a recorded key fingerprint may belong to any epoch —
    accepting a match under ANY held key is safe because a match proves the
    content is exactly what that key signed.
    """
    recomputed = ""
    for key in keys:
        recomputed = _compute_entry_hash(key, entry, prev_hash)
        if hmac.compare_digest(recomputed, stored_hash):
            return True, recomputed
    return False, recomputed


def _print_wrong_key_hint(keys: list[bytes]) -> None:
    """Explain the 0-verified-from-entry-#1 pattern: key mismatch, not tampering."""
    fps = ", ".join(_key_fingerprint(k) for k in keys)
    print(
        "  Likely cause: KEY MISMATCH, not tampering. Every entry failed against\n"
        "                your key starting at the very first one, while the chain's\n"
        "                internal linkage is consistent — the classic signature of\n"
        "                verifying with the wrong key. Common reasons:\n"
        "                  - your organization's key was created AFTER these events\n"
        "                    (they were signed under an AI Identity platform key)\n"
        "                  - the key was regenerated since this export (use the\n"
        "                    retired key: Dashboard -> Organization -> Forensics)\n"
        "                  - a copy/paste error in the key\n"
        "                Pass additional keys with --key to cover earlier epochs.\n"
        f"                Fingerprint(s) of the key(s) you supplied: {fps}"
    )
    print()


def _entries_have_org_chain(entries: list[dict[str, Any]]) -> bool:
    """True if every entry carries the per-org chain fields.

    A forensics report exported after Phase 1 of the per-org chain
    migration carries ``prev_hash_org``/``entry_hash_org``/``org_chain_seq``
    on every event. Older reports won't have them — fall through to
    global-chain verify for those.
    """
    if not entries:
        return False
    for entry in entries:
        if entry.get("entry_hash_org") is None or entry.get("org_chain_seq") is None:
            return False
    return True


# ── File loading ────────────────────────────────────────────────────────


def _load_json(path: str) -> Any:
    """Load and parse a JSON file."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(2)


# ── Report verification ────────────────────────────────────────────────


def _extract_report_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Extract the fields needed for report signature verification.

    Handles the standard ForensicsReportResponse JSON shape.
    """
    # Top-level fields
    report_id = data.get("report_id")
    generated_at = data.get("generated_at")
    signature = data.get("report_signature")

    if not all([report_id, generated_at, signature]):
        print(
            "Error: JSON file is missing required report fields "
            "(report_id, generated_at, report_signature).",
            file=sys.stderr,
        )
        sys.exit(2)

    # chain_verification may be nested or flat
    cv = data.get("chain_verification", data)
    chain_valid = cv.get("chain_valid", cv.get("valid"))
    total_entries = cv.get("total_entries")
    entries_verified = cv.get("entries_verified")

    if chain_valid is None or total_entries is None or entries_verified is None:
        print(
            "Error: JSON file is missing chain verification fields "
            "(chain_valid/valid, total_entries, entries_verified).",
            file=sys.stderr,
        )
        sys.exit(2)

    return {
        "report_id": report_id,
        "generated_at": generated_at,
        "chain_valid": chain_valid,
        "total_entries": total_entries,
        "entries_verified": entries_verified,
        "report_signature": signature,
    }


def _progress_bar(current: int, total: int, width: int = 32) -> str:
    """Render a simple progress bar string."""
    filled = width if total == 0 else int(width * current / total)
    bar = "\u2588" * filled + " " * (width - filled)
    return f"[{bar}] {current}/{total}"


def cmd_report(args: argparse.Namespace) -> int:
    """Verify a report's chain-of-custody certificate."""
    keys = _get_hmac_keys(args)
    data = _load_json(args.file)
    fields = _extract_report_fields(data)

    valid = False
    expected = ""
    for key in keys:
        expected = _compute_report_signature(
            key,
            report_id=fields["report_id"],
            generated_at=fields["generated_at"],
            chain_valid=fields["chain_valid"],
            total_entries=fields["total_entries"],
            entries_verified=fields["entries_verified"],
        )
        if hmac.compare_digest(expected, fields["report_signature"]):
            valid = True
            break

    # New exports state which key epoch signed the report; when the
    # signature fails and the fingerprints don't line up, the problem is
    # the key, not the report.
    report_fp = data.get("verification_key_fingerprint")
    held_fps = [_key_fingerprint(k) for k in keys]
    key_mismatch = bool(report_fp) and report_fp not in held_fps and not valid

    if args.json:
        result = {
            "tool": TOOL_NAME,
            "version": __version__,
            "command": "report",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "result": "valid" if valid else "invalid",
            "details": {
                "report_id": fields["report_id"],
                "generated_at": fields["generated_at"],
                "total_entries": fields["total_entries"],
                "entries_verified": fields["entries_verified"],
                "chain_valid": fields["chain_valid"],
                "signature_valid": valid,
            },
        }
        if key_mismatch:
            result["details"]["key_mismatch"] = {
                "report_key_fingerprint": report_fp,
                "supplied_key_fingerprints": held_fps,
            }
        print(json.dumps(result, indent=2))
    else:
        chain_mark = _green("\u2713") if fields["chain_valid"] else _red("\u2717")
        sig_text = _green("VALID \u2713") if valid else _red("INVALID \u2717")

        title = _bold("AI Identity \u2014 Report Verification")
        print(f"\n{title}")
        print("\u2550" * 34)
        print(f"  Report ID:    {fields['report_id']}")
        print(f"  Generated:    {fields['generated_at']}")
        print(
            f"  Entries:      {fields['total_entries']} total, "
            f"{fields['entries_verified']} verified"
        )
        print(f"  Chain Valid:  {chain_mark}")
        print()
        print(f"  Signature:    {sig_text}")
        if key_mismatch:
            print(
                "  Note:         KEY MISMATCH \u2014 this report was signed under key epoch\n"
                f"                {report_fp}, but your key(s) fingerprint to\n"
                f"                {', '.join(held_fps)}. Fetch the current key from\n"
                "                Dashboard -> Organization -> Forensics (or supply the\n"
                "                right retired key with --key) and re-run."
            )
        print()

        if args.verbose:
            print(_dim(f"  Expected:  {expected}"))
            print(_dim(f"  Got:       {fields['report_signature']}"))
            print()

    return 0 if valid else 1


# ── Chain verification ──────────────────────────────────────────────────


def _load_chain_entries(path: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Load audit chain entries (and the export's scope, when present).

    Accepts either:
      - A JSON array of entry objects  (bare export; no scope available)
      - A JSON object with an "events" key containing the array
        (ForensicsReportResponse shape; may carry a "scope" object)

    Returns (entries, scope). The scope matters for chain verification: an
    agent-scoped export is a sparse slice of the org's chain (other agents
    own the intervening sequence numbers), so gap/linkage rules differ.
    """
    data = _load_json(path)
    scope: dict[str, Any] | None = None

    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get("events", data.get("entries", []))
        raw_scope = data.get("scope")
        if isinstance(raw_scope, dict):
            scope = raw_scope
        if not isinstance(entries, list):
            print(
                "Error: Could not find an array of audit entries in the JSON file.\n"
                "Expected a top-level array or an object with an 'events' key.",
                file=sys.stderr,
            )
            sys.exit(2)
    else:
        print("Error: Unexpected JSON structure.", file=sys.stderr)
        sys.exit(2)

    if len(entries) == 0:
        print("Warning: File contains zero audit entries.", file=sys.stderr)

    return entries, scope


def _cmd_chain_full(
    args: argparse.Namespace, keys: list[bytes], entries: list[dict[str, Any]], total: int
) -> int:
    """Verify the full HMAC audit chain (first entry has prev_hash=GENESIS)."""
    expected_prev_hash = GENESIS
    verified = 0
    break_info: dict[str, Any] | None = None

    for i, entry in enumerate(entries):
        stored_hash = entry.get("entry_hash", "")
        entry_prev = entry.get("prev_hash", "")

        # 1. Check prev_hash linkage
        if entry_prev != expected_prev_hash:
            break_info = {
                "index": i,
                "entry_id": entry.get("id", "?"),
                "reason": "prev_hash mismatch",
                "expected_prev": expected_prev_hash,
                "got_prev": entry_prev,
            }
            break

        # 2. Recompute HMAC and compare (any held key epoch may match)
        matched, recomputed = _entry_hash_matches_any(keys, entry, entry_prev, stored_hash)
        if not matched:
            break_info = {
                "index": i,
                "entry_id": entry.get("id", "?"),
                "reason": "hash mismatch",
                "expected_hash": recomputed,
                "got_hash": stored_hash,
            }
            break

        expected_prev_hash = stored_hash
        verified += 1

        # Show progress on large chains (human mode only)
        if (
            not args.json
            and not args.verbose
            and total >= 100
            and ((i + 1) % max(1, total // 32) == 0 or i + 1 == total)
        ):
            sys.stdout.write(f"\r  Verifying chain...  {_progress_bar(i + 1, total)}")
            sys.stdout.flush()

    intact = break_info is None

    if args.json:
        details: dict[str, Any] = {
            "file": os.path.basename(args.file),
            "total_entries": total,
            "entries_verified": verified,
            "chain_intact": intact,
            "mode": "full",
        }
        if break_info:
            details["break_at"] = break_info
        result = {
            "tool": TOOL_NAME,
            "version": __version__,
            "command": "chain",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "result": "valid" if intact else "broken",
            "details": details,
        }
        print(json.dumps(result, indent=2))
    else:
        # Clear progress line if used
        if total >= 100 and not args.verbose:
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

        chain_title = _bold("AI Identity \u2014 Audit Chain Verification")
        print(f"\n{chain_title}")
        print("\u2550" * 39)
        print(f"  File:         {os.path.basename(args.file)}")
        print(f"  Entries:      {total}")
        print("  Mode:         Full (chain starts at genesis)")
        print()

        if not args.verbose:
            print(f"  Verifying chain...  {_progress_bar(verified, total)}")
        print()

        if intact:
            intact_msg = _green("CHAIN INTACT \u2713")
            print(f"  Result:       {intact_msg}")
            print(f"  Verified:     {verified}/{total} entries")
        else:
            if break_info is None:
                raise RuntimeError("Internal error: chain broken but break_info is None")
            broken_msg = _red("CHAIN BROKEN \u2717")
            print(f"  Result:       {broken_msg}")
            print(f"  Verified:     {verified}/{total} entries")
            print(f"  Break at:     Entry #{break_info['index'] + 1}")
            print(f"    Entry ID:   {break_info['entry_id']}")
            if break_info["reason"] == "prev_hash mismatch":
                print(f"    Expected prev_hash: {break_info['expected_prev'][:16]}...")
                print(f"    Got:                {break_info['got_prev'][:16]}...")
            else:
                print(f"    Expected:   {break_info['expected_hash'][:16]}...")
                print(f"    Got:        {break_info['got_hash'][:16]}...")

        print()

        if (
            not intact
            and break_info["reason"] == "hash mismatch"
            and break_info["index"] == 0
            and verified == 0
        ):
            _print_wrong_key_hint(keys)

        if args.verbose and not intact and break_info:
            print(_dim("  Full values:"))
            if break_info["reason"] == "prev_hash mismatch":
                print(_dim(f"    expected_prev: {break_info['expected_prev']}"))
                print(_dim(f"    got_prev:      {break_info['got_prev']}"))
            else:
                print(_dim(f"    expected: {break_info['expected_hash']}"))
                print(_dim(f"    got:      {break_info['got_hash']}"))
            print()

    return 0 if intact else 1


def _cmd_chain_partial(
    args: argparse.Namespace, keys: list[bytes], entries: list[dict[str, Any]], total: int
) -> int:
    """Verify a partial chain export (first entry does not start at genesis)."""
    first_entry_id = entries[0].get("id", "?")
    verified = 0
    tampered_entries: list[dict[str, Any]] = []
    anchor_ok: bool | None = None  # None = no anchor supplied

    # Anchor check: if --expected-prev-hash was supplied, verify the first
    # entry's prev_hash matches before doing anything else.
    expected_prev_hash: str | None = getattr(args, "expected_prev_hash", None)
    if expected_prev_hash is not None:
        actual_first_prev = entries[0].get("prev_hash", "")
        anchor_ok = hmac.compare_digest(expected_prev_hash, actual_first_prev)

    for i, entry in enumerate(entries):
        stored_hash = entry.get("entry_hash", "")
        entry_prev = entry.get("prev_hash", "")

        # For entries after the first, verify chain linkage within the export
        if i > 0:
            expected_prev = entries[i - 1].get("entry_hash", "")
            if entry_prev != expected_prev:
                tampered_entries.append(
                    {
                        "index": i,
                        "entry_id": entry.get("id", "?"),
                        "reason": "prev_hash mismatch",
                        "expected_prev": expected_prev,
                        "got_prev": entry_prev,
                    }
                )
                continue

        # Recompute HMAC using the entry's own prev_hash (any held key epoch)
        matched, recomputed = _entry_hash_matches_any(keys, entry, entry_prev, stored_hash)
        if not matched:
            tampered_entries.append(
                {
                    "index": i,
                    "entry_id": entry.get("id", "?"),
                    "reason": "hash mismatch",
                    "stored_hash": stored_hash,
                    "computed_hash": recomputed,
                }
            )
            continue

        verified += 1

        # Show progress on large chains (human mode only)
        if (
            not args.json
            and not args.verbose
            and total >= 100
            and ((i + 1) % max(1, total // 32) == 0 or i + 1 == total)
        ):
            sys.stdout.write(f"\r  Verifying entry integrity...  {_progress_bar(i + 1, total)}")
            sys.stdout.flush()

    all_valid = len(tampered_entries) == 0
    is_single = total == 1

    if args.json:
        if all_valid:
            result_str = "entry_valid" if is_single else "partial_valid"
        else:
            result_str = "entry_tampered" if is_single else "partial_tampered"

        details: dict[str, Any] = {
            "file": os.path.basename(args.file),
            "total_entries": total,
            "entries_verified": verified,
            "chain_intact": all_valid,
            "mode": "partial",
            "partial_start_entry": first_entry_id,
        }
        if anchor_ok is not None:
            details["anchor_verified"] = anchor_ok
        if tampered_entries:
            details["tampered_entries"] = tampered_entries
        result = {
            "tool": TOOL_NAME,
            "version": __version__,
            "command": "chain",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "result": result_str,
            "details": details,
        }
        print(json.dumps(result, indent=2))
    else:
        # Clear progress line if used
        if total >= 100 and not args.verbose:
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

        chain_title = _bold("AI Identity \u2014 Audit Chain Verification")
        print(f"\n{chain_title}")
        print("\u2550" * 39)
        print(f"  File:         {os.path.basename(args.file)}")
        print(f"  Entries:      {total}")
        print(f"  Mode:         Partial (chain starts at entry #{first_entry_id}, not genesis)")
        if anchor_ok is True:
            anchor_msg = _green("VERIFIED \u2713")
            print(f"  Anchor:       {anchor_msg} (prev_hash matches expected)")
        elif anchor_ok is False:
            anchor_msg = _red("MISMATCH \u2717")
            print(f"  Anchor:       {anchor_msg} (prev_hash does not match --expected-prev-hash)")
        print()

        if not args.verbose:
            label = "Verifying entry integrity..."
            print(f"  {label}  {_progress_bar(total, total)}")
        print()

        if all_valid:
            if is_single:
                ok_msg = _green("ENTRY VERIFIED \u2713")
                print(f"  Result:       {ok_msg}")
                print(f"  Verified:     {verified}/{total} entries")
                print(
                    "  Note:         Entry hash matches HMAC computation.\n"
                    "                Chain linkage cannot be fully verified\n"
                    "                without preceding entries."
                )
            else:
                ok_msg = _green("PARTIAL CHAIN INTACT \u2713")
                print(f"  Result:       {ok_msg}")
                print(f"  Verified:     {verified}/{total} entries")
                print(
                    "  Note:         All entry hashes valid and chain linkage\n"
                    "                intact within this export. Full chain\n"
                    "                verification requires all entries from genesis."
                )
        else:
            tampered_msg = (
                _red("ENTRY TAMPERED \u2717") if is_single else _red("CHAIN TAMPERED \u2717")
            )
            print(f"  Result:       {tampered_msg}")
            print(f"  Verified:     {verified}/{total} entries")
            for te in tampered_entries:
                print(f"  Tampered:     Entry #{te['entry_id']}")
                if te["reason"] == "hash mismatch":
                    print(f"    Stored hash:    {te['stored_hash'][:16]}...")
                    print(f"    Computed hash:  {te['computed_hash'][:16]}...")
                else:
                    print(f"    Expected prev_hash: {te['expected_prev'][:16]}...")
                    print(f"    Got:                {te['got_prev'][:16]}...")

        print()

        if args.verbose and tampered_entries:
            print(_dim("  Full values:"))
            for te in tampered_entries:
                print(_dim(f"    Entry #{te['entry_id']}:"))
                if te["reason"] == "hash mismatch":
                    print(_dim(f"      stored:   {te['stored_hash']}"))
                    print(_dim(f"      computed: {te['computed_hash']}"))
                else:
                    print(_dim(f"      expected_prev: {te['expected_prev']}"))
                    print(_dim(f"      got_prev:      {te['got_prev']}"))
            print()

    passed = all_valid and (anchor_ok is not False)
    return 0 if passed else 1


def _cmd_chain_org(
    args: argparse.Namespace,
    keys: list[bytes],
    entries: list[dict[str, Any]],
    total: int,
    agent_scoped: bool = False,
) -> int:
    """Verify the per-org HMAC chain from an exported report.

    Org-scoped export: a time-windowed slice of one org's chain — the
    starting ``org_chain_seq`` may not be 1, but within the slice the
    sequence must be contiguous (no gaps = no deletions) and the chain
    linkage must hold via ``prev_hash_org``/``entry_hash_org``.

    Agent-scoped export (``agent_scoped=True``): a *sparse* slice — other
    agents legitimately own the intervening sequence numbers, so a gap is
    NOT evidence of deletion. Mirrors the server-side rule
    (common/audit/writer.py verify_chain): per-row hash recomputation
    always runs; linkage is enforced only across consecutive sequence
    numbers, and each gap re-anchors the window. Completeness (no deleted
    rows) can only be proven by an org-scope export.

    Key epochs: each entry may carry ``key_fingerprint`` — the fingerprint
    of the HMAC key it was hashed under. Entries whose fingerprint matches
    none of the supplied keys (e.g. rows written under the platform key
    before the org's key existed) are reported as **not covered by your
    key(s)** — an honest partial result — rather than as tampering. The
    structural checks (sequence + linkage) still run on every entry.

    Sorts by ``org_chain_seq`` defensively in case the export ordering
    differs.
    """
    entries = sorted(entries, key=lambda e: e["org_chain_seq"])
    keymap = {_key_fingerprint(k): k for k in keys}
    verified = 0
    gaps_reanchored = 0
    foreign_epochs: dict[str, int] = {}  # fingerprint → entry count not covered by held keys
    break_info: dict[str, Any] | None = None
    expected_seq: int | None = None
    expected_prev_hash: str | None = None

    for i, entry in enumerate(entries):
        seq = entry["org_chain_seq"]
        stored_hash = entry.get("entry_hash_org", "")
        entry_prev = entry.get("prev_hash_org", "")

        # First entry anchors the window — accept its seq and prev_hash_org
        if expected_seq is None:
            expected_seq = seq
            expected_prev_hash = entry_prev
        else:
            if seq != expected_seq:
                if agent_scoped:
                    # Rows in between belong to other agents in the org —
                    # re-anchor the window at this entry.
                    gaps_reanchored += 1
                    expected_prev_hash = entry_prev
                else:
                    break_info = {
                        "index": i,
                        "entry_id": entry.get("id", "?"),
                        "reason": "sequence gap (rows deleted from this org's history)",
                        "expected_seq": expected_seq,
                        "got_seq": seq,
                    }
                    break
            if entry_prev != expected_prev_hash:
                break_info = {
                    "index": i,
                    "entry_id": entry.get("id", "?"),
                    "reason": "prev_hash_org mismatch",
                    "expected_prev": expected_prev_hash,
                    "got_prev": entry_prev,
                }
                break

        entry_fp = entry.get("key_fingerprint")
        if entry_fp and entry_fp not in keymap:
            # Recorded under a key epoch we don't hold — its hash cannot be
            # recomputed with the supplied keys, so this is a coverage gap,
            # not evidence of tampering. Linkage continues over the stored
            # hash, so structure is still fully checked.
            foreign_epochs[entry_fp] = foreign_epochs.get(entry_fp, 0) + 1
            expected_prev_hash = stored_hash
            expected_seq = seq + 1
            continue

        # Recompute entry_hash_org and compare. _compute_entry_hash uses
        # the same canonical payload — we just pass prev_hash_org as the
        # chain field. With a recorded fingerprint we know the exact key;
        # legacy entries without one may match any held key.
        if entry_fp:
            recomputed = _compute_entry_hash(keymap[entry_fp], entry, entry_prev)
            matched = hmac.compare_digest(recomputed, stored_hash)
        else:
            matched, recomputed = _entry_hash_matches_any(keys, entry, entry_prev, stored_hash)
        if not matched:
            break_info = {
                "index": i,
                "entry_id": entry.get("id", "?"),
                "reason": "hash mismatch",
                "expected_hash": recomputed,
                "got_hash": stored_hash,
                "entry_key_fingerprint": entry_fp,
            }
            break

        expected_prev_hash = stored_hash
        expected_seq = seq + 1
        verified += 1

    intact = break_info is None
    unverified = sum(foreign_epochs.values())
    # Zero coverage — the supplied key(s) match no entry's epoch at all.
    # Structure may be intact, but NOTHING was cryptographically verified;
    # reporting that as a pass would let a typo'd key masquerade as a
    # successful verification. Distinct result, non-zero exit.
    no_coverage = intact and unverified > 0 and verified == 0
    partial = intact and unverified > 0 and verified > 0

    if args.json:
        if not intact:
            result_str = "broken"
        elif no_coverage:
            result_str = "no_key_coverage"
        elif partial:
            result_str = "valid_partial_coverage"
        else:
            result_str = "valid"
        details: dict[str, Any] = {
            "file": os.path.basename(args.file),
            "total_entries": total,
            "entries_verified": verified,
            "entries_not_covered_by_keys": unverified,
            "chain_intact": intact,
            "mode": "per-org-agent-slice" if agent_scoped else "per-org",
            "supplied_key_fingerprints": sorted(keymap),
            "seq_range": (
                [entries[0]["org_chain_seq"], entries[-1]["org_chain_seq"]] if entries else None
            ),
        }
        if agent_scoped:
            details["gaps_reanchored"] = gaps_reanchored
        if foreign_epochs:
            details["uncovered_key_epochs"] = foreign_epochs
        if break_info:
            details["break_at"] = break_info
        result = {
            "tool": TOOL_NAME,
            "version": __version__,
            "command": "chain",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "result": result_str,
            "details": details,
        }
        print(json.dumps(result, indent=2))
    else:
        chain_title = _bold("AI Identity — Per-Org Audit Chain Verification")
        print(f"\n{chain_title}")
        print("═" * 47)
        print(f"  File:         {os.path.basename(args.file)}")
        print(f"  Entries:      {total}")
        if entries:
            print(f"  Seq range:    {entries[0]['org_chain_seq']} → {entries[-1]['org_chain_seq']}")
        if agent_scoped:
            print("  Mode:         Agent slice (row integrity + intra-run linkage;")
            print("                completeness proof requires an org-scope export)")
            if gaps_reanchored:
                print(
                    f"  Note:         {gaps_reanchored} sequence gap(s) re-anchored — "
                    "other agents own those rows"
                )
        else:
            print("  Mode:         Per-org (tenant-scoped completeness proof)")
        print()
        if intact and not partial and not no_coverage:
            print(f"  Result:       {_green('CHAIN INTACT ✓')}")
            print(f"  Verified:     {verified}/{total} entries")
        elif no_coverage:
            print(f"  Result:       {_red('NOT VERIFIED ✗')} (no key coverage)")
            print(f"  Verified:     0/{total} entries")
            fps = ", ".join(sorted(foreign_epochs))
            print(f"  Key epochs:   entries were recorded under: {fps}")
            print(
                "                None of the supplied keys match any entry's key epoch,\n"
                "                so nothing could be cryptographically verified (sequence\n"
                "                and linkage structure are consistent). This is a key\n"
                "                problem, not proof of tampering — see below."
            )
        elif intact:
            print(f"  Result:       {_green('CHAIN INTACT ✓')} (partial key coverage)")
            print(f"  Verified:     {verified}/{total} entries with your key(s)")
            fps = ", ".join(sorted(foreign_epochs))
            print(f"  Not covered:  {unverified} entries from earlier key epoch(s): {fps}")
            print(
                "                These were recorded before your current key existed (or\n"
                "                under a retired key you did not supply with --key), so\n"
                "                your key cannot recompute their hashes. Sequence and\n"
                "                linkage checks passed for ALL entries; the uncovered\n"
                "                hashes can be verified by AI Identity or independently\n"
                "                via evidence-anchor public proofs (see README)."
            )
        else:
            assert break_info is not None
            print(f"  Result:       {_red('CHAIN BROKEN ✗')}")
            print(f"  Verified:     {verified}/{total} entries")
            print(f"  Break at:     Entry #{break_info['index'] + 1}")
            print(f"    Reason:     {break_info['reason']}")
        print()
        wrong_key_shape = no_coverage or (
            not intact
            and break_info is not None
            and break_info["reason"] == "hash mismatch"
            and break_info["index"] == 0
            and verified == 0
            and not break_info.get("entry_key_fingerprint")
        )
        if wrong_key_shape:
            _print_wrong_key_hint(keys)
    return 0 if intact and not no_coverage else 1


def cmd_chain(args: argparse.Namespace) -> int:
    """Verify the HMAC audit chain (per-org, full, or partial)."""
    keys = _get_hmac_keys(args)
    entries, scope = _load_chain_entries(args.file)
    total = len(entries)
    agent_scoped = isinstance(scope, dict) and scope.get("type") == "agent"

    if total == 0:
        if args.json:
            result = {
                "tool": TOOL_NAME,
                "version": __version__,
                "command": "chain",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "result": "valid",
                "details": {
                    "file": os.path.basename(args.file),
                    "total_entries": 0,
                    "entries_verified": 0,
                    "chain_intact": True,
                    "mode": "full",
                },
            }
            print(json.dumps(result, indent=2))
        else:
            chain_title = _bold("AI Identity \u2014 Audit Chain Verification")
            print(f"\n{chain_title}")
            print("\u2550" * 39)
            print(f"  File:         {os.path.basename(args.file)}")
            print("  Entries:      0")
            print()
            intact_msg = _green("CHAIN INTACT \u2713")
            print(f"  Result:       {intact_msg} (empty)")
            print()
        return 0

    # Prefer the per-org chain when the export carries it — that's the
    # tenant-scoped completeness proof. Older exports without the
    # org-chain fields fall through to the legacy global path.
    if not getattr(args, "global_chain", False) and _entries_have_org_chain(entries):
        return _cmd_chain_org(args, keys, entries, total, agent_scoped=agent_scoped)

    # Legacy / fallback: global chain. Detect partial export (first
    # entry's prev_hash is not GENESIS) → use partial verify.
    is_partial = entries[0].get("prev_hash", "") != GENESIS
    if is_partial:
        return _cmd_chain_partial(args, keys, entries, total)
    return _cmd_chain_full(args, keys, entries, total)


# ── Attestation verification (DSSE + ECDSA P-256) ──────────────────────
#
# Unlike the HMAC-only `report` and `chain` commands, the public-key
# commands (`attestation`, `inclusion-proof`) need asymmetric crypto. We
# rely on the `cryptography` package for ECDSA verification — importing
# it lazily inside those commands so that `report` and `chain` continue
# to work with a stdlib-only install.


def _require_cryptography(command: str) -> None:
    """Exit(2) with an install hint if the `cryptography` package is missing.

    Must be called at the top of every command that touches ECDSA, before
    any bare `from cryptography...` import on its path — otherwise a
    stdlib-only install gets a raw ModuleNotFoundError traceback instead
    of this message.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import ec  # noqa: F401
    except ImportError:
        print(
            f"Error: The `{command}` command requires the `cryptography` "
            "package.\n"
            "\n"
            "Install it with:\n"
            "\n"
            "  pip install cryptography\n"
            "\n"
            "(The `report` and `chain` commands are stdlib-only and work "
            "without this dependency.)",
            file=sys.stderr,
        )
        sys.exit(2)


def _base64_decode(value: str, field: str) -> bytes:
    """Strict base64 decode; raises usage error on bad input."""
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        print(f"Error: {field} is not valid base64: {exc}", file=sys.stderr)
        sys.exit(2)


def _b64url_decode(value: str, field: str) -> bytes:
    """Decode base64url (JWK) with optional missing padding."""
    pad = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + pad)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        print(f"Error: {field} is not valid base64url: {exc}", file=sys.stderr)
        sys.exit(2)


def _dsse_pae(payload_type: str, payload_bytes: bytes) -> bytes:
    """DSSE Pre-Authentication Encoding.

    Must match ``common.schemas.forensic_attestation.pae`` byte-for-byte.
    Any divergence here silently breaks verification — keep the two
    implementations in lockstep.
    """
    type_bytes = payload_type.encode("utf-8")
    return (
        DSSE_PREAMBLE
        + b" "
        + str(len(type_bytes)).encode("ascii")
        + b" "
        + type_bytes
        + b" "
        + str(len(payload_bytes)).encode("ascii")
        + b" "
        + payload_bytes
    )


def _load_public_key(args: argparse.Namespace, envelope_kid: str):
    """Resolve the public key used to verify the envelope.

    Two sources, mutually exclusive:

    * ``--pubkey <PEM file>`` — single local PEM (e.g. a pinned copy
      for the key that signed this envelope). No kid cross-check —
      if you passed a specific PEM, we trust you know which key it is.
    * ``--jwks <JSON file>`` — a JWKS document (as served by
      ``/.well-known/ai-identity-public-keys.json``). We match on
      ``kid`` against the envelope's signature keyid.

    Returns the cryptography public key object. Exits with code 2 on
    any configuration error so the caller never needs to guard against
    ``None``.
    """
    _require_cryptography(getattr(args, "command", None) or "attestation")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    if args.pubkey and args.jwks:
        print(
            "Error: --pubkey and --jwks are mutually exclusive; pick one.",
            file=sys.stderr,
        )
        sys.exit(2)
    if not args.pubkey and not args.jwks:
        print(
            "Error: Provide a verification key via --pubkey <pem-file> or --jwks <jwks.json>.",
            file=sys.stderr,
        )
        sys.exit(2)

    if args.pubkey:
        try:
            with open(args.pubkey, "rb") as f:
                pem_bytes = f.read()
        except FileNotFoundError:
            print(f"Error: Public key file not found: {args.pubkey}", file=sys.stderr)
            sys.exit(2)
        try:
            public_key = serialization.load_pem_public_key(pem_bytes)
        except ValueError as exc:
            print(f"Error: Could not parse PEM public key: {exc}", file=sys.stderr)
            sys.exit(2)
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            print(
                "Error: Public key is not an EC key (attestation format requires ECDSA P-256).",
                file=sys.stderr,
            )
            sys.exit(2)
        return public_key

    # JWKS path ---------------------------------------------------------
    jwks = _load_json(args.jwks)
    if not isinstance(jwks, dict) or "keys" not in jwks:
        print(
            "Error: JWKS file does not look like a JWK Set "
            "(expected an object with a 'keys' array).",
            file=sys.stderr,
        )
        sys.exit(2)

    match = None
    for jwk in jwks["keys"]:
        if jwk.get("kid") == envelope_kid:
            match = jwk
            break
    if match is None:
        available = [k.get("kid", "<no-kid>") for k in jwks["keys"]]
        print(
            f"Error: JWKS has no key with kid={envelope_kid!r}.\nAvailable kids: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    if match.get("kty") != "EC" or match.get("crv") != "P-256":
        print(
            f"Error: JWK kid={envelope_kid!r} is not EC/P-256 "
            f"(kty={match.get('kty')!r}, crv={match.get('crv')!r}).",
            file=sys.stderr,
        )
        sys.exit(1)

    x_bytes = _b64url_decode(match["x"], field=f"JWK kid={envelope_kid!r} x")
    y_bytes = _b64url_decode(match["y"], field=f"JWK kid={envelope_kid!r} y")
    numbers = ec.EllipticCurvePublicNumbers(
        x=int.from_bytes(x_bytes, "big"),
        y=int.from_bytes(y_bytes, "big"),
        curve=ec.SECP256R1(),
    )
    return numbers.public_key()


def cmd_attestation(args: argparse.Namespace) -> int:
    """Verify a forensic attestation DSSE envelope."""
    _require_cryptography("attestation")
    envelope = _load_json(args.file)

    # Shape check — fail fast with a precise message rather than a
    # generic KeyError deep inside the verify path.
    if not isinstance(envelope, dict):
        print("Error: Envelope must be a JSON object.", file=sys.stderr)
        sys.exit(2)

    # GET /api/v1/sessions/{id}/attestation returns the envelope wrapped
    # in an AttestationResponse ({id, org_id, ..., envelope: {...}}).
    # Accept that shape directly so a saved API response verifies as-is.
    unwrapped = False
    if "payloadType" not in envelope and isinstance(envelope.get("envelope"), dict):
        inner = envelope["envelope"]
        if "payloadType" in inner and "payload" in inner:
            envelope = inner
            unwrapped = True

    if envelope.get("payloadType") != ATTESTATION_PAYLOAD_TYPE:
        print(
            f"Error: Unexpected payloadType: {envelope.get('payloadType')!r} "
            f"(expected {ATTESTATION_PAYLOAD_TYPE!r}).",
            file=sys.stderr,
        )
        return 1
    signatures = envelope.get("signatures") or []
    if len(signatures) != 1:
        print(
            f"Error: Expected exactly 1 signature, got {len(signatures)}.",
            file=sys.stderr,
        )
        return 1

    sig_entry = signatures[0]
    envelope_kid = sig_entry.get("keyid", "")
    if not envelope_kid:
        print("Error: Signature is missing keyid.", file=sys.stderr)
        return 1

    public_key = _load_public_key(args, envelope_kid)

    payload_bytes = _base64_decode(envelope.get("payload", ""), field="envelope.payload")
    signature_der = _base64_decode(sig_entry.get("sig", ""), field="signature.sig")

    # Parse the payload JSON (without re-canonicalizing — we verify over
    # the bytes that were actually signed, not a round-tripped copy).
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as exc:
        print(f"Error: payload is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print("Error: payload JSON is not an object.", file=sys.stderr)
        return 1

    schema_version = payload.get("schema_version")
    if schema_version != ATTESTATION_SCHEMA_VERSION:
        print(
            f"Error: Unsupported schema_version: {schema_version!r} "
            f"(this CLI only understands v{ATTESTATION_SCHEMA_VERSION}).",
            file=sys.stderr,
        )
        return 1

    # Range sanity — cheap and catches obviously-malformed payloads
    # before we invest in the ECDSA verify.
    first_id = payload.get("first_audit_id")
    last_id = payload.get("last_audit_id")
    event_count = payload.get("event_count")
    range_ok = (
        isinstance(first_id, int)
        and isinstance(last_id, int)
        and isinstance(event_count, int)
        and last_id >= first_id
        and event_count >= 1
    )
    if not range_ok:
        print(
            "Error: Payload range fields are missing or inconsistent "
            "(first_audit_id / last_audit_id / event_count).",
            file=sys.stderr,
        )
        return 1

    # Signature verify --------------------------------------------------
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    signing_input = _dsse_pae(ATTESTATION_PAYLOAD_TYPE, payload_bytes)
    sig_valid = True
    sig_error: str | None = None
    try:
        public_key.verify(signature_der, signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        sig_valid = False
        sig_error = "signature does not verify against the supplied public key"
    except Exception as exc:  # pragma: no cover — defensive
        sig_valid = False
        sig_error = f"verify raised: {exc}"

    # Output ------------------------------------------------------------
    details = {
        "file": os.path.basename(args.file),
        "payload_type": ATTESTATION_PAYLOAD_TYPE,
        "schema_version": schema_version,
        "signer_key_id": payload.get("signer_key_id"),
        "envelope_keyid": envelope_kid,
        "session_id": payload.get("session_id"),
        "org_id": payload.get("org_id"),
        "first_audit_id": first_id,
        "last_audit_id": last_id,
        "event_count": event_count,
        "evidence_chain_hash": payload.get("evidence_chain_hash"),
        "session_start": payload.get("session_start"),
        "session_end": payload.get("session_end"),
        "signed_at": payload.get("signed_at"),
        "signature_valid": sig_valid,
    }
    if unwrapped:
        details["unwrapped_envelope"] = True
    if sig_error:
        details["signature_error"] = sig_error

    if args.json:
        result = {
            "tool": TOOL_NAME,
            "version": __version__,
            "command": "attestation",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "result": "valid" if sig_valid else "invalid",
            "details": details,
        }
        print(json.dumps(result, indent=2))
    else:
        title = _bold("AI Identity \u2014 Attestation Verification")
        print(f"\n{title}")
        print("\u2550" * 41)
        print(f"  File:         {details['file']}")
        if unwrapped:
            print(
                _dim(
                    "                (API response detected \u2014 verifying its `envelope` field)"
                )
            )
        print(f"  Schema:       v{schema_version}")
        print(f"  Key ID:       {details['signer_key_id']}")
        print(f"  Session:      {details['session_id']}")
        print(f"  Org:          {details['org_id']}")
        print(
            f"  Audit range:  {first_id}..{last_id} "
            f"({event_count} event{'s' if event_count != 1 else ''})"
        )
        print(f"  Chain hash:   {details['evidence_chain_hash']}")
        print(f"  Signed at:    {details['signed_at']}")
        print()
        if sig_valid:
            ok_msg = _green("VALID \u2713")
            print(f"  Signature:    {ok_msg}")
        else:
            bad_msg = _red("INVALID \u2717")
            print(f"  Signature:    {bad_msg}")
            if sig_error:
                print(f"                {_dim(sig_error)}")
        print()

        if args.verbose:
            print(_dim(f"  payloadType:     {envelope.get('payloadType')}"))
            print(_dim(f"  signing keyid:   {envelope_kid}"))
            print(_dim(f"  signature bytes: {len(signature_der)} (DER)"))
            print(_dim(f"  payload bytes:   {len(payload_bytes)} (canonical JSON)"))
            print()

    return 0 if sig_valid else 1


# ── CLI argument parsing ────────────────────────────────────────────────


# ── Evidence Anchor: Merkle inclusion-proof verification ───────────────
#
# Verifies that a single audit event is committed to a signed Merkle
# checkpoint, using ONLY the public key + SHA-256 — no shared secret. The
# checkpoint signature reuses the same DSSE/ECDSA-P256 path as `attestation`;
# the Merkle math below is a byte-for-byte port of
# ``common.forensic.merkle`` (RFC 6962 §2.1.1). Keep the two in lockstep.

CHECKPOINT_PAYLOAD_TYPE = "application/vnd.ai-identity.anchor-checkpoint+json"


def _merkle_leaf_hash(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def _merkle_node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _merkle_verify_inclusion(
    leaf_data: bytes, index: int, tree_size: int, proof: list[bytes], root: bytes
) -> bool:
    """RFC 6962 §2.1.1 inclusion-proof check. O(log N), stdlib only."""
    if tree_size <= 0 or not 0 <= index < tree_size:
        return False
    fn = index
    sn = tree_size - 1
    r = _merkle_leaf_hash(leaf_data)
    for p in proof:
        if sn == 0:
            return False
        if (fn & 1) or fn == sn:
            r = _merkle_node_hash(p, r)
            if not (fn & 1):
                while True:
                    fn >>= 1
                    sn >>= 1
                    if (fn & 1) or fn == 0:
                        break
        else:
            r = _merkle_node_hash(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and hmac.compare_digest(r, root)


def _verify_checkpoint_signature(args: argparse.Namespace, envelope: dict):
    """Verify a checkpoint DSSE envelope's ECDSA-P256 signature.

    Returns ``(ok, payload_dict)``. ``ok`` is False (with a printed reason)
    on any structural or cryptographic failure.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    if envelope.get("payloadType") != CHECKPOINT_PAYLOAD_TYPE:
        print(_red(f"  ✗ unexpected payloadType: {envelope.get('payloadType')!r}"))
        return False, {}
    sigs = envelope.get("signatures") or []
    if len(sigs) != 1:
        print(_red(f"  ✗ expected exactly 1 signature, got {len(sigs)}"))
        return False, {}

    payload_bytes = _base64_decode(envelope.get("payload", ""), field="checkpoint payload")
    signature_der = _base64_decode(sigs[0].get("sig", ""), field="checkpoint signature")
    public_key = _load_public_key(args, sigs[0].get("keyid", ""))

    signing_input = _dsse_pae(CHECKPOINT_PAYLOAD_TYPE, payload_bytes)
    try:
        public_key.verify(signature_der, signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        print(_red("  ✗ checkpoint signature verification failed"))
        return False, {}
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        print(_red("  ✗ checkpoint payload is not valid JSON"))
        return False, {}
    return True, payload


def cmd_inclusion_proof(args: argparse.Namespace) -> int:
    """Verify Merkle inclusion proofs against signed checkpoints (public key only)."""
    _require_cryptography("inclusion-proof")
    checkpoints = _load_json(args.checkpoints)
    proofs_doc = _load_json(args.proofs)
    proofs = proofs_doc.get("proofs", []) if isinstance(proofs_doc, dict) else proofs_doc
    pending = proofs_doc.get("pending", []) if isinstance(proofs_doc, dict) else []

    if not isinstance(checkpoints, list) or not proofs:
        print(_red("Error: no checkpoints or proofs to verify."), file=sys.stderr)
        return 2

    # Verify each checkpoint's signature ONCE, and bind the signed root to the
    # root the proofs reference (a signature over a different root is useless).
    verified_roots: dict[str, bool] = {}
    for cp in checkpoints:
        root = cp.get("merkle_root", "")
        print(_bold(f"Checkpoint {root[:16]}…"))
        ok, payload = _verify_checkpoint_signature(args, cp.get("envelope", {}))
        if ok and payload.get("merkle_root") != root:
            print(_red("  ✗ signed root does not match the checkpoint's stated root"))
            ok = False
        if ok:
            print(_green("  ✓ signature valid"))
        verified_roots[root] = ok

    all_ok = True
    print()
    for p in proofs:
        root = p.get("merkle_root", "")
        sig_ok = verified_roots.get(root, False)
        incl_ok = sig_ok and _merkle_verify_inclusion(
            bytes.fromhex(p["entry_hash"]),
            p["index"],
            p["tree_size"],
            [bytes.fromhex(h) for h in p["proof"]],
            bytes.fromhex(root),
        )
        label = f"event #{p.get('audit_id')} (entry {p['entry_hash'][:12]}…)"
        print(f"  {_green('✓ VERIFIED') if incl_ok else _red('✗ NOT VERIFIED')}  {label}")
        all_ok = all_ok and incl_ok

    if pending:
        print()
        print(_dim(f"  note: {len(pending)} exported event(s) not yet anchored to a checkpoint."))

    print()
    if all_ok:
        print(
            _green(_bold("INCLUSION VERIFIED")) + f" — {len(proofs)} event(s) provably committed."
        )
        return 0
    print(_red(_bold("INCLUSION NOT VERIFIED")) + " — one or more events failed.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_identity_verify",
        description=(
            "AI Identity \u2014 Offline Verification CLI\n"
            "Verify chain-of-custody certificates and HMAC audit chains\n"
            "from AI Identity forensic exports, completely offline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s report forensics_report.json\n"
            "  %(prog)s chain audit_export.json --verbose\n"
            "  %(prog)s chain audit_export.json --json\n"
            "  %(prog)s chain audit_export.json --key <retired-key>   # multi key-epoch\n"
            "  %(prog)s attestation envelope.json --pubkey signer.pem\n"
            "  %(prog)s attestation envelope.json --jwks keys.json\n"
            "\n"
            "Environment:\n"
            "  AI_IDENTITY_HMAC_KEY  HMAC secret key (required for report/chain)\n"
            "\n"
            "Exit codes:\n"
            "  0  Verification passed\n"
            "  1  Verification failed (invalid signature or broken chain)\n"
            "  2  Usage error (missing file, bad JSON, missing env var)\n"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Common flags
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output for each verification step",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (for CI/automation)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Verification command")

    # report subcommand
    report_parser = subparsers.add_parser(
        "report",
        help="Verify chain-of-custody certificate on an exported report",
        description="Verify the HMAC-SHA256 signature on an AI Identity forensics report.",
    )
    report_parser.add_argument(
        "file",
        help="Path to a JSON report file (ForensicsReportResponse)",
    )
    report_parser.add_argument(
        "--key",
        dest="extra_keys",
        action="append",
        metavar="KEY",
        help=(
            "Additional HMAC key to try (repeatable), e.g. a retired key from "
            "before a key regeneration. AI_IDENTITY_HMAC_KEY remains the primary."
        ),
    )

    # attestation subcommand
    attestation_parser = subparsers.add_parser(
        "attestation",
        help="Verify a forensic attestation DSSE envelope",
        description=(
            "Verify the ECDSA-P256 signature on an AI Identity forensic "
            "attestation envelope (DSSE + JCS). Requires the `cryptography` "
            "package (the `report` and `chain` commands do not)."
        ),
    )
    attestation_parser.add_argument(
        "file",
        help=(
            "Path to a JSON file containing either a bare DSSE envelope or the "
            "full response of GET /api/v1/sessions/{id}/attestation (the "
            "envelope is unwrapped from its `envelope` field automatically)"
        ),
    )
    attestation_parser.add_argument(
        "--pubkey",
        metavar="PEM",
        help=(
            "Path to a PEM-encoded ECDSA P-256 public key. Use when you've "
            "pinned a specific verification key. Mutually exclusive with --jwks."
        ),
    )
    attestation_parser.add_argument(
        "--jwks",
        metavar="JSON",
        help=(
            "Path to a JWKS file (as served by "
            "/.well-known/ai-identity-public-keys.json). The envelope's "
            "keyid is matched against the JWKS to pick the right public key. "
            "Mutually exclusive with --pubkey."
        ),
    )

    # inclusion-proof subcommand (Evidence Anchor)
    incl_parser = subparsers.add_parser(
        "inclusion-proof",
        help="Verify Merkle inclusion proofs against signed checkpoints",
        description=(
            "Verify that exported audit events are committed to a signed "
            "Merkle checkpoint, using only the public key — no shared secret. "
            "Reads the evidence-anchor/ files from a Case File bundle. Requires "
            "the `cryptography` package."
        ),
    )
    incl_parser.add_argument(
        "--checkpoints",
        metavar="JSON",
        required=True,
        help="Path to evidence-anchor/checkpoints.json",
    )
    incl_parser.add_argument(
        "--proofs",
        metavar="JSON",
        required=True,
        help="Path to evidence-anchor/inclusion-proofs.json",
    )
    incl_parser.add_argument(
        "--pubkey",
        metavar="PEM",
        help="Path to a PEM-encoded ECDSA P-256 public key. Mutually exclusive with --jwks.",
    )
    incl_parser.add_argument(
        "--jwks",
        metavar="JSON",
        help=(
            "Path to a JWKS file (/.well-known/ai-identity-public-keys.json). "
            "The checkpoint keyid is matched against it. Mutually exclusive with --pubkey."
        ),
    )

    # chain subcommand
    chain_parser = subparsers.add_parser(
        "chain",
        help="Verify the full HMAC audit chain from an exported audit log",
        description="Walk the sequential HMAC chain and verify each entry's integrity.",
    )
    chain_parser.add_argument(
        "file",
        help="Path to a JSON file containing audit log entries",
    )
    chain_parser.add_argument(
        "--key",
        dest="extra_keys",
        action="append",
        metavar="KEY",
        help=(
            "Additional HMAC key to try (repeatable). An org's history can span "
            "key epochs — rows written before your key existed, or before a key "
            "regeneration, verify only with that epoch's key. Supply every key "
            "you hold to cover all epochs; entries from epochs you don't hold "
            "are reported as 'not covered', never as tampering."
        ),
    )
    chain_parser.add_argument(
        "--expected-prev-hash",
        metavar="HEX",
        default=None,
        help=(
            "Expected prev_hash of the first entry in a partial export. "
            "Anchors the export to a known position in the full chain, "
            "proving no entries were prepended or the start-point was not altered. "
            "Obtain this value from the entry immediately before your export window."
        ),
    )
    chain_parser.add_argument(
        "--global",
        dest="global_chain",
        action="store_true",
        help=(
            "Force verification against the legacy platform-wide chain "
            "(prev_hash/entry_hash) instead of the per-org chain. By default, "
            "exports that carry per-org chain fields are verified per-org, "
            "which gives a tenant-scoped completeness proof (no gaps in "
            "this org's sequence). Use --global to verify older reports "
            "exported before the per-org chain migration."
        ),
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    global _NO_COLOR

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.no_color:
        _NO_COLOR = True

    if not args.command:
        parser.print_help()
        return 2

    if args.command == "report":
        return cmd_report(args)
    elif args.command == "chain":
        return cmd_chain(args)
    elif args.command == "attestation":
        return cmd_attestation(args)
    elif args.command == "inclusion-proof":
        return cmd_inclusion_proof(args)
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
