# HITL Approval — Implementation Plan

## Overview

Human-in-the-Loop (HITL) approval adds a pause/resume gate to the gateway enforcement pipeline. When a policy's `require_approval` patterns match the incoming request, the gateway returns **202 Accepted** with a `review_id` instead of forwarding. An admin or owner then approves/rejects via the API (or dashboard). Unanswered requests auto-expire (fail-closed).

Enterprise tier only. Phase 1 = backend + gateway. Phase 2 = dashboard UI.

---

## 1. Complete File List

### New Files (create)

| File | Purpose |
|------|---------|
| `common/models/approval_request.py` | SQLAlchemy model for `approval_requests` table |
| `common/schemas/approval.py` | Pydantic request/response schemas |
| `api/app/routers/approvals.py` | REST endpoints: list, detail, approve, reject |
| `gateway/app/hitl.py` | HITL check logic + auto-expire helper |
| `alembic/versions/j0e1f2g3h4i5_add_approval_requests.py` | Migration |
| `gateway/tests/test_hitl.py` | Unit tests for HITL enforcement |
| `tests/test_approvals_api.py` | Integration tests for approval endpoints |
| `dashboard/src/services/api/approvals.ts` | Frontend API client |
| `dashboard/src/pages/ApprovalsPage.tsx` | Approval queue UI |

### Modified Files

| File | Change |
|------|--------|
| `common/models/__init__.py` | Export `ApprovalRequest`, `ApprovalStatus` |
| `common/validation/policy.py` | Add `require_approval` to `ALLOWED_RULE_KEYS`, validate it |
| `gateway/app/enforce.py` | Add `PENDING_APPROVAL` decision, insert HITL check after policy ALLOW |
| `gateway/app/main.py` | Handle 202 response for pending approvals |
| `api/app/main.py` | Register approvals router |
| `common/config/settings.py` | Add `hitl_default_timeout_seconds` setting |
| `dashboard/src/App.tsx` | Add `/dashboard/approvals` route |
| `dashboard/src/components/Sidebar.tsx` | Add "Approvals" nav item |

---

## 2. Database Schema: `approval_requests`

```sql
CREATE TABLE approval_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint        VARCHAR(512) NOT NULL,
    method          VARCHAR(10)  NOT NULL,
    request_metadata JSONB NOT NULL DEFAULT '{}',
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending',
    timeout_seconds INTEGER      NOT NULL DEFAULT 300,
    expires_at      TIMESTAMPTZ  NOT NULL,
    resolved_by     UUID         REFERENCES users(id) ON DELETE SET NULL,
    resolved_at     TIMESTAMPTZ,
    resolution_note TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT chk_status CHECK (status IN ('pending','approved','rejected','expired'))
);

CREATE INDEX ix_approval_user_status ON approval_requests(user_id, status);
CREATE INDEX ix_approval_agent_created ON approval_requests(agent_id, created_at DESC);
CREATE INDEX ix_approval_expires_pending ON approval_requests(expires_at)
    WHERE status = 'pending';
```

### SQLAlchemy Model (`common/models/approval_request.py`)

- UUID PK with `default=uuid.uuid4`
- `agent_id` FK to agents, `user_id` FK to users (both CASCADE on delete)
- `resolved_by` FK to users (SET NULL on delete)
- `status` as String(20) with StrEnum `ApprovalStatus` (pending/approved/rejected/expired)
- `request_metadata` as JSONB
- `expires_at` as DateTime(timezone=True), computed at creation as `now() + timedelta(seconds=timeout_seconds)`
- Composite indexes: `(user_id, status)`, `(agent_id, created_at DESC)`, partial index on `expires_at WHERE status='pending'`
- Relationships: `agent` (Agent), `owner` (User via user_id), `resolver` (User via resolved_by)

---

## 3. Policy Rules Extension: `require_approval`

The `rules` JSONB column gains a new optional key:

```json
{
    "allowed_endpoints": ["/v1/*"],
    "allowed_methods": ["POST"],
    "require_approval": ["/v1/chat/completions", "/v1/fine-tuning/*"]
}
```

**Semantics**: if the request WOULD BE ALLOWED by existing rules AND the endpoint matches any `require_approval` pattern, the gateway pauses and returns 202 instead of 200.

### Validation Changes (`common/validation/policy.py`)

1. Add `"require_approval"` to `ALLOWED_RULE_KEYS` frozenset.
2. Reuse the existing `_validate_endpoints()` method for `require_approval` -- same endpoint pattern format, same safety regex, same length/count limits.
3. Add `self._validate_endpoints(rules, "require_approval", result)` call in `validate()`.

