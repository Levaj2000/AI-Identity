# AI Identity — Architecture Overview

**Last Updated:** 2026-03-25
**Status:** Current (Sprint 7)

---

## System Overview

AI Identity is a security and compliance platform for AI agents. It provides identity management, policy enforcement, credential vaulting, and tamper-evident audit trails for organizations deploying AI agents in production.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                 │
│                                                                     │
│   Landing Page (Vercel)          Dashboard (Vercel)                 │
│   ai-identity.co                 dashboard.ai-identity.co          │
│   React + Vite                   React + Vite + Clerk Auth         │
│   11 pages                       15 pages                          │
└──────────┬──────────────────────────────┬───────────────────────────┘
           │                              │
           │ HTTPS                        │ HTTPS + JWT
           │                              │
┌──────────▼──────────────────────────────▼───────────────────────────┐
│                      SERVICE LAYER (Render, Oregon)                 │
│                                                                     │
│  ┌─────────────────────────┐    ┌──────────────────────────────┐   │
│  │   API Service            │    │   Gateway Service             │   │
│  │   ai-identity-api        │    │   ai-identity-gateway         │   │
│  │   FastAPI :8001          │    │   FastAPI :8002                │   │
│  │                          │    │                                │   │
│  │   12 routers:            │    │   Enforcement pipeline:        │   │
│  │   • agents               │    │   1. Rate limiter (100/s IP)   │   │
│  │   • keys                 │◄───│   2. Key validation            │   │
│  │   • policies             │    │   3. Agent status check        │   │
│  │   • credentials          │    │   4. Policy evaluation         │   │
│  │   • audit                │    │   5. Circuit breaker           │   │
│  │   • billing (Stripe)     │    │   6. Audit log (HMAC)          │   │
│  │   • compliance           │    │                                │   │
│  │   • qa                   │    │   FAIL-CLOSED: Any error       │   │
│  │   • usage                │    │   results in DENY              │   │
│  │   • capabilities         │    │                                │   │
│  │   • admin                │    │   Circuit breaker:             │   │
│  │   • auth                 │    │   5 failures/60s → OPEN        │   │
│  └──────────┬───────────────┘    └──────────────┬─────────────────┘   │
│             │                                   │                    │
│             │          HMAC-SHA256               │                    │
│             │◄──────── service auth ────────────►│                    │
│             │                                   │                    │
└─────────────┼───────────────────────────────────┼────────────────────┘
              │                                   │
              │         SQL + SSL                 │
              │                                   │
┌─────────────▼───────────────────────────────────▼────────────────────┐
│                      DATA LAYER                                      │
│                                                                      │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │   Neon PostgreSQL (Oregon)                                    │   │
│   │                                                               │   │
│   │   9 tables:                                                   │   │
│   │   ├── users          (Clerk ID, tier, Stripe IDs, quotas)    │   │
│   │   ├── agents         (UUID, status, capabilities, metadata)  │   │
│   │   ├── agent_keys     (SHA-256 hash, type, rotation, expiry)  │   │
│   │   ├── policies       (JSONB rules, versioned, one active)    │   │
│   │   ├── audit_log      (HMAC chain, PII-sanitized, RLS)       │   │
│   │   ├── upstream_creds (Fernet encrypted, per-provider)        │   │
│   │   ├── compliance_*   (frameworks, checks, reports, results)  │   │
│   │   └── qa_runs        (15-step checklist, dual sign-off)      │   │
│   │                                                               │   │
│   │   Security: RLS (user_id), SSL required, append-only audit   │   │
│   └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                               │
│                                                                      │
│   Clerk (Auth)     Stripe (Billing)    Sentry (Errors)              │
│   JWT + JWKS       Checkout + Portal   Optional DSN                 │
│                    Webhooks → tier                                   │
│                    sync                                              │
│                                                                      │
│   UptimeRobot      GitHub Actions      Render Cron                  │
│   HEAD /health     CI (lint+test+      Keepalive every              │
│   3 monitors       build)              10 min                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Services

### 1. API Service (`ai-identity-api`)

**Purpose:** Core business logic — CRUD for agents, keys, policies, credentials; billing; compliance; QA.

| Property | Value |
|----------|-------|
| Runtime | Python 3.11 / FastAPI / Uvicorn |
| Port | 8001 |
| Deploy | Render (Starter tier, auto-deploy from main) |
| Auth | Clerk JWT or X-API-Key (legacy) |
| Database | Neon PostgreSQL (SQLAlchemy + Alembic) |

**Routers (12):**

