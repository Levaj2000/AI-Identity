# ADR-001: Architecture Review & Recommendations

**Status:** Proposed
**Date:** 2026-03-25
**Deciders:** Jeff Leva (CEO/CTO)

## Context

After a thorough audit of the AI Identity codebase (Sprint 7), the application has grown significantly from the initial architecture. This ADR captures architectural observations and recommended improvements, prioritized by impact and effort.

## Current Architecture Strengths

The architecture is well-designed for a solo-founder stage:

1. **Clean service separation** — API (business logic) and Gateway (enforcement) are properly decoupled
2. **Fail-closed enforcement** — Gateway defaults to DENY on any error, which is the correct security posture
3. **HMAC audit chain** — Tamper-evident logging is a genuine differentiator
4. **Shared code pattern** — `common/` avoids duplication while keeping services independently deployable
5. **Tier-based quotas** — Clean quota model with per-tier limits baked into the User model
6. **Circuit breaker** — Prevents cascade failures in the gateway

## Recommendations

### Priority 1: High Impact, Low Effort

#### R1: Add Database Connection Pooling Configuration
**Severity:** High | **Effort:** Small

Currently using SQLAlchemy defaults. With Neon's connection pooler, you should explicitly configure pool sizes to avoid connection exhaustion under load.

```python
# common/models/base.py — add pool settings
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,  # recycle connections every 5 min
    pool_pre_ping=True,  # verify connections before use
)
```

#### R2: Add Request ID Propagation Between Services
**Severity:** Medium | **Effort:** Small

The API generates `X-Request-ID` but the Gateway doesn't propagate it. When investigating incidents, you need to correlate a Gateway enforcement decision with the originating API request.

**Fix:** Pass `X-Request-ID` from Gateway → API in the HMAC-signed internal call, and log it in audit entries.

#### R3: Add Health Check Depth
**Severity:** Medium | **Effort:** Small

Current `/health` endpoints return 200 without verifying dependencies. A "deep health" check should verify DB connectivity and return degraded status if Neon is unreachable.

```json
GET /health?deep=true
{
  "status": "healthy",
  "database": "connected",
  "latency_ms": 12,
  "version": "0.1.0"
}
```

### Priority 2: Medium Impact, Medium Effort

#### R4: Separate Alembic Migration Execution from Service Startup
**Severity:** Medium | **Effort:** Medium

Currently `alembic upgrade head` runs in the Render build command. If a migration fails, the deploy still proceeds. Migrations should be a separate Render job that blocks deploys on failure.

#### R5: Add Structured Logging
**Severity:** Medium | **Effort:** Medium

Current logging uses Python's default formatter. For production observability, switch to JSON-structured logs that can be parsed by log aggregation tools.

```python
{"timestamp": "2026-03-25T09:14:00Z", "level": "INFO", "service": "api",
 "request_id": "abc123", "method": "POST", "path": "/agents", "status": 200, "duration_ms": 45}
```

#### R6: Add API Versioning Strategy
**Severity:** Medium | **Effort:** Medium

All routes are under `/api/v1`. Good. But there's no mechanism for deprecating endpoints or running v1 and v2 simultaneously. Document the versioning strategy now so breaking changes don't surprise early customers.

### Priority 3: Future Considerations (Post-Revenue)

#### R7: Extract Audit Service
**Severity:** Low (now) | **Effort:** Large

The audit subsystem (HMAC chain, PII sanitizer, verification, export) is the most valuable IP. As the product scales, extracting it into its own service would:
- Allow independent scaling (audit writes are high-volume)
- Enable audit-as-a-service for other products
- Simplify SOC 2 audit scope (isolate the compliance-critical component)

**Not needed now** — the shared `common/audit` module is fine at current scale.

#### R8: Add Webhook System for Real-Time Alerts
**Severity:** Low (now) | **Effort:** Medium

Customers will eventually want real-time notifications when:
- An agent is denied (policy violation)
- Rapid-fire denials detected (anomaly)
- HMAC chain integrity broken
- Quota approaching limit

This would be a simple webhook table + async delivery queue.

#### R9: Consider Read Replicas for Forensics Queries
**Severity:** Low (now) | **Effort:** Medium

Forensics queries scan large audit log ranges. As data grows, these analytical queries could impact transactional performance. Neon supports read replicas — route forensics reads to a replica.

## Action Items

1. [ ] **R1:** Add DB pool configuration (Sprint 7 or 8)
2. [ ] **R2:** Propagate X-Request-ID through Gateway → API (Sprint 8)
3. [ ] **R3:** Add deep health checks (Sprint 8)
4. [ ] **R4:** Separate migration execution (Sprint 8)
5. [ ] **R5:** Structured JSON logging (Sprint 8-9)
6. [ ] **R6:** Document API versioning strategy (Sprint 8)
7. [ ] **R7-R9:** Backlog (post-revenue)

## Consequences

- **R1-R3** are quick wins that improve production resilience
- **R4-R6** improve operational maturity for when customers arrive
- **R7-R9** are architectural investments that only matter at scale

None of these are blockers for design partner onboarding. The current architecture is solid for the first 10-50 customers.
