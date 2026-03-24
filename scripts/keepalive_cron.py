"""
Keepalive ping for Render cron job.

Sends lightweight HEAD requests to API and Gateway health endpoints
to prevent Render Starter instances from spinning down (~15 min idle timeout).

Runs every 10 minutes via Render cron job (see render.yaml).
"""

import datetime

import httpx

SERVICES = [
    ("API", "https://ai-identity-api.onrender.com/health"),
    ("Gateway", "https://ai-identity-gateway.onrender.com/health"),
]

TIMEOUT = 30


def main():
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{ts} Keepalive ping starting...")

    for name, url in SERVICES:
        try:
            r = httpx.head(url, timeout=TIMEOUT)
            status = "healthy" if r.status_code == 200 else f"status {r.status_code}"
            print(f"{ts} {name}: {status}")
        except Exception as e:
            print(f"{ts} {name}: error - {e}")

    print(f"{ts} Keepalive complete.")


if __name__ == "__main__":
    main()
