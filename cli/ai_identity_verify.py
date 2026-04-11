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
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

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
      - prev_hash from chain
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
        print()

        if args.verbose:
            print(_dim(f"  Expected:  {expected}"))
            print(_dim(f"  Got:       {fields['report_signature']}"))
            print()

    return 0 if valid else 1


# ── Chain verification ──────────────────────────────────────────────────


def _load_chain_entries(path: str) -> list[dict[str, Any]]:
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


def _cmd_chain_full(
    args: argparse.Namespace, key: bytes, entries: list[dict[str, Any]], total: int
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
    args: argparse.Namespace, key: bytes, entries: list[dict[str, Any]], total: int
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

        # Recompute HMAC using the entry's own prev_hash
        recomputed = _compute_entry_hash(key, entry, entry_prev)
        if not hmac.compare_digest(recomputed, stored_hash):
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


def cmd_chain(args: argparse.Namespace) -> int:
    """Verify the HMAC audit chain (full or partial)."""
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

    # Detect partial chain: first entry's prev_hash is not GENESIS
    is_partial = entries[0].get("prev_hash", "") != GENESIS

    if is_partial:
        return _cmd_chain_partial(args, key, entries, total)
    else:
        return _cmd_chain_full(args, key, entries, total)


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
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
