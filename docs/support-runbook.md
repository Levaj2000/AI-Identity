# Post-Deployment Support Runbook

**Audience**: Solo founder + AI agents (CTO, PM, Security)
**Phase**: Design Partner (5 external teams, pre-revenue)
**Last updated**: 2026-03-17

---

## 1. Triage Levels

| Level | Name | Response Target | Examples |
|-------|------|-----------------|----------|
| **P0** | Service Down | 30 min | API returns 5xx globally, database unreachable, data loss |
| **P1** | Feature Broken | 4 hours | Agent creation fails, key rotation broken, audit chain corrupted |
| **P2** | Degraded | 24 hours | Slow responses (>2s), gateway suspended, rate limits too aggressive |
| **P3** | Minor / UX | 72 hours | Dashboard rendering issue, docs typo, confusing error message |
| **P4** | Enhancement | Next sprint | Feature request from partner, "nice to have" improvements |

### Triage Decision Tree

```
Is the API returning 5xx for all users?
  → YES → P0 (service down)
  → NO →
    Is a core workflow broken? (create agent, rotate key, audit)
      → YES → P1 (feature broken)
      → NO →
        Is performance degraded or a service partially down?
          → YES → P2 (degraded)
          → NO →
            Is it a UI/UX or non-blocking issue?
              → YES → P3 (minor)
              → NO → P4 (enhancement)
```

---

## 2. Services & Health Checks

| Service | URL | Health Endpoint | Hosting |
|---------|-----|-----------------|---------|
| API | `api.ai-identity.co` | `GET /health` | GKE Autopilot (us-east1) |
| Gateway | `gateway.ai-identity.co` | `GET /health` | GKE Autopilot (us-east1) |
| Dashboard | `dashboard.ai-identity.co` | Load `/` | Vercel |
| Landing Page | `ai-identity.co` | Load `/` | Vercel |
| Database | Neon PostgreSQL | Via API `/health` | Neon |
| CEO Dashboard | `ceo.corethread.tech` | `GET /api/v1/dashboard/summary` | Vercel |

### Quick Health Check (run from terminal)

```bash
echo "API:" && curl -sf https://api.ai-identity.co/health | jq .status
echo "Gateway:" && curl -sf https://gateway.ai-identity.co/health | jq .status
echo "Dashboard:" && curl -sf -o /dev/null -w "%{http_code}" https://dashboard.ai-identity.co
echo "Landing:" && curl -sf -o /dev/null -w "%{http_code}" https://ai-identity.co
```

Or run the automated smoke test:
```bash
./scripts/qa-smoke-test.sh
```

---

## 3. Expected Issues During Design Partner Phase

Based on the architecture and current state, these are the most likely issues partners will encounter:

### 3.1 Authentication Confusion (P3)
**Symptom**: Partner gets 401 on all API calls.
**Cause**: MVP auth uses email-as-key pattern. Partners may not understand what to pass in `X-API-Key`.
**Fix**: Direct them to the quickstart guide. Ensure their user exists in the database.
**Prevention**: Add clearer error messages for 401 responses.

### 3.2 Gateway Pod Unavailable (P2)
**Symptom**: Gateway returns 503 or connection refused.
**Cause**: GKE pod crashed, failed health check, or deployment rollout issue.
**Fix**: Check pod status with `kubectl get pods -n ai-identity`. Restart if needed with `kubectl rollout restart deployment/gateway -n ai-identity`.
**Prevention**: GKE Autopilot handles node provisioning automatically. Ensure liveness/readiness probes are configured correctly.

### 3.4 Key Rotation Grace Period Confusion (P3)
**Symptom**: Partner rotates a key, old key stops working "too soon" or "too late."
**Cause**: 24-hour grace period may not match their deployment cycle.
**Fix**: Explain the grace period in onboarding. Suggest they deploy the new key before the old one expires.
**Prevention**: Make grace period configurable per-agent in a future release.

### 3.5 Audit Log Empty (P2)
**Symptom**: Partner checks audit log, sees 0 entries despite using the API.
**Cause**: Audit entries are only created by gateway enforce calls, not by API management operations.
**Fix**: Explain that audit logs track gateway decisions, not management API calls.
**Prevention**: Sprint backlog item exists to audit management operations too.

### 3.6 Rate Limiting False Positives (P2)
**Symptom**: Partner gets 429 during normal development/testing.
**Cause**: Default rate limits (60 req/s per agent, 100 req/s per IP) may be hit during load testing or scripted integration tests.
**Fix**: Adjust rate limits for the partner's IP or agent during testing.
**Prevention**: Add a "testing mode" or higher limits for design partner accounts.

### 3.7 Credential Encryption Key Not Set (P1)
**Symptom**: Storing upstream credentials returns 500 error.
**Cause**: `CREDENTIAL_ENCRYPTION_KEY` environment variable not set in production.
**Fix**: Generate a Fernet key and set it via `kubectl create secret` or update the existing K8s secret.
**Prevention**: Startup health check should validate encryption key is set.

### 3.8 Database Connection Pool Exhaustion (P1)
**Symptom**: API returns 500 intermittently, logs show "too many connections."
**Cause**: Neon free tier has connection limits. Multiple services sharing one DB.
**Fix**: Restart the API service. Check for connection leaks.
**Prevention**: Add connection pooling (PgBouncer or SQLAlchemy pool limits).

---

## 4. Escalation Paths

