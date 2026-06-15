# Changelog

All notable changes to AI Identity are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Fixed
- Case File bundle now actually contains the verifier script. `cli/` was excluded from the Docker image (`.dockerignore`), so the bundle builder silently skipped `ai_identity_verify.py` and every downloaded bundle shipped without the tool needed to verify it. The verifier is now copied into the image, and the bundle endpoint fails loudly (500) rather than ever shipping a verifier-less bundle again. (#326)
- Case File report signature is now signed with the organization's forensic key (the one in the bundle / dashboard), not AI Identity's internal server key — so a customer's offline `ai_identity_verify.py report` shows **VALID** instead of always **INVALID**, matching the Reliability Statement's "verifiable by a key-holder" promise. Bundle README rewritten for a clean, repeatable verify. (Affects new exports.) (#325)
- Dogfood agent-identity verification works in prod again: `/api/v1/keys/verify` authenticates trusted backends (the CEO Dashboard) via a dedicated `X-Service-Token`, now mounted into the API pod from Secret Manager — completing the #298/#299 migration. (#321, #323)

### Added
- **Case File export scope** — `GET /api/v1/audit/report` (and `/report/bundle`) now export beyond a single agent + date window: by **incident** (`correlation_id` — every event sharing the id) or **org-wide** (omit `agent_id`). All four formats (JSON/CSV/OCSF/ZIP) inherit the scope, each Case File states its `scope` on its face, and org-wide / incident exports require an org owner/admin (cross-tenant is platform-admin-only). Agent-scoped exports are unchanged. (#403)
- **OCSF export** — the Case File can now export its audit events as **OCSF API Activity** (`class_uid 6003`) with the **`ai_operation` profile** and an **`attestation`** integrity object (hash-chain `entry_hash`/`prev_entry_hash`/`chain_uid`), grounded in AI Identity's OCSF contributions (PR #1641 `ai_agent` placement, #1661 provenance). New `common/ocsf` mapper + `format=ocsf` on `GET /api/v1/audit/report` (returns **NDJSON** — one OCSF event per line — the de-facto SIEM ingestion format, e.g. Splunk HEC) + an "OCSF" export button on the Case File page. The dashboard's OCSF claim is now backed by a real export (chip: "OCSF export").
- Dashboard **Attestation page** (flagship surface, under Assurance): surfaces the public **JWKS trust anchor** (`/.well-known/ai-identity-public-keys.json`), looks up and displays a **DSSE-signed session attestation** by session id (`/api/v1/sessions/{id}/attestation`) — window, event count, audit range, signer key, and the raw DSSE envelope — and explains offline verification. Enterprise-clinical, token-driven; grounded in real endpoints (no fabricated list, since attestations are retrieved per session).
- R&D strategy deliverables under `docs/strategy/`: an Agent Accountability **landscape & next-bet** report, a frontier **"Horizon 2030"** report (3–5yr; "evidence is the durable asset" thesis), and two gated design proposals — **Evidence Anchor** (transparency-log + offline verifier) and **Case File** (court-ready evidence export). Reports ship with reproducible PDF generators.
- Forensics report (**Case File**): exports now carry a plain-English **Reliability Statement** (FRE 702 / Daubert + ISO/IEC 27037 framing) describing how integrity is established, what the signature attests, the timestamp source, and the honest limits of key-holder verification. Surfaced on `/api/v1/audit/report` (JSON) and the verification bundle.
- **Case File** branding for the forensics evidence export: the verification bundle, downloaded report JSON, and CSV are now `case-file-*` (was `forensics-*`), the bundle README documents the Reliability Statement, and the API doc summaries say "Case File." Endpoint paths unchanged (non-breaking).
- Monthly **infra cost report** (`scripts/infra-cost-report/`) summarizing Neon, Atlas, GKE, and Sentry spend.
- Dashboard **design-token layer** (`dashboard/src/index.css`): semantic colors — surfaces, text, lines, brand, status — defined once per mode and exposed as Tailwind v4 utilities (`bg-surface`, `text-ink`, `border-line`, `bg-brand`…), replacing per-element `dark:` overrides. Light mode is now an intentional palette (brand uses an AA-compliant `#1d6fe0` on light, `#A6DAFF` on dark), and the app shell (layout, sidebar, theme toggle) is migrated to tokens. Phase 1 of the dashboard polish work; pages migrate in a follow-up.
- Dashboard **Overview page migrated to the design tokens** (Phase 2): stat cards, recent activity, request-volume chart, agent-health grid, quick-start, getting-started, and the system-status banner all theme through tokens — no per-element `dark:` overrides — so light mode is fully intentional on that screen. Card styling unified to flat token surfaces (the dark-mode glassmorphism/glow on stat cards was dropped for consistency).
- **Onboarding Acceptance** (dashboard QA page): the 15-step E2E checklist is now a two-party acceptance record — the customer and AI Identity each sign off — with a downloadable signed PDF bound to the run id and both signatures. (Reframed from "Simulate client onboarding.")

### Changed
- OCSF export: gateway latency is now emitted as the OCSF base `duration` field (milliseconds) instead of `unmapped.latency_ms`, per the CMF↔OCSF crossmap — reads natively to an OCSF consumer.
- Case File **exports grouped into a single "Export ▾" menu** (JSON report · CSV · OCSF · verification bundle) in the toolbar — more discoverable than the separate buttons, and surfaces the signed verification bundle (.zip + offline-verify CLI) on the page for the first time.
- Dashboard **Phase D.2 — remaining workspace migrated to design tokens**: Compliance (+ exports), Usage & billing, Shadow agents, Approvals, Web properties, Support (+ ticket detail, create-ticket modal), Admin (+ user detail, stat drawer), the Onboarding Acceptance (QA) page, the agent/key status badges, health indicator, login, and not-found. Enterprise/Pro tiers now use the `ai` accent. **The dashboard workspace is now fully token-driven** (only the deliberately-dark Demo terminal and the brand logo SVG remain non-token). Adds `success-ink`/`danger-ink`/`warning-ink` tokens and retrofits solid status buttons so their text passes AA contrast in dark mode.
- Dashboard **Phase D.1 — Agents & Keys cluster** migrated to the design tokens: Organization, Agent detail, Agents, Create agent, Agent keys, Keys pages + the agents/keys tables, cards, filters, forms, pagination, and key/agent modals. Status badges → success/warning/danger tokens; inputs/selects → tokenized; dark-mode card glassmorphism flattened. (Tier badges temporarily use `brand` pending the `ai` accent token.)
- Dashboard **Demo page** migrated to clinical tokens while keeping the bash/terminal playground deliberately dark (via the constant-navy rail tokens) — a terminal reads as a terminal in both themes.
- Dashboard **AI-feature (purple) and perf-anomaly (orange) accents tokenized** (`--ai`, `--anomaly`) with AA-accessible light + dark values, fixing low-contrast forensics accents on the light workspace.
- Dashboard **Case File workspace** (Phase C): the forensics surface is migrated off dark-only `zinc` to the design tokens (works in light + dark) and reframed as **Case File** — a court-ready evidence identity with a standards ribbon (FRE 702 / Daubert · ISO/IEC 27037 · OCSF · HMAC-SHA256), atop the existing real generate-report / chain-verify / download-bundle / verify-offline flow. Migrates `ForensicsPage` + 7 forensics components. (Distinct AI-feature purple and perf-anomaly orange accents are kept pending dedicated tokens.)
- Dashboard **shell redesigned to enterprise-clinical** (Phase A of the dashboard redesign): a constant **navy nav rail** (brand anchor in both themes) with **grouped IA** — Identity / Control / Assurance / Detect / Account — beside a **light clinical workspace** and a breadcrumb top bar. Adds `rail-*` design tokens and a shared `src/config/nav.tsx`; renames "Forensics" → "Case File" in nav. Only existing routes are linked (no dead links). Flagship surfaces (Attestation, OCSF interop) and per-page content reposition follow in later phases.
- Dashboard **Overview Phase B**: adds an **Evidence & integrity** panel wired to the real tamper-evident audit-chain verification (`/api/v1/audit/verify`) and an informational **Standards & frameworks** panel (OCSF / SOC 2 / EU AI Act / NIST AI RMF, linking to Compliance) — surfacing the trust/forensics positioning on the home screen. No fabricated metrics (attestation/Case-File counts deferred until backed by real endpoints).
- Dashboard **Overview redesigned to an action-first layout** (Phase 3): leads with a "Needs your attention" panel — pending approvals, detected shadow agents, and QA awaiting sign-off, wired to real counts (`/approvals/pending/count`, `/shadow-agents/stats`, `/qa/has-pending`) with a graceful "all caught up" state — then demotes the agent counts to a compact metric strip. Built on the design tokens. (Replaces the four stat cards / `StatsGrid`.)
- `infra-cost-report`: Treat a deliberate paid Sentry plan as a decision rather than a nag — suppresses the downgrade recommendation when the paid tier is intentional (configurable via `scripts/infra-cost-report/.env.example`).

### Fixed
- OCSF export: the `decision` → `action_id` mapping now handles long-form values (`allowed`/`denied`) and is whitespace/case-tolerant, so rows no longer fall through to `action_id: 0` ("Unknown"); `severity_id` is no longer falsely elevated for unclassified decisions.
- QA checklist runner authenticated its self-calls with the removed `X-API-Key`=email credential (broken by Insight #89), so every authenticated step failed (the "3/5" runs). It now replays the caller's Clerk session token, and onboarding runs under the caller's real account instead of a synthetic test user.

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
