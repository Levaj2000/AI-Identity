#!/usr/bin/env python3
"""Export design-partner pipeline state as a CSV + post a summary briefing.

Reads the pipeline tracking decision (#40 by default) and produces:
  1. CSV file at marketing/sales/pipeline-snapshots/YYYY-MM-DD.csv
  2. A briefing posted to the dashboard with summary + risk callouts

The briefing is what shows up on the Team page; the CSV is for any
spreadsheet workflow (Google Sheets import, Excel, etc.).

The pipeline format is parsed from the decision's `reasoning` field —
specifically the section between '=== PIPELINE — YYYY-MM-DD ===' and
'=== ANALYSIS ==='. Each numbered prospect is read as a record with
key:value pairs.

Usage:
    CEO_API_KEY=... python3 scripts/export_pipeline_snapshot.py
    python3 scripts/export_pipeline_snapshot.py --dry-run

Designed for weekly cadence — see .github/workflows/ceo-dashboard-sync.yml.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
from json import dumps, loads
from pathlib import Path
from urllib import error as uerror
from urllib import request as ureq

API_BASE = os.environ.get("CEO_API_URL", "https://ceo-agent-evfb.onrender.com")
COMPANY = "ai-identity"
DEFAULT_DECISION_ID = 40
SNAPSHOT_DIR = Path(__file__).parent.parent / "marketing" / "sales" / "pipeline-snapshots"


def _api_key() -> str:
    key = os.environ.get("CEO_API_KEY")
    if key:
        return key
    env = Path.home() / "Dev" / "CEO-Dashboard" / "backend" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("CEO_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("ERROR: CEO_API_KEY not set")


def _request(method: str, path: str, body: dict | None = None):
    url = f"{API_BASE}{path}"
    data = dumps(body).encode() if body is not None else None
    req = ureq.Request(
        url,
        data=data,
        method=method,
        headers={"X-API-Key": _api_key(), "Content-Type": "application/json"},
    )
    try:
        with ureq.urlopen(req, timeout=20) as r:
            return loads(r.read())
    except uerror.HTTPError as e:
        sys.exit(f"ERROR: {method} {path} -> HTTP {e.code}: {e.read().decode()[:300]}")


# ── Parsing the pipeline section out of decision reasoning ────────────────


PROSPECT_FIELDS = ["Stage", "Owner", "Target close", "Last touch", "Blockers", "Reality", "Risk"]


def parse_pipeline(reasoning: str) -> tuple[str, list[dict]]:
    """Return (snapshot_date, list-of-prospect-dicts) parsed from reasoning."""
    m = re.search(r"=== PIPELINE — (\d{4}-\d{2}-\d{2}) ===(.*?)===", reasoning, re.DOTALL)
    if not m:
        return ("unknown", [])
    snapshot_date = m.group(1)
    block = m.group(2)
    prospects: list[dict] = []
    # Each prospect block starts with "N. Name" and contains "  - Field: value"
    chunks = re.split(r"\n\s*\d+\.\s+", "\n" + block)
    for chunk in chunks[1:]:
        lines = [ln.rstrip() for ln in chunk.split("\n") if ln.strip()]
        if not lines:
            continue
        # Name might include "— Contact" — strip the contact suffix for the name field
        name_line = lines[0].strip()
        # Pattern: "Name — Contact Name (email/url)"  or  "Name"
        name_parts = re.split(r"\s+—\s+", name_line, maxsplit=1)
        name = name_parts[0].strip()
        contact = name_parts[1].strip() if len(name_parts) > 1 else ""
        record: dict[str, str] = {"Name": name, "Contact": contact}
        for line in lines[1:]:
            mfield = re.match(r"\s*-\s+([A-Z][a-zA-Z ]+):\s*(.*)", line)
            if mfield:
                k = mfield.group(1).strip()
                v = mfield.group(2).strip()
                record[k] = v
        prospects.append(record)
    return snapshot_date, prospects


# ── Output: CSV ───────────────────────────────────────────────────────────


def write_csv(snapshot_date: str, prospects: list[dict]) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{snapshot_date}.csv"
    headers = ["Name", "Contact", *PROSPECT_FIELDS]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for p in prospects:
            w.writerow(p)
    return path


# ── Output: briefing posted to dashboard ─────────────────────────────────


def build_briefing_body(snapshot_date: str, prospects: list[dict]) -> str:
    today = dt.date.today()
    gate_date = dt.date(2026, 6, 30)
    days_to_gate = (gate_date - today).days

    paid = sum(1 for p in prospects if "paid" in (p.get("Stage") or "").lower())
    verbal_or_pilot = sum(
        1
        for p in prospects
        if any(s in (p.get("Stage") or "").lower() for s in ("verbal", "free pilot", "pilot"))
    )
    total = len(prospects)

    lines = [
        f"## Pipeline snapshot — {snapshot_date}",
        "",
        f"**Days to H1 hard gate (2026-06-30):** {days_to_gate}",
        f"**Funnel:** {total} prospect(s) tracked · {paid} paid · {verbal_or_pilot} verbal/pilot · gate target: 3 paid",
        "",
        "| Name | Contact | Stage | Owner | Target Close | Blockers |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for p in prospects:
        lines.append(
            f"| {p.get('Name', '')} | {p.get('Contact', '')} | {p.get('Stage', '')} | "
            f"{p.get('Owner', '')} | {p.get('Target close', '')} | {p.get('Blockers', '')} |"
        )
    lines.append("")
    if paid < 3:
        lines.append(
            f"⚠️ **Gate at risk** — {paid}/3 paid with {days_to_gate} days remaining. "
            "Either backfill outreach (need 6-9 prospects to safely land 3) or formally re-baseline the gate."
        )
    else:
        lines.append("✅ Gate count met. Confirm contracts countersigned + revenue recognized.")
    lines.append("")
    lines.append("Source: Decision #40 · auto-generated by `scripts/export_pipeline_snapshot.py`")
    return "\n".join(lines)


def post_briefing(snapshot_date: str, prospects: list[dict], dry_run: bool) -> None:
    body = build_briefing_body(snapshot_date, prospects)
    if dry_run:
        print("--- briefing body (DRY) ---")
        print(body)
        return
    payload = {
        "company_slug": COMPANY,
        "title": f"Pipeline snapshot — {snapshot_date}",
        "body": body,
        "author": "sales",
        "tags": ["auto:pipeline-snapshot", f"snapshot:{snapshot_date}"],
    }
    _request("POST", "/api/v1/briefings", payload)
    print("✓ briefing posted to dashboard")


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--decision-id", type=int, default=DEFAULT_DECISION_ID)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"▶ Fetching decision #{args.decision_id}")
    d = _request("GET", f"/api/v1/decisions/{args.decision_id}")
    snapshot_date, prospects = parse_pipeline(d.get("reasoning") or "")
    print(f"  Snapshot date: {snapshot_date}")
    print(f"  Parsed {len(prospects)} prospect(s)")
    if not prospects:
        sys.exit("ERROR: no prospects parsed; decision reasoning may not match expected format")

    if args.dry_run:
        print("--- prospects (DRY) ---")
        for pr in prospects:
            print(
                f"  - {pr.get('Name')}: stage={pr.get('Stage', '?')}, blockers={pr.get('Blockers', '?')[:40]}"
            )
        post_briefing(snapshot_date, prospects, dry_run=True)
        return

    csv_path = write_csv(snapshot_date, prospects)
    print(f"✓ CSV written: {csv_path.relative_to(Path(__file__).parent.parent)}")

    post_briefing(snapshot_date, prospects, dry_run=False)
    print("✅ Done.")


if __name__ == "__main__":
    main()
