# Incident Response Plan

**Document Owner:** Jeff Leva, CEO
**Version:** 1.0
**Last Reviewed:** March 25, 2026
**Next Review:** June 25, 2026

---

## 1. Purpose

This plan defines how AI Identity detects, responds to, and recovers from security incidents and service disruptions. It applies to all production systems: the Identity API, Proxy Gateway, Neon database, and supporting services (Clerk, Stripe, Vercel, Cloudflare).

## 2. Severity Levels

| Level | Definition | Example | Target Response |
|-------|-----------|---------|-----------------|
| **P1 -- Critical** | Customer data exposed, or full service outage | Database credential leak; API and Gateway both unreachable | Immediate (< 15 min) |
| **P2 -- High** | Major feature broken, security vulnerability found | Proxy Gateway returning 500s on all requests; auth bypass discovered | < 1 hour |
| **P3 -- Medium** | Degraded performance or partial feature failure | Elevated error rate on credential rotation endpoint; Sentry alert spike | < 4 hours |
| **P4 -- Low** | Minor issue, no customer impact | Dashboard CSS rendering bug; non-critical deprecation warning in logs | Next business day |

## 3. Detection Sources

- **Sentry:** Real-time error monitoring on both API (`api/app/main.py`) and Gateway (`gateway/app/main.py`). Alerts on new error types and error rate spikes.
- **Render Health Checks:** `/health` endpoint polled continuously on both `ai-identity-api` and `ai-identity-gateway`. Render alerts on consecutive failures.
- **UptimeRobot:** External HTTP monitoring of both services with HEAD requests to `/health`. Alerts via email and SMS on downtime.
- **Audit Log Anomalies:** HMAC-chained audit logs allow detection of tampering. Broken chains indicate unauthorized modification.
- **Neon Dashboard:** Database metrics and connection count monitoring for unusual activity.
- **Stripe Webhooks:** Failed payment events and unexpected billing activity surface via Stripe dashboard alerts.

## 4. Response Procedures

### P1 -- Critical

1. **Assess** -- Confirm the incident via Sentry, Render dashboard, and UptimeRobot. Determine scope.
2. **Contain** -- Immediately rotate any compromised secrets using `scripts/rotate_master_key.py` and Render environment variable updates. If the API is compromised, disable the Render service to stop traffic.
3. **Communicate** -- Notify affected customers within 1 hour via email. Post status update to status page.
4. **Remediate** -- Deploy fix via emergency hotfix process (see Change Management Policy).
5. **Recover** -- Verify service health, confirm audit log integrity, restore normal operation.

### P2 -- High

1. **Assess** -- Check Sentry stack traces and Render deploy logs. Identify root cause.
2. **Contain** -- If security-related, rotate affected API keys. If deploy-related, roll back via Render dashboard.
3. **Communicate** -- Notify affected customers within 4 hours if customer-facing.
4. **Remediate** -- Fix and deploy through standard PR process (expedited review).

### P3 -- Medium

1. **Assess** -- Review Sentry errors and Render metrics. Determine if issue is trending worse.
2. **Remediate** -- Create a GitHub issue, fix through normal PR workflow.
3. **Communicate** -- No external communication unless issue persists beyond 24 hours.

### P4 -- Low

1. Track in GitHub Issues. Address in normal development cycle.

## 5. Containment Quick Reference

| Threat | Containment Action |
|--------|--------------------|
| Leaked database credential | Rotate `DATABASE_URL` in Neon console, update in Render env vars, restart services |
| Leaked encryption key | Run `scripts/rotate_master_key.py --old-key <old> --new-key <new>`, update `CREDENTIAL_ENCRYPTION_KEY` in Render |
| Compromised Clerk account | Revoke all active sessions in Clerk dashboard, rotate `CLERK_ISSUER` if needed |
| Suspicious API traffic | Enable Cloudflare rate limiting rules, review Render access logs |
| Compromised GitHub token | Revoke token in GitHub settings, audit recent commits and PR merges |

## 6. Evidence Preservation

- **Audit logs** are append-only and integrity-protected with HMAC chains (`AUDIT_HMAC_KEY`). Each entry's hash includes the previous entry's hash, making tampering detectable.
- **Render deploy logs** are retained by Render and provide a timeline of all deployments.
- **Git history** is immutable and provides a complete record of all code changes.
- **Sentry events** are retained per Sentry's data retention policy and provide stack traces and context.
- During an incident, take screenshots of relevant dashboards before making changes.

## 7. Post-Incident Review

Within 48 hours of resolving any P1 or P2 incident, conduct a blameless postmortem:

**Template:**
1. **Incident summary** -- What happened, when, and who was affected.
2. **Timeline** -- Chronological log from detection to resolution.
3. **Root cause** -- The underlying technical or process failure.
4. **Impact** -- Number of users affected, duration, data implications.
5. **What went well** -- Detection, response, or communication that worked.
6. **What can improve** -- Gaps in monitoring, slow response, missing runbooks.
7. **Action items** -- Specific tasks with owners and deadlines to prevent recurrence.

Postmortems are stored in the repository under `docs/postmortems/` and linked in the relevant GitHub issue.

---

## SOC 2 Mapping

| Trust Services Criteria | How This Plan Addresses It |
|------------------------|----------------------------|
| CC7.2 -- Monitoring for anomalies | Section 3: Sentry, Render health checks, UptimeRobot, audit log anomaly detection |
| CC7.3 -- Incident identification and response | Sections 2, 4: severity classification and per-level response procedures |
| CC7.4 -- Incident containment and remediation | Section 5: containment quick reference with specific actions per threat |
| CC7.5 -- Incident recovery | Section 4: recovery steps within each severity procedure |
| CC7.6 -- Post-incident analysis | Section 7: blameless postmortem template and storage |
| CC1.2 -- Integrity of evidence | Section 6: append-only HMAC-chained audit logs, immutable git history |
