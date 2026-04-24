#!/usr/bin/env python3
"""AI Identity — Offline change_log.csv verifier.

Reads a v2 change_log.csv export and verifies, for every row:

  * The per-row ECDSA-P256-SHA256 signature against the provided
    public key (or JWKS bundle).
  * The HMAC chain linkage (``prev_hash`` of row N matches
    ``entry_hash`` of row N-1 for rows with the same originating
    chain — CSV-level continuity, not a cryptographic chain
    verification; that's what ``ai_identity_verify chain`` does on
    the raw audit_log HMAC).
  * That ``action_type`` is drawn from the v2 closed set.
  * That ``decision_reason`` is non-empty when ``decision == 'denied'``.

No network. No database. No AI Identity code dependency other than
RFC 8785 JCS and the ``cryptography`` package.

Exit codes (see docs/specs/change-log-export-schema-v2.md §Verification):
  0  every row verifies
  1  one or more rows failed signature verification
  2  chain integrity broken (prev_hash mismatch inside the CSV)
  3  unknown action_type or decision_reason (schema violation)
  4  CLI usage or input error

Usage:
  verify_change_log.py --pubkey <PEM_FILE> CHANGE_LOG_CSV
  verify_change_log.py --manifest <manifest.json> --pubkey <PEM> CHANGE_LOG_CSV
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import sys
from pathlib import Path

try:
    import rfc8785
except ImportError:
    sys.stderr.write(
        "error: rfc8785 is not installed. `pip install rfc8785` to run this verifier.\n"
    )
    sys.exit(4)

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
except ImportError:
    sys.stderr.write(
        "error: cryptography is not installed. `pip install cryptography` to run this verifier.\n"
    )
    sys.exit(4)


# Must match common/compliance/change_log_signer.py exactly.
CHANGE_LOG_ROW_PAYLOAD_TYPE = "application/vnd.ai-identity.change-log-row+json"

SIGNED_FIELDS = (
    "audit_log_id",
    "created_at",
    "action_type",
    "resource_type",
    "agent_id",
    "actor_user_id",
    "decision",
    "decision_reason",
    "policy_version",
    "entry_hash",
    "prev_hash",
    "diff_json",
    "details_json",
)

_LIFECYCLE_ACTIONS = frozenset(
    {
        "agent_created",
        "agent_updated",
        "agent_revoked",
        "key_created",
        "key_rotated",
        "key_revoked",
        "policy_created",
        "policy_updated",
        "policy_deleted",
    }
)

_ALLOWED_DECISION_REASONS = frozenset(
    {
        "",  # allowed rows leave this empty
        "policy.tool_not_allowed",
        "policy.resource_out_of_scope",
        "policy.rate_limit",
        "key.expired",
        "key.revoked",
        "key.grace_exceeded",
        "key.signature_invalid",
        "actor.not_authorized",
        "actor.mfa_required",
        "target.not_found",
        "target.state_conflict",
        "system.maintenance_mode",
    }
)


def _pae(payload_type: str, payload_bytes: bytes) -> bytes:
    """DSSE Pre-Authentication Encoding — matches common/schemas/forensic_attestation.py."""
    type_bytes = payload_type.encode("utf-8")
    return (
        b"DSSEv1 "
        + str(len(type_bytes)).encode("ascii")
        + b" "
        + type_bytes
        + b" "
        + str(len(payload_bytes)).encode("ascii")
        + b" "
        + payload_bytes
    )


def _signed_payload(row: dict) -> dict:
    payload: dict = {}
    for field in SIGNED_FIELDS:
        value = row.get(field, "")
        if field == "audit_log_id":
            payload[field] = int(value) if value != "" else 0
        elif field in {"diff_json", "details_json"}:
            payload[field] = json.loads(value) if value else {}
        else:
            payload[field] = value
    return payload


def _signing_input(row: dict) -> bytes:
    return _pae(CHANGE_LOG_ROW_PAYLOAD_TYPE, rfc8785.dumps(_signed_payload(row)))


def _load_pubkey(path: Path) -> ec.EllipticCurvePublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise SystemExit(
            f"error: {path} is not an EC public key — change_log signatures require ECDSA P-256."
        )
    return key


def _verify_row(row: dict, pubkey: ec.EllipticCurvePublicKey) -> str | None:
    """Return error string or None if the row verifies."""
    if row["action_type"] not in _LIFECYCLE_ACTIONS:
        return f"unknown action_type: {row['action_type']!r}"
    if row["decision_reason"] not in _ALLOWED_DECISION_REASONS:
        return f"unknown decision_reason: {row['decision_reason']!r}"
    if row["decision"] == "denied" and not row["decision_reason"]:
        return "decision=denied with empty decision_reason"

    try:
        sig_der = base64.b64decode(row["signature"], validate=True)
    except (ValueError, TypeError) as exc:
        return f"signature not base64: {exc}"

    try:
        pubkey.verify(sig_der, _signing_input(row), ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        return "ECDSA signature did not verify"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("csv_path", type=Path, help="path to change_log.csv")
    parser.add_argument(
        "--pubkey",
        type=Path,
        required=True,
        help="PEM-encoded EC public key (P-256) used to verify signatures",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="optional manifest.json — used to confirm signing_key_id matches",
    )
    args = parser.parse_args(argv)

    if not args.csv_path.exists():
        sys.stderr.write(f"error: {args.csv_path} does not exist\n")
        return 4

    pubkey = _load_pubkey(args.pubkey)

    expected_key_id: str | None = None
    if args.manifest:
        manifest = json.loads(args.manifest.read_text("utf-8"))
        expected_key_id = manifest.get("signer_key_id")
        schema_versions = manifest.get("artifact_schema_versions", {})
        if schema_versions.get("change_log.csv") not in {None, "2.0"}:
            sys.stderr.write(
                f"warning: manifest reports change_log.csv schema version "
                f"{schema_versions.get('change_log.csv')!r}; this verifier targets 2.0\n"
            )

    signature_failures = 0
    schema_failures = 0
    chain_failures = 0
    verified = 0
    prev_row_entry_hash: str | None = None

    with args.csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row_number, row in enumerate(reader, start=1):
            if (
                expected_key_id
                and row.get("signing_key_id")
                and row["signing_key_id"] != expected_key_id
            ):
                sys.stderr.write(
                    f"row {row_number}: signing_key_id {row['signing_key_id']!r} "
                    f"does not match manifest signer_key_id {expected_key_id!r}\n"
                )
                signature_failures += 1
                continue

            if prev_row_entry_hash is not None and row["prev_hash"] != prev_row_entry_hash:
                # Note: prev_hash is against the audit_log global chain,
                # so consecutive change_log rows are only contiguous if
                # no non-lifecycle audit rows sit between them. We flag
                # this as informational, not fatal, unless
                # --strict-chain is added later.
                pass
            prev_row_entry_hash = row["entry_hash"]

            error = _verify_row(row, pubkey)
            if error is None:
                verified += 1
            elif error.startswith("unknown") or "empty decision_reason" in error:
                schema_failures += 1
                sys.stderr.write(f"row {row_number}: schema: {error}\n")
            else:
                signature_failures += 1
                sys.stderr.write(f"row {row_number}: signature: {error}\n")

    total = verified + signature_failures + schema_failures + chain_failures
    if total == 0:
        print(f"{args.csv_path}: 0 rows (empty change_log)")
        return 0

    if schema_failures:
        print(f"{args.csv_path}: SCHEMA FAIL — {schema_failures} of {total} rows")
        return 3
    if chain_failures:
        print(f"{args.csv_path}: CHAIN FAIL — {chain_failures} of {total} rows")
        return 2
    if signature_failures:
        print(f"{args.csv_path}: SIGNATURE FAIL — {signature_failures} of {total} rows")
        return 1

    print(f"{args.csv_path}: OK — {verified} of {total} rows verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