| Router | Prefix | Key Endpoints |
|--------|--------|---------------|
| auth | `/auth` | `GET /me`, `POST /login` |
| agents | `/agents` | CRUD for AI agents |
| keys | `/agents/{id}/keys` | Create, rotate (24h grace), revoke |
| policies | `/agents/{id}/policies` | Versioned policy CRUD |
| credentials | `/agents/{id}/credentials` | Fernet-encrypted vault |
| audit | `/audit` | Logs, stats, chain verify, forensic export |
| billing | `/billing` | Stripe Checkout, Portal, webhook |
| compliance | `/compliance` | Frameworks, assessments, sign-off |
| qa | `/qa` | 15-step E2E checklist with dual sign-off |
| usage | `/usage` | Aggregated usage, tier info |
| capabilities | `/capabilities` | Predefined capability catalog |
| admin | `/admin` | Platform stats, user management |

### 2. Gateway Service (`ai-identity-gateway`)

**Purpose:** Real-time policy enforcement proxy. Evaluates every agent request against active policies. Fail-closed design.

| Property | Value |
|----------|-------|
| Runtime | Python 3.11 / FastAPI / Uvicorn |
| Port | 8002 |
| Deploy | Render (Starter tier, auto-deploy from main) |
| Latency target | < 50ms per enforcement decision |

**Enforcement Pipeline (6 steps):**

```
Request → Rate Limiter → Key Validation → Agent Status → Policy Match → Circuit Breaker → Audit Log
            │                │                │              │               │              │
            ▼                ▼                ▼              ▼               ▼              ▼
         429 Too          401 Invalid      403 Agent      403 Policy      503 Circuit    200 + decision
         Many Req         Key              Inactive       Denied          Open           (allow/deny)
```

- **Rate limiter:** 100 req/s per IP, 60 req/s per agent key
- **Circuit breaker:** CLOSED → OPEN (5 failures/60s) → HALF_OPEN (test single request)
- **Timeout:** 500ms max for policy evaluation (4 thread pool workers)
- **Fail-closed:** Any exception or timeout = DENY

### 3. Dashboard (Frontend)

**Purpose:** Customer-facing UI for managing agents, viewing forensics, running compliance checks.

| Property | Value |
|----------|-------|
| Framework | React + TypeScript + Vite |
| Auth | Clerk (SSO-ready) |
| Deploy | Vercel (preview deploys on PR) |
| Pages | 15 |

**Key Pages:**
- **Overview** — Agent count, recent activity, health status
- **Agents** — CRUD, key management, policy editor
- **Forensics** — Timeline + table view, filters, HMAC chain verification, detail drawer, anomaly detection, CSV/JSON export
- **Compliance** — Framework assessments, evidence collection, sign-off workflow
- **QA Checklist** — 15-step E2E validation with dual sign-off
- **Usage & Billing** — Tier status, Stripe checkout/portal
- **Admin** — User management, platform stats

### 4. Landing Page

**Purpose:** Marketing site at ai-identity.co.

| Property | Value |
|----------|-------|
| Framework | React + TypeScript + Vite |
| Deploy | Vercel |
| Pages | 11 (Home, How It Works, Docs, Security, Privacy, Terms, Blog, Contact, Brand, Integrations, Careers) |

---

## Shared Code (`common/`)

The `common` package is imported by both API and Gateway services.

| Module | Purpose |
|--------|---------|
| `models/` | 9 SQLAlchemy models (User, Agent, AgentKey, Policy, AuditLog, UpstreamCredential, Compliance*, QARun) |
| `auth/keys.py` | Key generation (UUID), SHA-256 hashing, prefix system (`aid_sk_`, `aid_admin_`) |
| `auth/internal.py` | HMAC-SHA256 service-to-service authentication |
| `audit/writer.py` | Append-only audit log with HMAC integrity chain |
| `audit/sanitizer.py` | PII redaction (email, phone, SSN, tokens, IP addresses) |
| `crypto/fernet.py` | Fernet encryption for credential vault |
| `validation/policy.py` | Declarative policy rule evaluation |
| `config/settings.py` | Pydantic settings (DB, Stripe, Clerk, CORS, security) |
| `schemas/` | Pydantic response models |

---

## Security Architecture

### Defense in Depth (7 layers)

```
Layer 1: Network        → HTTPS/TLS (Render + Cloudflare)
Layer 2: Headers        → HSTS, CSP, X-Frame-Options, etc.
Layer 3: Auth           → Clerk JWT or API key (SHA-256 hashed)
Layer 4: Rate limiting  → Per-IP (100/s) + per-key (60/s)
Layer 5: Policy         → Fail-closed gateway enforcement
Layer 6: Data           → Fernet encryption, RLS, PII sanitization
Layer 7: Audit          → HMAC-SHA256 chain, append-only, tamper-evident
```

