# Admin User Detail Page — Implementation Plan

## Overview
Add a clickable user detail page accessible from the Admin dashboard. Clicking a user's email in the user management table (or the stat drawer) navigates to `/dashboard/admin/users/:id`, showing a full profile with their agents, recent audit logs, tier/quota info, and account metadata.

## Changes Required

### 1. Backend — New API Endpoint
**File: `api/app/routers/admin.py`**
- Add `GET /api/v1/admin/users/{user_id}` endpoint
- Returns a rich `AdminUserDetail` response including:
  - User profile fields (email, role, tier, created_at, updated_at, stripe IDs, email tracking dates)
  - Tier quota info (max agents, max requests, etc.)
  - List of their agents (id, name, status, key_count, created_at)
  - Recent audit logs (last 50, with endpoint, method, decision, latency, created_at)
  - Usage summary (requests_this_month, agent count)

### 2. Backend — New Schema
**File: `common/schemas/admin.py`**
- Add `AdminUserDetail` Pydantic model with all profile fields
- Add `AdminUserAgent` model (agent summary scoped to user)
- Add `AdminUserAuditEntry` model (audit log entry for display)

### 3. Frontend — API Client
**File: `dashboard/src/services/api/admin.ts`**
- Add `getAdminUserDetail(userId: string): Promise<AdminUserDetail>` function
- Add corresponding TypeScript interfaces

### 4. Frontend — New Page Component
**File: `dashboard/src/pages/AdminUserDetailPage.tsx`** (new)
- Sections:
  - **Header**: Back link to admin, email, user ID, tier badge, role badge
  - **Account Info Card**: Created at, updated at, Stripe customer ID, subscription status, welcome/followup email dates
  - **Quota Usage Card**: Current usage vs tier limits (agents used/max, requests used/max) with progress bars
  - **Agents Table**: List of user's agents with name, status, key count, created date — each clickable to agent detail
  - **Recent Activity Table**: Last 50 audit log entries with timestamp, endpoint, method, decision, latency
- Loading/error/not-found states matching existing patterns

### 5. Frontend — Route Registration
**File: `dashboard/src/App.tsx`**
- Add `<Route path="admin/users/:id" element={<AdminUserDetailPage />} />`

### 6. Frontend — Make Emails Clickable
**File: `dashboard/src/pages/AdminPage.tsx`**
- Wrap user email in the table with `<Link to={`/dashboard/admin/users/${user.id}`}>`
- Add hover styling (underline, color change)

**File: `dashboard/src/components/admin/StatDetailDrawer.tsx`**
- Make user emails in the "All Users" drawer panel clickable with the same link pattern

## Design Notes
- Follows existing dark theme (`bg-[#10131C]`, `border-[#1a1a1d]`, `text-[#A6DAFF]`)
- Reuses `TierBadge` component from AdminPage (will extract if needed, or duplicate the small helper)
- Matches card/table styling from AdminPage and AgentDetailPage
- Back navigation via `← Back to Admin` link at top
- No new npm dependencies needed

## Files Modified (6) + Files Created (1)
1. `api/app/routers/admin.py` — new endpoint
2. `common/schemas/admin.py` — new schemas
3. `dashboard/src/services/api/admin.ts` — new API function + types
4. `dashboard/src/pages/AdminUserDetailPage.tsx` — **NEW** page component
5. `dashboard/src/App.tsx` — add route
6. `dashboard/src/pages/AdminPage.tsx` — make emails clickable links
7. `dashboard/src/components/admin/StatDetailDrawer.tsx` — make drawer emails clickable
