# Manual QA Checklist — Design Partner Onboarding

**Run weekly** during the design partner phase against production.

## Environment

| Service | URL | Expected |
|---------|-----|----------|
| API | `https://ai-identity-api.onrender.com` | `{"status": "ok"}` |
| Gateway | `https://ai-identity-gateway.onrender.com` | `{"status": "ok"}` |
| Dashboard | `https://dashboard.ai-identity.co` | Login page loads |
| Landing | `https://ai-identity.co` | Landing page loads |

```bash
# Set these before running
API=https://ai-identity-api.onrender.com
GW=https://ai-identity-gateway.onrender.com
KEY="your-api-key-here"
```

---

## Checklist (15 Steps)

### Phase 1: Health & Docs

| # | Step | Command | Pass Criteria | Status |
|---|------|---------|---------------|--------|
| 1 | **API Health** | `curl $API/health` | Returns `{"status": "ok"}` | |
| 2 | **Swagger UI** | `curl -o /dev/null -w "%{http_code}" $API/docs` | HTTP 200 | |

### Phase 2: Agent Lifecycle

| # | Step | Command | Pass Criteria | Status |
|---|------|---------|---------------|--------|
| 3 | **Create Agent** | `curl -X POST $API/api/v1/agents -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"name":"QA Bot","description":"QA test","capabilities":["chat_completion"]}'` | 201, returns `agent.id` + `api_key` | |
| 4 | **Get Agent** | `curl $API/api/v1/agents/$AGENT_ID -H "X-API-Key: $KEY"` | Returns agent with correct name, status=active | |
| 5 | **List Agents** | `curl "$API/api/v1/agents?status=active" -H "X-API-Key: $KEY"` | Returns `items[]` with agent in list, `total` ≥ 1 | |
| 6 | **Update Agent** | `curl -X PUT $API/api/v1/agents/$AGENT_ID -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"capabilities":["chat_completion","embeddings"]}'` | Returns agent with updated capabilities | |

### Phase 3: Key Management

| # | Step | Command | Pass Criteria | Status |
|---|------|---------|---------------|--------|
| 7 | **Create Key** | `curl -X POST $API/api/v1/agents/$AGENT_ID/keys -H "X-API-Key: $KEY"` | Returns `key.id` + `api_key` (plaintext, shown once) | |
| 8 | **List Keys** | `curl $API/api/v1/agents/$AGENT_ID/keys -H "X-API-Key: $KEY"` | Returns `items[]` with 2 keys, both `status: active` | |
| 9 | **Rotate Key** | `curl -X POST $API/api/v1/agents/$AGENT_ID/keys/rotate -H "X-API-Key: $KEY"` | Returns `new_key` (active) + `rotated_key` (status=rotated, expires_at set to +24h) | |
| 10 | **Verify Rotation** | `curl $API/api/v1/agents/$AGENT_ID/keys -H "X-API-Key: $KEY"` | 3 keys: 2 active, 1 rotated with `expires_at` | |
| 11 | **Revoke Key** | `curl -X DELETE $API/api/v1/agents/$AGENT_ID/keys/$KEY_ID -H "X-API-Key: $KEY"` | Returns key with `status: revoked` | |

### Phase 4: Credential Vault

| # | Step | Command | Pass Criteria | Status |
|---|------|---------|---------------|--------|
| 12 | **Store Credential** | `curl -X POST $API/api/v1/agents/$AGENT_ID/credentials -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"provider":"openai","label":"test","api_key":"sk-proj-fake-key-1234567890"}'` | Returns `credential` with `key_prefix: "sk-proj-"`, plaintext NOT in response | |

### Phase 5: Gateway Enforcement

| # | Step | Command | Pass Criteria | Status |
|---|------|---------|---------------|--------|
| 13 | **Gateway Enforce** | `curl -X POST "$GW/gateway/enforce?agent_id=$AGENT_ID&endpoint=/v1/chat&method=POST&key_type=runtime"` | `{"decision": "allow"}` | |

### Phase 6: Audit & Cleanup

| # | Step | Command | Pass Criteria | Status |
|---|------|---------|---------------|--------|
| 14 | **Audit Log** | `curl "$API/api/v1/audit?agent_id=$AGENT_ID&limit=10" -H "X-API-Key: $KEY"` | Returns `items[]` with entries for gateway decisions | |
| 15 | **Verify Chain** | `curl "$API/api/v1/audit/verify?agent_id=$AGENT_ID" -H "X-API-Key: $KEY"` | `{"valid": true}`, `entries_verified` > 0 | |

### Cleanup

```bash
# Revoke the QA agent (also revokes all keys)
curl -X DELETE $API/api/v1/agents/$AGENT_ID -H "X-API-Key: $KEY"
```

---

## Run Log

### Run 1 — 2026-03-17 (Production)

| # | Step | Result | Notes |
|---|------|--------|-------|
| 1 | API Health | **PASS** | `{"status":"ok","version":"0.1.0"}` |
| 2 | Swagger UI | **PASS** | HTTP 200 |
| 3 | Create Agent | **PASS** | Agent created, key returned |
| 4 | Get Agent | **PASS** | Correct name, status, capabilities |
| 5 | List Agents | **PASS** | `items[]` format, total=7 |
| 6 | Update Agent | **PASS** | Capabilities updated, metadata merged |
| 7 | Create Key | **PASS** | New key returned with plaintext |
| 8 | List Keys | **PASS** | 2 keys, both active |
| 9 | Rotate Key | **PASS** | New key active, old key rotated with 24h expiry |
| 10 | Verify Rotation | **PASS** | 3 keys: 2 active, 1 rotated |
| 11 | Revoke Key | **PASS** | Key status changed to revoked |
| 12 | Store Credential | **PASS** | Encrypted, only `key_prefix` visible |
| 13 | Gateway Enforce | **FAIL** | Gateway service suspended on Render (503) |
| 14 | Audit Log | **FAIL** | Returns empty — no entries logged (gateway down) |
| 15 | Verify Chain | **PASS** *(trivial)* | Valid but 0 entries (no gateway traffic to log) |

### Summary: 12/15 PASS, 2 FAIL, 1 trivial pass

### Bugs Filed

1. **[BUG] Gateway service suspended on Render** — `ai-identity-gateway.onrender.com` returns 503 "Service Suspended". Blocks steps 13-14. Need to re-activate the Render service.
2. **[BUG] Audit log empty despite API activity** — Audit entries are only created by gateway enforce calls. API CRUD operations (create agent, rotate key, etc.) do not create audit entries. Consider: should management operations also be audited?