### Key Security Properties

| Property | Implementation |
|----------|---------------|
| Keys never stored in plaintext | SHA-256 hash only; raw key shown once at creation |
| Fail-closed enforcement | Any error → DENY (gateway default) |
| Tamper-evident audit | HMAC-SHA256 chain; each entry hashes previous |
| Credential encryption | Fernet (symmetric) with master key rotation |
| Tenant isolation | Row-level security on user_id |
| PII redaction | 12-field sanitizer on all logs |
| Key rotation | 24-hour grace period; old key valid during overlap |
| Circuit breaker | Prevents cascade failures (5 failures/60s → OPEN) |

---

## Database Schema

```
users ──────────┐
  │              │
  │ 1:N          │ 1:N
  ▼              ▼
agents        compliance_reports
  │              │
  ├── 1:N → agent_keys          compliance_results
  ├── 1:N → policies               │
  ├── 1:N → audit_log          compliance_checks
  └── 1:N → upstream_credentials    │
                                compliance_frameworks
qa_runs (user_id FK)
```

### Tier Quotas

| Tier | Agents | Keys/Agent | Requests/Mo | Credentials | Audit Retention |
|------|--------|-----------|-------------|-------------|-----------------|
| Free | 5 | 2 | 2,000 | 1 | 30 days |
| Pro ($79/mo) | 50 | 10 | 75,000 | 10 | 90 days |
| Business ($299/mo) | 200 | 25 | 500,000 | 50 | 365 days |
| Enterprise (custom) | ∞ | ∞ | ∞ | ∞ | ∞ |

---

## Infrastructure

```
┌─────────────────────────────────────────────────┐
│ Render (Oregon)                                  │
│  ├── ai-identity-api      (Starter, auto-deploy) │
│  ├── ai-identity-gateway   (Starter, auto-deploy) │
│  └── ai-identity-keepalive (Cron, 10 min)        │
├──────────────────────────────────────────────────┤
│ Vercel                                           │
│  ├── dashboard.ai-identity.co (preview deploys)  │
│  └── ai-identity.co          (landing page)      │
├──────────────────────────────────────────────────┤
│ Neon (Oregon)                                    │
│  └── PostgreSQL (connection pooling, SSL)        │
├──────────────────────────────────────────────────┤
│ External Services                                │
│  ├── Clerk       → JWT auth, SSO-ready           │
│  ├── Stripe      → Subscriptions, checkout       │
│  ├── Sentry      → Error monitoring (optional)   │
│  ├── UptimeRobot → Health checks (HEAD /health)  │
│  └── GitHub      → CI/CD (lint, test, build)     │
└──────────────────────────────────────────────────┘
```

---

## CI/CD Pipeline

```
PR opened → GitHub Actions:
  ├── Python: ruff lint + format
  ├── Python: pytest (SQLite)
  ├── Dashboard: ESLint + Prettier + tsc
  └── Dashboard: Vite build

Merge to main → Render auto-deploy:
  ├── API: pip install + alembic upgrade + uvicorn
  ├── Gateway: pip install + uvicorn
  └── Keepalive: no rebuild needed

Post-deploy → QA smoke test (optional):
  └── 15-step E2E checklist via POST /api/v1/qa/run
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `seed.py` | Initial data (users, agents) |
| `seed_compliance.py` | Compliance frameworks (NIST, EU AI Act, SOC 2) |
| `generate_internal_key.py` | Generate INTERNAL_SERVICE_KEY |
| `rotate_master_key.py` | Re-encrypt all credentials with new master key |
| `qa-smoke-test.sh` | 15-step E2E QA |
| `keepalive_cron.py` | Prevent cold starts (Render cron) |
| `setup-uptimerobot.sh` | Configure monitoring |

---

## Compliance Documentation

Located in `/docs/compliance/`:

| Document | SOC 2 Criteria |
|----------|---------------|
| Access Management Policy | CC6.1, CC6.2, CC6.3 |
| Incident Response Plan | CC7.3, CC7.4, CC7.5 |
| Change Management Policy | CC8.1 |

---

## Data Flow: Agent Request Lifecycle

```
1. Agent sends request with API key (aid_sk_xxx)
2. Gateway receives at POST /gateway/enforce
3. Rate limiter checks per-IP and per-key limits
4. Key validated (SHA-256 hash lookup)
5. Agent status checked (must be active)
6. Policy evaluated (endpoint + method rules)
7. Circuit breaker checked (if DB errors accumulating)
8. Decision logged to audit_log (HMAC chained)
9. Response returned: {decision: allow|deny, status_code, deny_reason}
```
