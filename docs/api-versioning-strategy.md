# API Versioning Strategy

**Document Owner:** Jeff Leva, CEO
**Version:** 1.0
**Last Reviewed:** March 30, 2026

---

## Current State

All API endpoints are under `/api/v1/`. The gateway enforce endpoint is at `/gateway/enforce`. There is currently one version in production.

## Versioning Scheme

**URL-based versioning**: `/api/v1/`, `/api/v2/`, etc.

URL-based versioning is explicit, easy to route, and the industry standard for developer-facing APIs. It avoids the ambiguity of header-based versioning and is visible in logs, docs, and curl commands.

## When to Create v2

A new API version is required when making **breaking changes**:

- Removing or renaming a field from a response body
- Changing a field's type (e.g., string to integer)
- Removing an endpoint
- Changing required request parameters
- Altering authentication flow

**Non-breaking changes** do NOT require a new version:

- Adding new fields to response bodies
- Adding new optional query parameters
- Adding new endpoints
- Adding new enum values
- Performance improvements

## Deprecation Process

When introducing a breaking change:

1. **Build v2 alongside v1** — both versions run simultaneously in the same service
2. **Announce deprecation** — email customers + dashboard banner + API response header, 30 days before removal
3. **Add deprecation header** — all v1 responses include `Deprecation: true` and `Sunset: <date>` headers
4. **Monitor v1 usage** — track which customers are still hitting v1 endpoints via audit logs
5. **Remove v1** — only after all active customers have migrated, minimum 90 days after announcement

## Implementation Pattern

```python
# Both versions coexist in the same FastAPI app
from api.app.routers.agents_v1 import router as agents_v1_router
from api.app.routers.agents_v2 import router as agents_v2_router

app.include_router(agents_v1_router)  # /api/v1/agents
app.include_router(agents_v2_router)  # /api/v2/agents
```

Shared business logic lives in `common/` — routers are thin wrappers that handle request/response shape translation.

## SDK Versioning

Python and TypeScript SDKs follow semantic versioning (semver):

- **Patch** (1.0.x): Bug fixes, no API changes
- **Minor** (1.x.0): New features, backward compatible
- **Major** (x.0.0): Breaking changes, aligned with API version bumps

SDK major versions map to API versions: SDK v1.x → API v1, SDK v2.x → API v2.

## Gateway Versioning

The gateway enforce endpoint (`/gateway/enforce`) is an internal contract between AI Identity services. It follows the same versioning principles but with a shorter deprecation window (14 days) since the only consumer is the AI Identity proxy layer, not external customers.

## Customer Communication

| Timeline | Action |
|----------|--------|
| Day 0 | v2 released. v1 still works. Email + dashboard banner announcing deprecation. |
| Day 0-30 | `Deprecation: true` header on all v1 responses. Docs show v2 as default. |
| Day 30-90 | Active outreach to remaining v1 users. Migration guide published. |
| Day 90+ | v1 removed (only if zero active v1 traffic). |

---

*This document satisfies SOC 2 CC8.1 requirements for change management of customer-facing interfaces.*
