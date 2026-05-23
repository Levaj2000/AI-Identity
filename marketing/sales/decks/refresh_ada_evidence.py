"""Refresh the full Ada evidence pack — one command, freshly pulled from prod.

Re-runs the audit-snapshot + chain-verify queries against the live API,
exports the CSV, and rebuilds the dogfood-proof PDF. Run this the morning
of any demo so the timestamps in the artifacts are recent.

Outputs (overwritten in place):
    marketing/sales/ada-audit-snapshot-2026-05-12.json
    marketing/sales/ada-chain-verify-2026-05-12.json
    marketing/sales/ada-audit-snapshot-2026-05-12.csv
    marketing/sales/ada-dogfood-proof-2026-05-12.pdf

Usage:
    cd /Users/jeffleva/Dev/AI-Identity
    .venv/bin/python marketing/sales/decks/refresh_ada_evidence.py

Requires:
    AI_IDENTITY_ADMIN_KEY env var set to your admin email
    (defaults to levaj2000@gmail.com if unset — change that for your tenant)
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────

ADA_AGENT_ID = "2e22d027-dd98-4096-a000-ddceb0e5d269"
API_URL = "https://api.ai-identity.co"
ADMIN_KEY = os.getenv("AI_IDENTITY_ADMIN_KEY", "levaj2000@gmail.com")

HERE = Path(__file__).resolve().parent.parent  # marketing/sales/
SNAPSHOT_JSON = HERE / "ada-audit-snapshot-2026-05-12.json"
VERIFY_JSON = HERE / "ada-chain-verify-2026-05-12.json"
SNAPSHOT_CSV = HERE / "ada-audit-snapshot-2026-05-12.csv"

# Decision normalization — server returns past-tense for legacy rows
DECISION_NORM = {
    "allow": "allow",
    "allowed": "allow",
    "deny": "deny",
    "denied": "deny",
}

CSV_COLS = [
    "entry_id",
    "created_at",
    "agent_id",
    "method",
    "endpoint",
    "decision",
    "policy_version",
    "status_code",
    "latency_ms",
    "upstream_latency_ms",
    "correlation_id",
    "entry_hash",
    "prev_hash",
]


def _http_get(path: str, params: dict) -> dict | list:
    """Plain stdlib GET with proper URL encoding (so '+' in timestamps survives)."""
    qs = urllib.parse.urlencode(params)
    url = f"{API_URL}{path}?{qs}"
    req = urllib.request.Request(url, headers={"X-API-Key": ADMIN_KEY})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fetch_snapshot() -> list[dict]:
    """Pull all audit entries for Ada from 2026-01-01 onward (wide enough)."""
    body = _http_get(
        "/api/v1/audit",
        {
            "agent_id": ADA_AGENT_ID,
            "start_date": "2026-01-01T00:00:00+00:00",
            "limit": 500,
        },
    )
    entries = body if isinstance(body, list) else body.get("items", body.get("entries", []))
    if not entries:
        raise SystemExit("No audit entries returned — check ADMIN_KEY and agent_id.")
    return entries


def fetch_verify() -> dict:
    return _http_get("/api/v1/audit/verify", {"agent_id": ADA_AGENT_ID})


def write_csv(entries: list[dict], path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        for e in sorted(entries, key=lambda x: x["created_at"]):
            meta = e.get("request_metadata") or {}
            w.writerow(
                {
                    "entry_id": e["id"],
                    "created_at": e["created_at"],
                    "agent_id": e["agent_id"],
                    "method": e["method"],
                    "endpoint": e["endpoint"],
                    "decision": DECISION_NORM.get(e["decision"], e["decision"]),
                    "policy_version": meta.get("policy_version", ""),
                    "status_code": meta.get("status_code", ""),
                    "latency_ms": e.get("latency_ms", ""),
                    "upstream_latency_ms": meta.get("upstream_latency_ms", ""),
                    "correlation_id": e["correlation_id"],
                    "entry_hash": e["entry_hash"],
                    "prev_hash": e["prev_hash"],
                }
            )


def rebuild_proof_pdf() -> None:
    """Re-run the proof PDF builder so it picks up the refreshed JSON."""
    builder = Path(__file__).resolve().parent / "build_ada_proof_pdf.py"
    subprocess.run([sys.executable, str(builder)], check=True)


def main() -> None:
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    print(f"[{stamp}] Refreshing Ada evidence pack from {API_URL}…")

    entries = fetch_snapshot()
    verify = fetch_verify()

    SNAPSHOT_JSON.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"  ✓ {SNAPSHOT_JSON.name}  ({len(entries)} entries)")

    VERIFY_JSON.write_text(json.dumps(verify, indent=2) + "\n")
    print(
        f"  ✓ {VERIFY_JSON.name}  (verified={verify.get('entries_verified')}/{verify.get('total_entries')})"
    )

    write_csv(entries, SNAPSHOT_CSV)
    print(f"  ✓ {SNAPSHOT_CSV.name}")

    rebuild_proof_pdf()
    print("  ✓ ada-dogfood-proof-2026-05-12.pdf")

    print(
        f"\nReady. {len(entries)} entries, chain verdict: "
        f"{'VALID' if verify.get('valid') else 'BROKEN'}."
    )


if __name__ == "__main__":
    main()