No DB migration needed for this -- it is a new key within the existing JSONB `rules` column.

---

## 4. Gateway Enforcement Changes

### New Decision + DenyReason in `gateway/app/enforce.py`

```python
class Decision(enum.StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ERROR = "error"
    PENDING_APPROVAL = "pending_approval"  # NEW

class DenyReason(enum.StrEnum):
    # ... existing values ...
    PENDING_APPROVAL = "pending_approval"  # NEW
```

### EnforcementResult Extension

Add `review_id: uuid.UUID | None = None` field. Set when decision is PENDING_APPROVAL.

### Pipeline Insertion Point

The HITL check runs AFTER the policy ALLOW decision but BEFORE the quota increment. This is the exact location in enforce() (after line ~401, after `policy_circuit_breaker.record_success()` and the `if not policy_allows` deny block):

```
Current flow:
  0. Key-type enforcement
  1. Circuit breaker check
  2. Agent validation
  3. Policy evaluation (timeout-bounded)
  4. Record success on circuit breaker
  4a. If policy denied -> DENY
  5. ALLOW -> quota check -> return

New flow (insert 4b):
  0-4a: unchanged
  4b. HITL check (NEW):
      - Skip if user tier != enterprise
      - Load policy rules, check require_approval patterns against endpoint
      - If match: create ApprovalRequest row, return PENDING_APPROVAL (202)
  5. ALLOW -> quota check -> return (unchanged)
```

### New Module: `gateway/app/hitl.py`

Two public functions:

**`check_hitl_required(db, agent_id, user_id, user_tier, endpoint, method, request_metadata) -> ApprovalRequest | None`**
- Returns None (skip HITL) if: tier != enterprise, no active policy, no require_approval patterns, endpoint doesn't match
- Creates and returns ApprovalRequest row if HITL triggered
- Sets `expires_at = now + timedelta(seconds=settings.hitl_default_timeout_seconds)`

**`expire_stale_approvals(db) -> int`**
- Single UPDATE: set status='expired' WHERE status='pending' AND expires_at <= now()
- Returns count of expired rows
- Uses the partial index for efficiency

### enforce() Code Change

After the circuit breaker success recording and policy-denied check block, before the "ALLOW" section:

1. Look up user tier via `agent.user_id -> User.tier` (agent already loaded in step 2)
2. If tier == "enterprise", call `check_hitl_required()`
3. If it returns an ApprovalRequest, build EnforcementResult with decision=PENDING_APPROVAL, status_code=202, review_id=approval.id
4. Audit the HITL decision with review_id in metadata
5. Return the result (skipping quota check)

### Gateway main.py — Handle 202

In `enforce_request()` route handler, after the `enforce()` call and before the existing deny/allow branching, add a check:

```python
if result.decision.value == "pending_approval":
    return JSONResponse(
        status_code=202,
        content={
            "decision": "pending_approval",
            "status_code": 202,
            "message": result.message,
            "review_id": str(result.review_id),
            "deny_reason": "pending_approval",
        },
    )
```

---

## 5. API Endpoints (Approvals Router)

### `api/app/routers/approvals.py`

Prefix: `/api/v1/approvals`, tags: `["approvals"]`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/approvals` | get_current_user | List approvals (paginated, filterable by status/agent_id) |
| GET | `/api/v1/approvals/pending/count` | get_current_user | Pending count for sidebar badge |
| GET | `/api/v1/approvals/{review_id}` | get_current_user | Single approval detail |
| POST | `/api/v1/approvals/{review_id}/approve` | get_current_user | Approve pending request |
| POST | `/api/v1/approvals/{review_id}/reject` | get_current_user | Reject pending request |

Key behaviors:
- All queries filter by `ApprovalRequest.user_id == user.id` (ownership scoping)
- List and detail endpoints call `expire_stale_approvals(db)` first (lazy expiration)
- Approve/reject check: status must be "pending", else 409
- Approve/reject on expired: return 410 Gone
- Both approve and reject create audit entries via `create_audit_entry()`
- The list endpoint joins to Agent for agent_name
- Approve sets `resolved_by=user.id`, `resolved_at=now`, status="approved"
- Reject sets `resolved_by=user.id`, `resolved_at=now`, status="rejected"

### Router Registration in `api/app/main.py`

Add import and `app.include_router(approvals_router)` following the existing pattern.

---

## 6. Pydantic Schemas (`common/schemas/approval.py`)

- `ApprovalStatusEnum(StrEnum)`: pending, approved, rejected, expired
- `ApprovalSummary(BaseModel)`: id, agent_id, agent_name, endpoint, method, status, created_at, expires_at, resolved_at. `model_config = {"from_attributes": True}`
- `ApprovalDetailResponse(BaseModel)`: extends summary with user_id, request_metadata, timeout_seconds, resolved_by, resolution_note, updated_at
- `ApprovalListResponse(BaseModel)`: items (list[ApprovalSummary]), total, limit, offset
- `ApprovalResolveRequest(BaseModel)`: note (str | None, max_length=1000)
- `ApprovalPendingCount(BaseModel)`: count (int)

---

## 7. Settings Extension (`common/config/settings.py`)

One new field in the Settings class:

```python
hitl_default_timeout_seconds: int = 300  # 5 minutes, fail-closed
```

---

## 8. Migration File

File: `alembic/versions/j0e1f2g3h4i5_add_approval_requests.py`

- `revision = "j0e1f2g3h4i5"`
- `down_revision`: Must be determined by running `alembic heads`. Current latest files both start with `i9d0e1f2g3h4` -- if they are two heads, create a merge migration first. If one depends on the other, use the final one.
- `upgrade()`: create_table + 3 create_index calls
- `downgrade()`: drop indexes + drop table

---

## 9. Gateway 202 Response Contract

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
    "decision": "pending_approval",
    "status_code": 202,
    "message": "Request requires human approval",
    "review_id": "a1b2c3d4-e5f6-...",
    "deny_reason": "pending_approval"
}
```

