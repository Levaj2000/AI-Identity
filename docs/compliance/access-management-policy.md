# Access Management Policy

**Document Owner:** Jeff Leva, CEO
**Version:** 1.0
**Last Reviewed:** March 25, 2026
**Next Review:** June 25, 2026

---

## 1. Purpose

This policy defines how AI Identity controls access to production systems, infrastructure services, and customer data. It applies to all personnel, service accounts, and automated systems.

## 2. Production Access Inventory

| Service | Access Holder | Auth Method | MFA Required |
|---------|--------------|-------------|--------------|
| GitHub (Levaj2000/AI-Identity) | Jeff Leva | SSO + PAT | Yes |
| GCP / GKE (ai-identity-api, ai-identity-gateway) | Jeff Leva | Google SSO | Yes |
| Neon (PostgreSQL) | Jeff Leva | Email/password | Yes |
| Clerk (user auth dashboard) | Jeff Leva | Email/password | Yes |
| Stripe (billing dashboard) | Jeff Leva | Email/password | Yes |
| Vercel (dashboard frontend) | Jeff Leva | GitHub SSO | Yes |
| Cloudflare (DNS/CDN) | Jeff Leva | Email/password | Yes |
| Sentry (error monitoring) | Jeff Leva | GitHub SSO | Yes |

As a solo-founder company, Jeff Leva is currently the only individual with production access. When additional team members are onboarded, this table will be updated and the approval process in Section 3 will apply.

## 3. Access Granting and Revocation

**Granting access:**
1. New personnel submit an access request specifying the service and permission level needed.
2. Jeff Leva (or a designated admin) approves and provisions the minimum role required.
3. The grant is recorded in an internal access log with date, service, role, and approver.

**Revoking access:**
1. On personnel departure or role change, all service accounts are disabled within 24 hours.
2. API keys and tokens associated with the individual are rotated immediately.
3. Revocation is confirmed and logged.

## 4. Service Accounts and API Keys

AI Identity uses the following service-level secrets, managed as Kubernetes secrets in GKE:

- **DATABASE_URL** -- Neon PostgreSQL connection string (pooled via Neon's connection pooler)
- **CREDENTIAL_ENCRYPTION_KEY** -- Fernet key for encrypting upstream provider credentials at rest
- **AUDIT_HMAC_KEY** -- HMAC key used for tamper-evident audit log chains
- **INTERNAL_SERVICE_KEY** -- Shared secret for API-to-Gateway internal calls
- **CLERK_ISSUER** -- Clerk JWT issuer URL for token verification

All secrets are stored as Kubernetes secrets in the GKE cluster, managed via `kubectl`. They are never committed to the repository. The `.env.example` file documents required variables without values.

## 5. Database Access Controls

- **Neon PostgreSQL** is the sole production database, hosted in the Oregon region.
- Direct database access requires the Neon dashboard (authenticated, MFA-enabled).
- Application connections use Neon's built-in connection pooling to limit concurrent connections.
- Row-Level Security (RLS) policies enforce tenant isolation -- queries are scoped to the authenticated user's `clerk_user_id`.
- The application connects with a single database role (`neondb_owner`). No direct shell access to the database server exists.

## 6. Key Rotation

- **Encryption keys:** Rotated using `scripts/rotate_master_key.py`, which re-encrypts all upstream credentials in a single transaction. The script supports `--dry-run` for safe verification.
- **AUDIT_HMAC_KEY:** Rotated with a transition period where both old and new keys are accepted.
- **INTERNAL_SERVICE_KEY:** Rotated by updating the Kubernetes secret and restarting both deployments (`kubectl rollout restart`).
- **Target cadence:** All secrets rotated at minimum every 90 days, or immediately upon suspected compromise.

## 7. Principle of Least Privilege

- Production services run with only the environment variables they require (see K8s deployment manifests for per-service configuration).
- The Gateway service has no direct write access to user or billing tables.
- CI/CD (GitHub Actions) has no access to production secrets -- tests run against an in-memory SQLite database.
- Vercel (dashboard hosting) has no server-side access to the database; it communicates exclusively through the API.

## 8. Quarterly Access Review

Every quarter, the document owner will:
1. Review the access inventory table above and confirm it is accurate.
2. Verify that MFA is enabled on all services.
3. Confirm no unnecessary API keys or tokens exist.
4. Check GCP and Neon audit logs for unexpected access patterns.
5. Update this document with review date and any changes made.

---

## SOC 2 Mapping

| Trust Services Criteria | How This Policy Addresses It |
|------------------------|------------------------------|
| CC6.1 -- Logical access security | Sections 2-4: access inventory, granting/revocation, secret management |
| CC6.2 -- Credentials and authentication | Section 2: MFA required on all services |
| CC6.3 -- Access authorization | Section 3: explicit approval process, least privilege (Section 7) |
| CC6.5 -- Restriction and revocation | Section 3: 24-hour revocation, immediate key rotation |
| CC6.6 -- Periodic access review | Section 8: quarterly review cadence |
