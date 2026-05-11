#!/usr/bin/env python3
"""Daily probe-signup summary email.

Queries MongoDB for probe signups in the last 24h plus all-time totals,
formats a plain-text summary including kill-criteria progress, and emails
the founder via Resend.

Required env:
    MONGODB_URI       — Atlas connection string (also used by landing-page)
    RESEND_API_KEY    — same key used by /api/probe-signup

Runs daily via .github/workflows/probe-summary.yml at 14:00 UTC.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

# pymongo is imported lazily in main() so format_summary() can be unit-tested
# in environments that don't have the driver installed.

DB_NAME = "ai_identity_probes"
COLL = "signups"

FROM = "AI Identity <noreply@ai-identity.co>"
TO = "jeff@ai-identity.co"

# Mirrors landing-page/src/app/api/probe-signup/route.ts ALLOWED_PROBES.
# Add a new probe slug here when you add one on the route side.
PROBE_SLUGS = [
    "ai-forensics-standalone",  # Milestone #48
    "pqc-readiness",  # Milestone #49
    "finance-compliance-pack",  # Milestone #50
    "newsletter",
]

# Kill-criteria thresholds for the 30-day windows. From Decision #45 /
# Milestones #48-50 descriptions. PULL = signups within the 30-day window
# that meet or exceed this number. Newsletter has no kill criterion.
PROBE_PULL_THRESHOLD = {
    "ai-forensics-standalone": 10,
    "pqc-readiness": 15,
    "finance-compliance-pack": 5,  # qualified FI inbound — counted as a floor signal
}

# Probe launch dates — counts since launch are the input to the kill review.
PROBE_LAUNCH = {
    "ai-forensics-standalone": datetime(2026, 5, 15, tzinfo=UTC),
    "pqc-readiness": datetime(2026, 5, 22, tzinfo=UTC),
    "finance-compliance-pack": datetime(2026, 5, 15, tzinfo=UTC),
    "newsletter": datetime(2026, 1, 1, tzinfo=UTC),  # was already in Footer
}

# Days from launch to the kill review.
KILL_WINDOW_DAYS = 30


def env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.exit(f"ERROR: {name} not set in environment")
    return val


def main() -> int:
    from pymongo import MongoClient

    mongodb_uri = env("MONGODB_URI")
    resend_key = env("RESEND_API_KEY")

    now = datetime.now(UTC)
    since_24h = now - timedelta(hours=24)

    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    coll = client[DB_NAME][COLL]

    # 24h counts per probe
    pipeline_24h = [
        {"$match": {"created_at": {"$gte": since_24h}}},
        {"$group": {"_id": "$probe", "n": {"$sum": 1}}},
    ]
    counts_24h = {row["_id"]: row["n"] for row in coll.aggregate(pipeline_24h)}

    # Per-probe-window counts (since launch, capped at kill window)
    counts_window: dict[str, int] = {}
    for slug in PROBE_SLUGS:
        launch = PROBE_LAUNCH[slug]
        coll_filter = {
            "probe": slug,
            "created_at": {"$gte": launch},
        }
        counts_window[slug] = coll.count_documents(coll_filter)

    # 24h recent emails for the inbox view — show probe + email + source
    recent = list(
        coll.find(
            {"created_at": {"$gte": since_24h}},
            {"email": 1, "probe": 1, "source": 1, "created_at": 1, "_id": 0},
        )
        .sort("created_at", -1)
        .limit(20)
    )

    total_24h = sum(counts_24h.values())
    body = format_summary(now, total_24h, counts_24h, counts_window, recent)
    send_via_resend(resend_key, body, total_24h)
    return 0


def format_summary(
    now: datetime,
    total_24h: int,
    counts_24h: dict[str, int],
    counts_window: dict[str, int],
    recent: list[dict],
) -> str:
    lines = [
        f"Daily probe-signup summary — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"Signups in last 24h: {total_24h}",
        "",
        "─── 24h by probe ──────────────────────────────",
    ]
    for slug in PROBE_SLUGS:
        n = counts_24h.get(slug, 0)
        lines.append(f"  {slug:30}  {n}")

    lines += ["", "─── Window-to-date (since launch) ─────────────"]
    for slug in PROBE_SLUGS:
        threshold = PROBE_PULL_THRESHOLD.get(slug)
        n = counts_window.get(slug, 0)
        launch = PROBE_LAUNCH[slug].strftime("%Y-%m-%d")
        if threshold is None:
            lines.append(f"  {slug:30}  {n}  (since {launch}, no kill criterion)")
        else:
            kill_date = (PROBE_LAUNCH[slug] + timedelta(days=KILL_WINDOW_DAYS)).strftime("%Y-%m-%d")
            pct = int(100 * n / threshold) if threshold else 0
            status = "PULL" if n >= threshold else f"{pct}% toward PULL ({threshold})"
            lines.append(f"  {slug:30}  {n}  →  {status}  (kill review {kill_date})")

    lines += ["", "─── Recent 24h (newest first, max 20) ─────────"]
    if not recent:
        lines.append("  (none)")
    else:
        for r in recent:
            ts = r["created_at"].strftime("%H:%M")
            email = (r.get("email") or "?")[:40]
            probe = r.get("probe", "?")
            src = (r.get("source") or "direct")[:40]
            lines.append(f"  {ts}  [{probe:28}]  {email}  ← {src}")

    lines += [
        "",
        "─── Notes ────────────────────────────────────",
        "Vercel Analytics is still source of truth for event counts.",
        "This summary reads from MongoDB (best-effort write from the route)",
        "so a number here that's lower than Analytics means a Mongo write",
        "failed mid-pipeline. Reconcile if the gap is large.",
        "",
        "Refs: Decision #45 (publication strategy), Milestones #48/#49/#50.",
    ]
    return "\n".join(lines)


def send_via_resend(api_key: str, body: str, total_24h: int) -> None:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    payload = {
        "from": FROM,
        "to": [TO],
        "subject": f"[Probes] Daily summary {today} — {total_24h} signups in 24h",
        "text": body,
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"Resend send: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: Resend send failed: HTTP {e.code} — {e.read().decode()[:300]}")


if __name__ == "__main__":
    sys.exit(main())