```
Partner reports issue
  │
  ├─ P0/P1 → CEO gets Slack/text notification immediately
  │           Fix within response target
  │           Post-incident: write brief postmortem as insight
  │
  ├─ P2 → File as sprint item with [CTO] prefix
  │        Acknowledge to partner within 4 hours
  │        Fix in current sprint or next
  │
  ├─ P3 → File as sprint item with [PM] or [CTO] prefix
  │        Acknowledge to partner within 24 hours
  │        Fix in next sprint
  │
  └─ P4 → Log as insight (category: "product")
           Thank partner for feedback
           Prioritize during sprint planning
```

### Partner Communication Templates

**Acknowledgment** (use within response target):
> Thanks for flagging this, [Name]. I've confirmed the issue and I'm working on a fix. I'll update you within [timeframe].

**Resolution**:
> Fixed — [brief description of what was wrong and what we did]. Let me know if you see it again.

**Enhancement request**:
> Great idea — I've added it to our backlog. We're prioritizing based on what our design partners need most. I'll let you know when we pick it up.

---

## 5. Tooling

### Currently Active

| Tool | Purpose | Status |
|------|---------|--------|
| **GCP Console / kubectl** | API + Gateway deploy, logs, K8s secrets | ✅ Active |
| **Vercel Dashboard** | Dashboard + Landing deploy, logs | ✅ Active |
| **Neon Console** | Database monitoring, queries, branching | ✅ Active |
| **GitHub Issues** | Bug tracking (auto-created by QA workflow) | ✅ Active |
| **CEO Dashboard** | Sprint tracking, briefings, insights | ✅ Active |
| **QA Smoke Test** | Weekly automated 15-step production test | ✅ Active (GitHub Actions) |

| **UptimeRobot** | External uptime monitoring, alerting, public status page | ✅ Active |
| **CEO Dashboard Ops** | Live service health, triage reference, incident checklists | ✅ Active (ceo.corethread.tech/ops) |

### Recommended Additions (Design Partner Phase)

| Tool | Purpose | Priority | Cost |
|------|---------|----------|------|
| **Sentry** | Error tracking with stack traces, auto-grouping | P2 | Free tier covers 5K events/mo |

### UptimeRobot Setup

Monitors are provisioned via `scripts/setup-uptimerobot.sh`. Services monitored (5-min checks):

| Monitor | URL |
|---------|-----|
| AI Identity API | `https://api.ai-identity.co/health` |
| AI Identity Gateway | `https://gateway.ai-identity.co/health` |
| AI Identity Dashboard | `https://dashboard.ai-identity.co` |
| AI Identity Landing | `https://ai-identity.co` |
| CEO Dashboard | `https://ceo.corethread.tech` |

**Public Status Page**: Share with design partners for transparency.
**Alerts**: Email on all downtime, SMS for P0.

To re-run setup or add monitors:
```bash
export UPTIMEROBOT_API_KEY="ur_your_key_here"
./scripts/setup-uptimerobot.sh
```

---

## 6. Incident Response Checklist

### P0 — Service Down

```
□ Confirm the outage (check /health endpoint)
□ Check GKE pod status and logs (kubectl get pods, kubectl logs)
□ Check Neon console for database connectivity
□ If deploy failure: roll back with kubectl rollout undo
□ If database: check Neon status page, restart API service
□ If neither: check GKE logs for error pattern (kubectl logs, GCP Cloud Logging)
□ Once resolved: verify with qa-smoke-test.sh
□ Notify affected partners
□ Write postmortem as CEO Dashboard insight (category: "ops")
□ File prevention task as sprint item
```

### P1 — Feature Broken

```
□ Reproduce the issue locally
□ Check production logs via kubectl logs or GCP Cloud Logging
□ Identify root cause
□ Fix and deploy (or roll back if faster)
□ Verify with relevant qa-smoke-test.sh steps
□ Notify the reporting partner
□ File a sprint item if prevention work is needed
```

### P2 — Degraded

```
□ Confirm the degradation (timing, error rates)
□ Check if it's a known issue (pod crash loop, rate limit, resource limits)
□ Apply quick fix if available
□ File sprint item for proper fix
□ Acknowledge to partner
```

---

## 7. Design Partner SLA (Informal)

These are not contractual — they're internal targets to build trust:

| Metric | Target |
|--------|--------|
| API uptime | 99% (allows ~7 hours/month downtime) |
| P0 response | 30 minutes |
| P1 response | 4 hours (business hours) |
| P2 response | 24 hours |
| Weekly QA test | Automated, results posted to dashboard |
| Partner check-in | Weekly async (email/Slack) during first 30 days |

---

## 8. Weekly Support Rhythm

| Day | Activity |
|-----|----------|
| **Monday** | Automated QA smoke test runs (8am MT). Review results. |
| **Wednesday** | Check GKE/Neon dashboards for anomalies. Review partner feedback. |
| **Friday** | Quick partner check-in (async). Review any open GitHub issues. |

---

## 9. Rollback Procedures

### API (GKE)
1. Run `kubectl rollout undo deployment/api -n ai-identity`
2. Verify with `curl https://api.ai-identity.co/health`
3. Check rollout status with `kubectl rollout status deployment/api -n ai-identity`

### Dashboard (Vercel)
1. Go to Vercel dashboard → project → Deployments
2. Click the last successful deployment → "Promote to Production"
3. Verify the site loads

### Database (Neon)
1. Neon supports point-in-time recovery (PITR)
2. Go to Neon Console → Branches → Create branch from a past timestamp
3. Point the API at the recovery branch to verify data
4. Switch the main branch once confirmed

---

## 10. Contact Sheet

| Role | Contact | When |
|------|---------|------|
| CEO (you) | Direct | All P0, P1 escalations |
| GCP Support | GCP Console support | Infrastructure issues |
| Neon Support | support@neon.tech | Database issues |
| Vercel Support | Vercel dashboard ticket | Frontend deploy issues |
