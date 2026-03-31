# Changelog

All notable changes to AI Identity are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- **Agent purge with retention policy** — Revoked agents are now hard-deleted after a configurable retention period (default: 30 days). Audit logs are preserved with denormalized agent names so history remains meaningful after deletion. Admin-only `POST /api/v1/admin/agents/purge` endpoint and dashboard "Purge All" button (visible when filtering to Revoked). `revoked_at` timestamp tracks when each agent was revoked.

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