Caller workflow (poll and re-submit):
1. Receive 202 with review_id
2. Poll `GET /api/v1/approvals/{review_id}` for status changes
3. Once status is "approved", re-submit the original request to the gateway
4. Gateway evaluates fresh -- policy still allows it, HITL check sees no new approval needed (the endpoint still matches require_approval patterns, but we need a mechanism to avoid infinite loop)

**Important design detail -- avoiding re-trigger loop**: When the caller re-submits after approval, the HITL check would trigger again. Solution: the gateway's HITL check should look for a recent approved ApprovalRequest for the same agent_id + endpoint + method within the last N minutes. If one exists, skip HITL. Alternatively, the caller passes `review_id` as a query parameter, and the gateway validates it was approved before skipping HITL.

Recommended approach for Phase 1: **Accept `review_id` query parameter**. If provided, the gateway looks it up, confirms status=approved, confirms it matches the current agent_id/endpoint/method, and skips HITL. This is explicit and auditable.

Changes needed:
- `gateway/app/main.py enforce_request()`: accept optional `review_id` query param
- `gateway/app/enforce.py enforce()`: accept optional `review_id`, pass to HITL check
- `gateway/app/hitl.py check_hitl_required()`: if review_id provided and matches an approved ApprovalRequest for this agent/endpoint/method, return None (skip HITL)

---

## 10. Auto-Expire Mechanism

Three layers (defense in depth):

**Layer 1 -- Lazy on read**: Every list/detail API call runs `expire_stale_approvals(db)` first. Single UPDATE with partial index, very fast.

**Layer 2 -- Lazy on HITL check**: Each `check_hitl_required()` call optionally runs expire. Keeps table clean during active usage.

**Layer 3 -- Background task (Phase 3)**: Periodic cron running every 60s. Not needed for Phase 1 since layers 1+2 cover all active usage paths.

The partial index `ix_approval_expires_pending` on `(expires_at) WHERE status='pending'` ensures the expire query scans only pending rows.

---

## 11. Frontend (Phase 2)

### API Client (`dashboard/src/services/api/approvals.ts`)

Follows `apiFetch` + `toQueryString` pattern from `services/api/client.ts`:
- `getApprovals(params)` -> GET /api/v1/approvals
- `getApprovalDetail(id)` -> GET /api/v1/approvals/{id}
- `approveRequest(id, note?)` -> POST /api/v1/approvals/{id}/approve
- `rejectRequest(id, note?)` -> POST /api/v1/approvals/{id}/reject
- `getPendingCount()` -> GET /api/v1/approvals/pending/count

TypeScript interfaces mirror the Pydantic schemas.

### Approvals Page (`dashboard/src/pages/ApprovalsPage.tsx`)

Structure:
- Tab bar: Pending | Approved | Rejected | Expired (default: Pending)
- Table with columns: Agent, Endpoint, Method, Requested, Expires In (countdown), Status badge
- Row click opens detail drawer (following EventDetailDrawer pattern from ForensicsPage)
- Drawer shows: full request metadata (JSON), Approve/Reject buttons (for pending), resolution info (for resolved)
- Polling: `useEffect` + `setInterval` every 10s on Pending tab
- Empty state: shield icon + "No pending approvals"

