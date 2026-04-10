#!/usr/bin/env python3
"""AI Identity — Offline Verification CLI.

Standalone, zero-dependency tool for auditors to verify AI Identity
forensic exports completely offline — no database, no API, no network.

Two verification modes:
  report  — verify the HMAC chain-of-custody certificate on an exported report
  chain   — verify the full sequential HMAC audit chain from exported entries

Requires: Python 3.9+, no external packages.
HMAC key: set AI_IDENTITY_HMAC_KEY environment variable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import io
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

__version__ = "1.0.0"
TOOL_NAME = "ai-identity-verify"
GENESIS = "GENESIS"

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
        "generated_at": generated_at,
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
        report_id, generated_at, chain_valid, total_entries, entries_verified,
    )
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _canonical_entry_payload(entry: Dict[str, Any], prev_hash: str) -> bytes:
    """Build the canonical JSON payload for an audit chain entry.

    Mirrors ``common.audit.writer._canonical_payload`` exactly:
      - agent_id as string
      - cost_estimate_usd as string (or null)
      - created_at as ISO-8601 string
      - decision, endpoint, method as-is
      - latency_ms as int (or null)
      - prev_hash from chain
      - request_metadata as dict
    """
    cost = entry.get("cost_estimate_usd")
    payload = {
        "agent_id": str(entry["agent_id"]),
        "cost_estimate_usd": str(cost) if cost is not None else None,
        "created_at": entry["created_at"],
        "decision": entry["decision"],
        "endpoint": entry["endpoint"],
        "latency_ms": entry.get("latency_ms"),
        "method": entry["method"],
        "prev_hash": prev_hash,
        "request_metadata": entry.get("request_metadata", {}),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _compute_entry_hash(key: bytes, entry: Dict[str, Any], prev_hash: str) -> str:
    """Compute HMAC-SHA256 hex digest for an audit chain entry."""
    message = _canonical_entry_payload(entry, prev_hash)
    return hmac.new(key, message, hashlib.sha256).hexdigest()


# ── File loading ────────────────────────────────────────────────────────


def _load_json(path: str) -> Any:
    """Load and parse a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(2)


# ── Report verification ────────────────────────────────────────────────


def _extract_report_fields(data: Dict[str, Any]) -> Dict[str, Any]:
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
    if total == 0:
        filled = width
    else:
        filled = int(width * current / total)
    bar = "\u2588" * filled + " " * (width - filled)
    return f"[{bar}] {current}/{total}"


def cmd_report(args: argparse.Namespace) -> int:
    """Verify a report's chain-of-custody certificate."""
    key = _get_hmac_key()
    data = _load_json(args.file)
    fields = _extract_report_fields(data)

    expected = _compute_report_signature(
        key,
        report_id=fields["report_id"],
        generated_at=fields["generated_at"],
        chain_valid=fields["chain_valid"],
        total_entries=fields["total_entries"],
        entries_verified=fields["entries_verified"],
    )

    valid = hmac.compare_digest(expected, fields["report_signature"])

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
        print(json.dumps(result, indent=2))
    else:
        chain_mark = _green("\u2713") if fields["chain_valid"] else _red("\u2717")
        sig_text = _green("VALID \u2713") if valid else _red("INVALID \u2717")

        print(f"\n{_bold('AI Identity \u2014 Report Verification')}")
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
        print()

        if args.verbose:
            print(_dim(f"  Expected:  {expected}"))
            print(_dim(f"  Got:       {fields['report_signature']}"))
            print()

    return 0 if valid else 1


# ── Chain verification ──────────────────────────────────────────────────


def _load_chain_entries(path: str) -> List[Dict[str, Any]]:
    """Load audit chain entries from a JSON file.

    Accepts either:
      - A JSON array of entry objects  (bare export)
      - A JSON object with an "events" key containing the array
        (ForensicsReportResponse shape)
    """
    data = _load_json(path)

    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get("events", data.get("entries", []))
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

    return entries


def cmd_chain(args: argparse.Namespace) -> int:
    """Verify the full HMAC audit chain."""
    key = _get_hmac_key()
    entries = _load_chain_entries(args.file)
    total = len(entries)

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
                },
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"\n{_bold('AI Identity \u2014 Audit Chain Verification')}")
            print("\u2550" * 39)
            print(f"  File:         {os.path.basename(args.file)}")
            print("  Entries:      0")
            print()
            print(f"  Result:       {_green('CHAIN INTACT \u2713')} (empty)")
            print()
        return 0

    expected_prev_hash = GENESIS
    verified = 0
    break_info: Optional[Dict[str, Any]] = None

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

        # 2. Recompute HMAC and compare
        recomputed = _compute_entry_hash(key, entry, entry_prev)
        if not hmac.compare_digest(recomputed, stored_hash):
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
        if not args.json and not args.verbose and total >= 100 and (
            (i + 1) % max(1, total // 32) == 0 or i + 1 == total
        ):
            sys.stdout.write(
                f"\r  Verifying chain...  {_progress_bar(i + 1, total)}"
            )
            sys.stdout.flush()

    intact = break_info is None

    if args.json:
        details: Dict[str, Any] = {
            "file": os.path.basename(args.file),
            "total_entries": total,
            "entries_verified": verified,
            "chain_intact": intact,
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

        print(f"\n{_bold('AI Identity \u2014 Audit Chain Verification')}")
        print("\u2550" * 39)
        print(f"  File:         {os.path.basename(args.file)}")
        print(f"  Entries:      {total}")
        print()

        if not args.verbose:
            print(f"  Verifying chain...  {_progress_bar(verified, total)}")
        print()

        if intact:
            print(f"  Result:       {_green('CHAIN INTACT \u2713')}")
            print(f"  Verified:     {verified}/{total} entries")
        else:
            assert break_info is not None
            print(f"  Result:       {_red('CHAIN BROKEN \u2717')}")
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


# ── CLI argument parsing ────────────────────────────────────────────────


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
            "\n"
            "Environment:\n"
            "  AI_IDENTITY_HMAC_KEY  HMAC secret key (required)\n"
            "\n"
            "Exit codes:\n"
            "  0  Verification passed\n"
            "  1  Verification failed (invalid signature or broken chain)\n"
            "  2  Usage error (missing file, bad JSON, missing env var)\n"
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )

    # Common flags
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed output for each verification step",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON (for CI/automation)",
    )
    parser.add_argument(
        "--no-color", action="store_true",
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
        "file", help="Path to a JSON report file (ForensicsReportResponse)",
    )

    # chain subcommand
    chain_parser = subparsers.add_parser(
        "chain",
        help="Verify the full HMAC audit chain from an exported audit log",
        description="Walk the sequential HMAC chain and verify each entry's integrity.",
    )
    chain_parser.add_argument(
        "file", help="Path to a JSON file containing audit log entries",
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
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
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
