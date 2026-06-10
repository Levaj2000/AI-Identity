# Changelog

All notable changes to AI Identity are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- R&D strategy deliverables under `docs/strategy/`: an Agent Accountability **landscape & next-bet** report, a frontier **"Horizon 2030"** report (3–5yr; "evidence is the durable asset" thesis), and two gated design proposals — **Evidence Anchor** (transparency-log + offline verifier) and **Case File** (court-ready evidence export). Reports ship with reproducible PDF generators.
- Forensics report (**Case File**): exports now carry a plain-English **Reliability Statement** (FRE 702 / Daubert + ISO/IEC 27037 framing) describing how integrity is established, what the signature attests, the timestamp source, and the honest limits of key-holder verification. Surfaced on `/api/v1/audit/report` (JSON) and the verification bundle.
- **Case File** branding for the forensics evidence export: the verification bundle, downloaded report JSON, and CSV are now `case-file-*` (was `forensics-*`), the bundle README documents the Reliability Statement, and the API doc summaries say "Case File." Endpoint paths unchanged (non-breaking).

### Security
- **Removed the legacy `X-API-Key`=email authentication fallback** in the main API (`api/app/auth.py`) and the Mandate Service (`mandate/app/auth.py`). It matched the `X-API-Key` header directly against `users.email` — which is not a secret — so anyone who knew or guessed a registered user's email could authenticate as that user against the production API. Both services now require a Clerk session token (`Authorization: Bearer`); a present `X-API-Key` fails closed with a migration message. Runtime agent keys (`aid_sk_`) are unaffected — they authenticate at the gateway via the `/api/v1/keys/verify` path. Added a regression test asserting an email used as `X-API-Key` is rejected. (Insight #89)
- **`/api/v1/keys/verify` now uses a dedicated `X-Service-Token`** for service-to-service auth (constant-time compare against `VERIFY_SERVICE_TOKEN`), completing the Insight #89 migration on the consumer side — the CEO Dashboard's verify caller had been left on the removed email-as-key path and was failing closed. The general `X-API-Key` stays closed; this token is scoped to the verify endpoint only.

## [0.2.0] — 2026-04-14

### Added
- **Agent purge with retention policy** — Revoked agents are now hard-deleted after a configurable retention period (default: 30 days). Audit logs are preserved with denormalized agent names so history remains meaningful after deletion. Admin-only `POST /api/v1/admin/agents/purge` endpoint and dashboard "Purge All" button (visible when filtering to Revoked). `revoked_at` timestamp tracks when each agent was revoked.
- OpenAPI `servers` block (`https://api.ai-identity.co`) so ReDoc shows a concrete base URL.
- Tag descriptions for `capabilities`, `auth`, `audit.forensics`, `approvals`, and `shadow-agents` in the API docs.
- MIT license URL in the OpenAPI `license` block.

### Changed
- API docs `contact.url` now points to `https://ai-identity.co` (product site) instead of the repository.
- Stale "Render" references in `api/app/main.py` module and `/health` docstrings replaced with GKE / generic wording after the infrastructure migration.

## [0.1.0] — 2026-03-30

### Added
- Human-in-the-Loop approval for enterprise tier agents
- Shadow Agent Detection — customer-facing security analytics
- Automated tests for HITL approval and shadow agent detection
- Admin user detail page with agents, audit logs, and quota usage
- Request ID propagation and API versioning documentation
- Change window policy and customer notification requirements

### Changed
- Alembic migrations run automatically on API deploy
- Welcome email copy updated to warmer founder tone

### Fixed
- Approval requests migration uses IF NOT EXISTS for idempotent creation
- Performance indexes migration uses IF NOT EXISTS
- Alembic migration chain duplicate revision ID resolved

## [0.0.9] — 2026-03-24

### Added
- EU AI Act Checklist added to Solutions dropdown nav
- Solutions dropdown on landing page navigation
- Python and TypeScript SDKs with use-case blueprint pages

### Fixed
- CSP blocking Swagger UI on /docs
- Swagger docs enabled in production

## [0.0.8] — 2026-03-21

### Added
- Web Properties page and API docs link
- Redis-backed rate limiter with in-memory fallback

### Changed
- Sentry health check noise filtered, Stripe retries added, httpx connection pooling
- Gateway health check DB probe cached with 10s TTL
- uvloop + orjson added for 2-5x throughput gain

### Fixed
- P95 latency spikes — indexes, connection pooling, N+1 queries, Gunicorn tuning
- Rate limiter test accessing facade internals

## [0.0.7] — 2026-03-17

### Added
- Embedded Loom demo video and design partner callout
- Live demo link on landing page
- Why AI Identity comparison section with Okta positioning

### Changed
- Replaced remaining Framer components with custom sections