Color conventions (matching existing badge patterns in ForensicsPage):
- Pending: `bg-yellow-500/10 text-yellow-400 border-yellow-500/20`
- Approved: `bg-emerald-500/10 text-emerald-400 border-emerald-500/20`
- Rejected: `bg-red-500/10 text-red-400 border-red-500/20`
- Expired: `bg-gray-500/10 text-gray-400 border-gray-500/20`

### Sidebar (`dashboard/src/components/Sidebar.tsx`)

Add "Approvals" entry to `navItems` array (before the admin separator, after "Web Properties"). Use a clock or checkmark-circle icon. Optionally show a pending count badge.

### Route (`dashboard/src/App.tsx`)

Add `<Route path="approvals" element={<ApprovalsPage />} />` inside the dashboard routes block.

---

## 12. Testing Approach

### Unit Tests: `gateway/tests/test_hitl.py`

1. Non-enterprise tier -> check_hitl_required returns None
2. No require_approval patterns -> returns None
3. Endpoint matches pattern -> returns ApprovalRequest with correct fields
4. Endpoint does not match -> returns None
5. Wildcard require_approval ["*"] -> triggers for any endpoint
6. Prefix pattern ["/v1/fine-tuning/*"] -> correct matching
7. expires_at computed correctly from timeout_seconds
8. expire_stale_approvals: expired row gets status=expired, non-expired stays pending
9. review_id passthrough: approved review_id for matching agent/endpoint -> returns None (skip)
10. review_id mismatch: wrong agent_id -> still triggers HITL

### Integration Tests: enforce() pipeline

11. Enterprise agent + matching require_approval -> enforce() returns PENDING_APPROVAL, 202, review_id set
12. Same agent, pro tier -> enforce() returns ALLOW (200)
13. Audit entry created with decision="pending_approval" and review_id in metadata
14. With approved review_id -> enforce() returns ALLOW (200)

### API Tests: `tests/test_approvals_api.py`

15. GET /approvals -> returns user's approvals only
16. GET /approvals?status=pending -> filtered correctly
17. GET /approvals/{id} -> returns detail
18. POST /approvals/{id}/approve -> status becomes approved
19. POST /approvals/{id}/reject -> status becomes rejected
20. POST approve on expired -> 410
21. POST approve on already approved -> 409
22. GET /approvals/pending/count -> correct number
23. Other user's approvals -> 404

### Test Fixtures

- `enterprise_user`: User with tier="enterprise"
- `hitl_policy`: Policy with require_approval patterns
- `pending_approval`: ApprovalRequest in pending state
- `expired_approval`: ApprovalRequest past expires_at

---

## 13. Implementation Sequencing

### Phase 1 (Backend -- 3-4 days)

**Day 1**: Model + Migration + Settings
- common/models/approval_request.py
- common/models/__init__.py update
- common/config/settings.py update
- Migration file
- common/schemas/approval.py

**Day 2**: Policy validation + HITL check
- common/validation/policy.py (add require_approval)
- gateway/app/hitl.py
- gateway/app/enforce.py changes
- gateway/app/main.py 202 handling
- gateway/tests/test_hitl.py

**Day 3**: API endpoints + integration tests
- api/app/routers/approvals.py
- api/app/main.py router registration
- tests/test_approvals_api.py
- End-to-end manual test

### Phase 2 (Dashboard -- 2 days)

**Day 4**: Frontend API + Page
- dashboard/src/services/api/approvals.ts
- dashboard/src/pages/ApprovalsPage.tsx

**Day 5**: Navigation + Polish
- dashboard/src/components/Sidebar.tsx
- dashboard/src/App.tsx
- Polling, empty states, loading states
- Manual testing

---

## 14. Security Considerations

1. **Fail-closed**: expired approvals are DENIED. The gateway never allows a request unless the approval is explicitly "approved".
2. **No request body storage**: only endpoint, method, and sanitized metadata stored. Avoids PII in the approval table.
3. **Ownership scoping**: all API queries filter by user_id. Users cannot see or resolve other users' approvals.
4. **Race condition on resolve**: second concurrent approve gets 409 because first UPDATE changes status from pending.
5. **Audit trail**: both the HITL trigger (gateway) and the resolution (API) create HMAC-chained audit entries.
6. **Enterprise-only gate**: tier check happens before any ApprovalRequest creation, preventing free/pro users from accumulating rows.

---

## 15. Deferred to Phase 3

- Notification channels (email, Slack, webhook on approval creation)
- Role-based routing (route approvals to specific team members)
- Per-agent timeout override (currently global setting only)
- Approval delegation (delegate to another user)
- Batch approve/reject
- WebSocket push for real-time updates (currently polling)
- Background cron for expire (currently lazy-on-read)
