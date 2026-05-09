#!/usr/bin/env python3
"""Sync CEO Dashboard calendar with derived events.

Idempotently creates calendar events from:
  1. Decisions with review_date in the next 14 days
  2. Standing weekly cadence (Mon All-Hands, Fri Weekly Review)

"Idempotent" means: a tag-based fingerprint per derived event is checked
against existing calendar entries before creating a new one. Re-running
the script does not create duplicates.

Usage:
    CEO_API_KEY=... python3 scripts/sync_calendar_from_dashboard.py
    python3 scripts/sync_calendar_from_dashboard.py --dry-run

Designed to run as a daily GitHub Actions cron — see
.github/workflows/ceo-dashboard-sync.yml.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from json import dumps, loads
from pathlib import Path
from typing import Any
from urllib import error as uerror
from urllib import request as ureq

API_BASE = os.environ.get("CEO_API_URL", "https://ceo-agent-evfb.onrender.com")
COMPANY = "ai-identity"
TAG_PREFIX = "auto:dashboard-sync"  # all auto-managed events carry this tag


def _api_key() -> str:
    key = os.environ.get("CEO_API_KEY")
    if not key:
        # Fallback: read from local CEO-Dashboard .env if present (dev convenience)
        env = Path.home() / "Dev" / "CEO-Dashboard" / "backend" / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("CEO_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        sys.exit("ERROR: CEO_API_KEY not set and not found in ~/Dev/CEO-Dashboard/backend/.env")
    return key


def _request(method: str, path: str, body: dict | None = None) -> Any:
    url = f"{API_BASE}{path}"
    data = dumps(body).encode() if body is not None else None
    req = ureq.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
    )
    try:
        with ureq.urlopen(req, timeout=20) as r:
            return loads(r.read())
    except uerror.HTTPError as e:
        sys.exit(f"ERROR: {method} {path} -> HTTP {e.code}: {e.read().decode()[:300]}")


def _existing_events() -> list[dict]:
    return _request("GET", f"/api/v1/calendar?company={COMPANY}")


def _has_event_with_tag(events: list[dict], tag: str) -> bool:
    return any(tag in (e.get("tags") or []) for e in events)


def _create(
    title: str, when: dt.datetime, *, event_type: str, tags: list[str], description: str = ""
):
    body = {
        "company_slug": COMPANY,
        "title": title,
        "description": description,
        "start_date": int(when.timestamp()),
        "event_type": event_type,
        "author": "ceo",
        "tags": [TAG_PREFIX, *tags],
    }
    _request("POST", "/api/v1/calendar", body)


def derive_decision_review_events(events: list[dict], dry_run: bool) -> int:
    """Decisions with review_date in next 14 days -> 'Review decision' events."""
    decisions = _request("GET", f"/api/v1/decisions?company={COMPANY}")
    now = dt.datetime.now()
    horizon = now + dt.timedelta(days=14)
    created = 0
    for d in decisions:
        rd = d.get("review_date")
        if not rd:
            continue
        rd_dt = dt.datetime.fromtimestamp(rd)
        if not (now <= rd_dt <= horizon):
            continue
        # Skip if already reviewed-status
        if d.get("status") in ("decided", "superseded", "reversed"):
            continue
        tag = f"decision:{d['id']}:review"
        if _has_event_with_tag(events, tag):
            continue
        title = f"Review decision #{d['id']}: {d['title'][:60]}"
        desc = (d.get("decision_text") or "")[:300]
        if dry_run:
            print(f"  [DRY] would create: {rd_dt.date()}  {title}")
        else:
            _create(title, rd_dt, event_type="follow-up", tags=[tag], description=desc)
            print(f"  ✓ created:        {rd_dt.date()}  {title}")
        created += 1
    return created


def derive_standing_routines(events: list[dict], dry_run: bool) -> int:
    """Add standing weekly events for the next 4 weeks if not already present."""
    now = dt.datetime.now()
    created = 0

    # Friday 16:00 — Weekly Review (covers decisions, pipeline, gate state)
    # Monday 09:00 — All-Hands kickoff
    routines = [
        (
            "weekly-review",
            "Weekly Review (decisions + pipeline + gate state)",
            "meeting",
            4,
            16,
            0,
        ),  # Fri = 4
        ("all-hands", "All-Hands kickoff", "meeting", 0, 9, 0),  # Mon = 0
    ]
    for slug, title, etype, weekday, hour, minute in routines:
        # Find the next 4 occurrences from today
        days_ahead = (weekday - now.weekday()) % 7
        # If it's that day already and the time has passed, skip to next week
        target_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if days_ahead == 0 and now > target_today:
            days_ahead = 7
        first = (now + dt.timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        for week in range(4):
            occurrence = first + dt.timedelta(weeks=week)
            tag = f"routine:{slug}:{occurrence.date().isoformat()}"
            if _has_event_with_tag(events, tag):
                continue
            if dry_run:
                print(f"  [DRY] would create: {occurrence.date()} {hour:02}:{minute:02}  {title}")
            else:
                _create(title, occurrence, event_type=etype, tags=[tag])
                print(f"  ✓ created:        {occurrence.date()} {hour:02}:{minute:02}  {title}")
            created += 1
    return created


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="Show what would change, don't write")
    args = p.parse_args()

    print(f"▶ Calendar sync starting (mode={'DRY' if args.dry_run else 'WRITE'})")
    events = _existing_events()
    print(f"  Existing events: {len(events)}")

    print("→ Decision review reminders (next 14 days)")
    n_dec = derive_decision_review_events(events, args.dry_run)
    print(f"   {n_dec} event(s) {'would be ' if args.dry_run else ''}created")

    print("→ Standing routines (next 4 weeks)")
    n_rt = derive_standing_routines(events, args.dry_run)
    print(f"   {n_rt} event(s) {'would be ' if args.dry_run else ''}created")

    print(f"✅ Done. Total {'planned' if args.dry_run else 'written'}: {n_dec + n_rt}")


if __name__ == "__main__":
    main()
