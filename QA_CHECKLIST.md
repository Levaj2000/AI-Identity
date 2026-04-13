# Manual QA Checklist — Design Partner Onboarding

Run this 15-step end-to-end checklist against **production** before onboarding
a new design partner. Every step must pass. If any step fails, fix the issue
and re-run from the failed step.

**Production URLs:**
- API: `https://api.ai-identity.co`
- Gateway: `https://gateway.ai-identity.co`
- Dashboard: `https://dashboard.ai-identity.co`

```bash
API=https://api.ai-identity.co
GATEWAY=https://gateway.ai-identity.co
```

---

## Health & Infrastructure

### 1. API health check

```bash
curl -s $API/health | python3 -m json.tool
```

- [ ] Returns `{"status": "ok", "service": "ai-identity-api", ...}`
- [ ] Response time < 500ms

### 2. Gateway health check

```bash
curl -s $GATEWAY/health | python3 -m json.tool
```

- [ ] Returns `{"status": "ok", "database": "connected", "circuit_breaker": "closed", ...}`
- [ ] Database is `"connected"`
- [ ] Circuit breaker is `"closed"`

### 3. Dashboard loads

Open `https://dashboard.ai-identity.co` in a browser.

- [ ] Login page renders without errors
- [ ] No console errors in browser DevTools

---

## Authentication & Agent Lifecycle

### 4. Login / auth flow

```bash
curl -s -X POST $API/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "<partner-email>"}' | python3 -m json.tool
```

- [ ] Returns 200 with user object and API key
- [ ] API key starts with expected prefix

Save the key:
```bash
KEY=<paste key here>
```

### 5. Create an agent

```bash
curl -s -X POST $API/api/v1/agents \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "QA Test Agent",
    "description": "E2E QA checklist agent",
    "capabilities": ["chat_completion", "function_calling"],
    "metadata": {"environment": "qa", "checklist_run": "true"}
  }' | python3 -m json.tool
```

- [ ] Returns 201 with agent object
- [ ] `agent.status` is `"active"`
- [ ] `api_key` starts with `aid_sk_`
- [ ] `agent.id` is a valid UUID

Save the values:
```bash
AGENT_ID=<paste agent id>
AGENT_KEY=<paste api_key — store securely>
```

### 6. List agents

```bash
curl -s "$API/api/v1/agents?limit=10" \
  -H "X-API-Key: $KEY" | python3 -m json.tool
```

- [ ] Returns 200 with `items` array
- [ ] QA Test Agent appears in the list
- [ ] `total` count is accurate
- [ ] Other users' agents are **not** visible (tenant isolation)

### 7. Get agent by ID

```bash
curl -s $API/api/v1/agents/$AGENT_ID \
  -H "X-API-Key: $KEY" | python3 -m json.tool
```

- [ ] Returns 200 with full agent details
- [ ] Capabilities and metadata match what was sent

---

## Gateway Policy Enforcement

### 8. Gateway denies without policy (fail-closed)

```bash
curl -s -X POST "$GATEWAY/gateway/enforce?\
agent_id=$AGENT_ID&endpoint=/v1/chat/completions&method=POST" \
  | python3 -m json.tool
```

- [ ] Returns `"decision": "deny"`
- [ ] `deny_reason` is `"no_active_policy"`
- [ ] Status code is 403

### 9. Create a policy

```bash
curl -s -X POST $API/api/v1/agents/$AGENT_ID/policies \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "rules": {
      "allowed_endpoints": ["/v1/chat/*", "/v1/embeddings"],
      "allowed_methods": ["POST", "GET"]
    }
  }' | python3 -m json.tool
```

- [ ] Returns 201 with policy object
- [ ] `is_active` is `true`
- [ ] `version` is `1`

### 10. Gateway allows matching request

```bash
curl -s -X POST "$GATEWAY/gateway/enforce?\
agent_id=$AGENT_ID&endpoint=/v1/chat/completions&method=POST" \
  | python3 -m json.tool
```

- [ ] Returns `"decision": "allow"`
- [ ] Status code is 200

### 11. Gateway denies non-matching request

```bash
curl -s -X POST "$GATEWAY/gateway/enforce?\
agent_id=$AGENT_ID&endpoint=/v1/admin/secrets&method=DELETE" \
  | python3 -m json.tool
```

- [ ] Returns `"decision": "deny"`
- [ ] `deny_reason` is `"policy_denied"`

---

## Audit & Compliance

### 12. Audit log records all decisions

```bash
curl -s "$API/api/v1/audit?agent_id=$AGENT_ID&limit=10" \
  -H "X-API-Key: $KEY" | python3 -m json.tool
```

- [ ] Returns entries for the allow and deny requests from steps 8, 10, 11
- [ ] Each entry has `endpoint`, `method`, `decision`
- [ ] Each entry has `entry_hash` and `prev_hash` (HMAC chain)
- [ ] Entries are ordered newest-first

### 13. Audit chain integrity verification

```bash
curl -s "$API/api/v1/audit/verify" \
  -H "X-API-Key: $KEY" | python3 -m json.tool
```

- [ ] Returns `"valid": true`
- [ ] `entries_verified` > 0
- [ ] `first_broken_id` is `null`

---

## Key Management & Cleanup

### 14. Key rotation (zero-downtime)

```bash
curl -s -X POST $API/api/v1/agents/$AGENT_ID/keys/rotate \
  -H "X-API-Key: $KEY" | python3 -m json.tool
```

- [ ] Returns 201 with `new_key`, `api_key`, and `rotated_key`
- [ ] `new_key.status` is `"active"`
- [ ] `rotated_key.status` is `"rotated"`
- [ ] `rotated_key.expires_at` is ~24 hours from now

### 15. Revoke QA agent (cleanup)

```bash
curl -s -X DELETE $API/api/v1/agents/$AGENT_ID \
  -H "X-API-Key: $KEY" | python3 -m json.tool
```

- [ ] Returns 200 with agent status `"revoked"`
- [ ] Subsequent gateway enforce returns `"agent_inactive"` or `"agent_not_found"`

Verify:
```bash
curl -s -X POST "$GATEWAY/gateway/enforce?\
agent_id=$AGENT_ID&endpoint=/v1/chat/completions&method=POST" \
  | python3 -m json.tool
```

- [ ] Revoked agent is denied by gateway

---

## Result

| Section                    | Steps | Pass | Fail |
|----------------------------|-------|------|------|
| Health & Infrastructure    | 1–3   |      |      |
| Auth & Agent Lifecycle     | 4–7   |      |      |
| Gateway Policy Enforcement | 8–11  |      |      |
| Audit & Compliance         | 12–13 |      |      |
| Key Management & Cleanup   | 14–15 |      |      |

**Run date:** ____________
**Run by:** ____________
**All 15 steps pass?** [ ] Yes / [ ] No
**Notes:**
