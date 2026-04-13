"""
Keepalive + daily tasks for Render cron job.

1. Sends lightweight HEAD requests to API and Gateway health endpoints
   to prevent Render Starter instances from spinning down (~15 min idle timeout).
2. Once per day (first run after 16:00 UTC), triggers the follow-up email cron
   to send 5-day check-in emails to new users.

Runs every 10 minutes via Render cron job (see render.yaml).
"""

import datetime
import os

import httpx

SERVICES = [
    ("API", "https://api.ai-identity.co/health"),
    ("Gateway", "https://gateway.ai-identity.co/health"),
]

FOLLOWUP_URL = "https://api.ai-identity.co/api/internal/email/send-followups"
CLEANUP_URL = "https://api.ai-identity.co/api/internal/cleanup/inactive-users"

TIMEOUT = 30


def main():
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    now = datetime.datetime.utcnow()
    print(f"{ts} Keepalive ping starting...")

    with httpx.Client(timeout=TIMEOUT) as client:
        for name, url in SERVICES:
            try:
                r = client.head(url)
                status = "healthy" if r.status_code == 200 else f"status {r.status_code}"
                print(f"{ts} {name}: {status}")
            except Exception as e:
                print(f"{ts} {name}: error - {e}")

        # Run follow-up email check once per day (first run in the 16:00 UTC hour)
        if now.hour == 16 and now.minute < 10:
            _send_followup_emails(ts, client)

        # Run inactive user cleanup weekly (Sundays at 04:00 UTC)
        if now.weekday() == 6 and now.hour == 4 and now.minute < 10:
            _cleanup_inactive_users(ts, client)

    print(f"{ts} Keepalive complete.")


def _send_followup_emails(ts: str, client: httpx.Client):
    """Trigger the follow-up email endpoint on the API."""
    internal_key = os.environ.get("INTERNAL_SERVICE_KEY", "")
    if not internal_key:
        print(f"{ts} Follow-up emails: skipped (no INTERNAL_SERVICE_KEY)")
        return

    try:
        r = client.post(
            FOLLOWUP_URL,
            headers={"x-internal-key": internal_key},
        )
        if r.status_code == 200:
            data = r.json()
            print(
                f"{ts} Follow-up emails: sent={data.get('sent', 0)}, eligible={data.get('eligible', 0)}"
            )
        else:
            print(f"{ts} Follow-up emails: status {r.status_code}")
    except Exception as e:
        print(f"{ts} Follow-up emails: error - {e}")


def _cleanup_inactive_users(ts: str, client: httpx.Client):
    """Trigger inactive free-tier user cleanup on the API."""
    internal_key = os.environ.get("INTERNAL_SERVICE_KEY", "")
    if not internal_key:
        print(f"{ts} User cleanup: skipped (no INTERNAL_SERVICE_KEY)")
        return

    try:
        r = client.post(
            CLEANUP_URL,
            headers={"x-internal-key": internal_key},
            params={"inactivity_days": 90, "dry_run": False},
        )
        if r.status_code == 200:
            data = r.json()
            print(
                f"{ts} User cleanup: deleted={data.get('deleted', 0)}, "
                f"eligible={data.get('eligible', 0)}"
            )
        else:
            print(f"{ts} User cleanup: status {r.status_code}")
    except Exception as e:
        print(f"{ts} User cleanup: error - {e}")


if __name__ == "__main__":
    main()
