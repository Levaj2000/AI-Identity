# Uptime monitor runbook

**Owner:** Jeff Leva
**Last reviewed:** 2026-04-16
**Related incident:** [audit-infra 2026-04-16](#incident-2026-04-16-stale-monitors)

External uptime monitors are the last line of defense before customers
notice production is down. This runbook captures (a) the canonical list
of endpoints that must be monitored, (b) what counts as healthy, and
(c) a one-time repointing procedure for moving monitors off the retired
Render URLs.

## Endpoints to monitor

| Service | URL | Check interval | Method | Expected status | Expected body substring |
|---------|-----|----------------|--------|-----------------|-------------------------|
| API | `https://api.ai-identity.co/health` | 1 min | GET | `200` | `"status":"ok"` |
| Gateway | `https://gateway.ai-identity.co/health` | 1 min | GET | `200` | `"database":"connected"` |
| Dashboard | `https://dashboard.ai-identity.co/` | 5 min | GET | `200` | `<!doctype html` |
| Public keys | `https://api.ai-identity.co/.well-known/ai-identity-public-keys.json` | 15 min | GET | `200` | `"keys"` |
| Landing page | `https://ai-identity.co/` | 5 min | GET | `200` | `<!doctype html` |

Notes:

- **API + Gateway at 1-min cadence** because a fail-closed gateway that's
  itself down still fails closed (clients get 503) but we want to know
  within a minute.
- **Dashboard + landing at 5-min** because they're Vercel-hosted and
  Vercel monitors itself; our monitor is just a belt-and-suspenders.
- **Public keys at 15-min** because the JSON is small and static but
  critical for offline attestation verification; a drop would break
  forensic CLI verification until the next deploy.
- **Never monitor** `/api/v1/` endpoints requiring auth — a 401 is not a
  health signal, and storing a real API key in an external monitor is an
  extra blast-radius exposure.

## Expected response shapes

### API — `GET /health`

```json
{
  "status": "ok",
  "version": "0.2.0"
}
```

Returns 503 if the health check is wedged (rare). Any other status is
an outage signal.

### Gateway — `GET /health`

```json
{
  "status": "ok",
  "database": "connected",
  "circuit_breaker": "closed"
}
```

A response with `"database": "disconnected"` or
`"circuit_breaker": "open"` is a **partial** failure. The monitor body
check on `"database":"connected"` catches both because the substring
won't match. Good.

### Public keys — `GET /.well-known/ai-identity-public-keys.json`

```json
{
  "keys": [
    {
      "kid": "session-attestation:v1",
      "alg": "ES256",
      "use": "sig",
      "pem": "-----BEGIN PUBLIC KEY-----\n…\n-----END PUBLIC KEY-----\n"
    }
  ]
}
```

(Endpoint ships in sprint item #265.) Until that lands, skip this
monitor — don't add a check for a route that doesn't exist yet.

## Incident 2026-04-16 — stale monitors

### What happened

- Better Stack sent a "paused" notification at 2026-04-16 13:11 / 13:14
  for `ai-identity-api.onrender.com/health` and
  `ai-identity-gateway.onrender.com/health`.
- Both URLs are the retired Render URLs — production moved to GKE weeks
  ago (`api.ai-identity.co` / `gateway.ai-identity.co`). The monitors
  had not been repointed.
- Separately and coincidentally, the QA Admin Check failed because a
  merged migration never ran on GKE (tracked in
  [#142](https://github.com/Levaj2000/AI-Identity/pull/142)).

### Repointing checklist

Do this in Better Stack (or whichever uptime monitor is live — see
[scripts/setup-uptimerobot.sh](../../scripts/setup-uptimerobot.sh) for
the prior UptimeRobot setup if it's still the source of truth).

1. Log into Better Stack → Monitors.
2. For the monitor `ai-identity-api.onrender.com/health`:
   - Change URL → `https://api.ai-identity.co/health`
   - Set body check → contains `"status":"ok"`
   - Unpause
3. For the monitor `ai-identity-gateway.onrender.com/health`:
   - Change URL → `https://gateway.ai-identity.co/health`
   - Set body check → contains `"database":"connected"`
   - Unpause
4. Add new monitors for any rows in the table above that don't have one
   yet (dashboard, landing, public keys if shipped).
5. Confirm each monitor's notification channel routes to
   `levaj2000@gmail.com` (or the on-call alias, once we have one).
6. Delete or archive the retired `*.onrender.com` monitors after 7 days
   of green on the new ones.

### Acceptance check

Visit each monitor 10 minutes after repointing. The status should read
green (not "awaiting first check" and not "alerted"). If any row is not
green, capture the response body with:

```bash
curl -sS -i https://api.ai-identity.co/health
curl -sS -i https://gateway.ai-identity.co/health
```

…and treat it as an unresolved incident until the monitor recovers.

## Why external monitors at all

Internal metrics (Prometheus, Sentry) tell us when an observed request
fails. External monitors tell us when **no requests are observed**. The
2026-04-16 incident hit both failure modes:

- **Observed**: Sentry caught the 500 on POST /api/v1/agents (internal).
- **Unobserved**: audit writes silently dropped for 3 days because the
  gateway swallowed the exception. Nobody noticed because there was no
  external "is anyone writing audit entries?" check. [PR
  #143](https://github.com/Levaj2000/AI-Identity/pull/143) adds a
  Prometheus counter; this runbook locks in the external checks that
  would have caught it from the outside too.

## Alert routing

Current: email to `levaj2000@gmail.com`. Good enough for solo founder.

Before enterprise pilots: add PagerDuty / OpsGenie integration so alerts
route through on-call rotation with escalation. Track as a separate
work item — out of scope for this runbook.
