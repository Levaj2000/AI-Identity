# AI Identity — Quickstart: Zero to First Gateway Request in 15 Minutes

This guide walks you through registering an AI agent, attaching an access
policy, and sending your first request through the gateway — all with `curl`
and a short Python script.

## Base URLs

| Service       | Production                                    | Local dev              |
|---------------|-----------------------------------------------|------------------------|
| Identity API  | `https://ai-identity-api.onrender.com`        | `http://localhost:8001` |
| Gateway       | `https://ai-identity-gateway.onrender.com`    | `http://localhost:8002` |

## Prerequisites

- A user API key (for local dev, use: `test-dev-key-12345678`)
- `curl` installed
- Python 3.10+ (for the Python example)

Set your base URLs (adjust for production if needed):

```bash
API=http://localhost:8001
GATEWAY=http://localhost:8002
KEY=test-dev-key-12345678
```

---

## Step 1: Create an Agent

```bash
curl -s -X POST $API/api/v1/agents \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Agent",
    "description": "Quickstart demo agent",
    "capabilities": ["chat_completion"]
  }' | python3 -m json.tool
```

**Response (201):**
```json
{
  "agent": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My First Agent",
    "status": "active",
    ...
  },
  "api_key": "aid_sk_a1b2c3d4..."
}
```

Save both values — you'll need the `agent.id` for the next steps, and the
`api_key` is **shown only once**.

```bash
AGENT_ID=<paste agent id here>
```

---

## Step 2: Attach a Policy

Without a policy, the gateway will deny every request (fail-closed). Create
one that allows chat and embeddings endpoints:

```bash
curl -s -X POST $API/api/v1/agents/$AGENT_ID/policies \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "rules": {
      "allowed_endpoints": ["/v1/chat/*", "/v1/embeddings"],
      "allowed_methods": ["POST"]
    }
  }' | python3 -m json.tool
```

**Response (201):**
```json
{
  "id": 1,
  "agent_id": "550e8400-...",
  "rules": {
    "allowed_endpoints": ["/v1/chat/*", "/v1/embeddings"],
    "allowed_methods": ["POST"]
  },
  "version": 1,
  "is_active": true,
  ...
}
```

### Policy rules reference

| Field               | Description                                            |
|---------------------|--------------------------------------------------------|
| `allowed_endpoints` | Endpoint patterns the agent can access (`/v1/*`, `*`)  |
| `denied_endpoints`  | Explicitly blocked patterns (checked first)            |
| `allowed_methods`   | HTTP methods allowed (`GET`, `POST`, etc.)             |
| `max_cost_usd`      | Optional per-request cost cap                          |

---

## Step 3: Send a Request Through the Gateway

Now test the gateway's enforce endpoint — this is the core of AI Identity:

```bash
# This should be ALLOWED (matches policy)
curl -s -X POST "$GATEWAY/gateway/enforce?\
agent_id=$AGENT_ID&\
endpoint=/v1/chat/completions&\
method=POST" | python3 -m json.tool
```

**Response (200):**
```json
{
  "decision": "allow",
  "status_code": 200,
  "message": "Request allowed"
}
```

### Test a denied request

```bash
# This should be DENIED (DELETE not in allowed_methods)
curl -s -X POST "$GATEWAY/gateway/enforce?\
agent_id=$AGENT_ID&\
endpoint=/v1/chat/completions&\
method=DELETE" | python3 -m json.tool
```

**Response (403):**
```json
{
  "decision": "deny",
  "status_code": 403,
  "message": "Request denied by policy",
  "deny_reason": "policy_denied"
}
```

---

## Step 4: Check the Audit Trail

Every gateway decision is logged with HMAC integrity:

```bash
curl -s "$API/api/v1/audit?agent_id=$AGENT_ID&limit=5" \
  -H "X-API-Key: $KEY" | python3 -m json.tool
```

Verify chain integrity:

```bash
curl -s "$API/api/v1/audit/verify" \
  -H "X-API-Key: $KEY" | python3 -m json.tool
```

---

## Python Example

Here's the full flow in Python — register an agent, attach a policy, and
enforce a request:

```python
"""AI Identity quickstart — zero to first gateway request."""

import requests

API = "http://localhost:8001"       # Identity API
GATEWAY = "http://localhost:8002"   # Gateway
KEY = "test-dev-key-12345678"       # Your user API key
HEADERS = {"X-API-Key": KEY, "Content-Type": "application/json"}

# 1. Create an agent
agent_resp = requests.post(f"{API}/api/v1/agents", headers=HEADERS, json={
    "name": "Python Quickstart Agent",
    "capabilities": ["chat_completion"],
})
agent_resp.raise_for_status()
data = agent_resp.json()
agent_id = data["agent"]["id"]
agent_key = data["api_key"]
print(f"Agent created: {agent_id}")
print(f"API key (save this!): {agent_key}")

# 2. Attach a policy
policy_resp = requests.post(
    f"{API}/api/v1/agents/{agent_id}/policies",
    headers=HEADERS,
    json={
        "rules": {
            "allowed_endpoints": ["/v1/chat/*", "/v1/embeddings"],
            "allowed_methods": ["POST"],
        }
    },
)
policy_resp.raise_for_status()
print(f"Policy v{policy_resp.json()['version']} attached")

# 3. Enforce a request through the gateway
enforce_resp = requests.post(f"{GATEWAY}/gateway/enforce", params={
    "agent_id": agent_id,
    "endpoint": "/v1/chat/completions",
    "method": "POST",
})
result = enforce_resp.json()
print(f"Gateway decision: {result['decision']}")  # → "allow"

# 4. Try a denied request
denied_resp = requests.post(f"{GATEWAY}/gateway/enforce", params={
    "agent_id": agent_id,
    "endpoint": "/v1/admin/users",
    "method": "GET",
})
denied = denied_resp.json()
print(f"Gateway decision: {denied['decision']}")       # → "deny"
print(f"Reason: {denied.get('deny_reason')}")           # → "policy_denied"

# 5. Check audit trail
audit_resp = requests.get(
    f"{API}/api/v1/audit",
    headers=HEADERS,
    params={"agent_id": agent_id, "limit": 5},
)
entries = audit_resp.json()["items"]
print(f"\nAudit log ({len(entries)} entries):")
for entry in entries:
    print(f"  {entry['endpoint']} {entry['method']} → {entry['decision']}")
```

---

## What's Happening Under the Hood

```
Your app                     AI Identity
────────                     ───────────
                    ┌─────────────────────────────┐
  POST /v1/chat ──→ │ Gateway  (/gateway/enforce)  │
                    │  1. Rate limit (100/s per IP) │
                    │  2. Circuit breaker check      │
                    │  3. Agent lookup + validation   │
                    │  4. Policy evaluation           │
                    │  5. HMAC audit log              │
                    │  → ALLOW or DENY               │
                    └─────────────────────────────┘
                                  │
                         decision: allow
                                  │
                    ┌─────────────────────────────┐
  forward to ──────→ │ Upstream API (OpenAI, etc.)  │
  upstream          └─────────────────────────────┘
```

The gateway is a **decision engine**, not a proxy. Your application calls
`/gateway/enforce` before forwarding to the upstream API. If the decision
is `allow`, proceed. If `deny`, block the request.

---

## Key Concepts

| Concept              | Description                                                       |
|----------------------|-------------------------------------------------------------------|
| **Fail-closed**      | Any error (timeout, missing policy, DB down) → request denied     |
| **Key types**        | `runtime` keys for proxy endpoints, `admin` keys for management   |
| **Circuit breaker**  | Opens after 5 failures in 60s, recovers after 30s                 |
| **Audit chain**      | Every decision logged with HMAC-SHA256 integrity verification     |
| **Rate limiting**    | 100 req/s per IP, 60 req/s per agent key (pre-policy)             |

---

## Next Steps

- **Swagger UI**: Open `$API/docs` for interactive API documentation
- **Dashboard**: Visit [dashboard.ai-identity.co](https://dashboard.ai-identity.co) to manage agents visually
- **Key rotation**: `POST /api/v1/agents/{id}/keys/rotate` for zero-downtime key rotation
- **Demo playground**: Try the interactive demo at `/demo` on the dashboard

## API Reference

| Method   | Endpoint                                    | Description                          |
|----------|---------------------------------------------|--------------------------------------|
| `GET`    | `/health`                                   | Health check                         |
| `POST`   | `/api/v1/agents`                            | Create agent (+ initial key)         |
| `GET`    | `/api/v1/agents`                            | List agents                          |
| `GET`    | `/api/v1/agents/{id}`                       | Get agent details                    |
| `PUT`    | `/api/v1/agents/{id}`                       | Update agent                         |
| `DELETE` | `/api/v1/agents/{id}`                       | Revoke agent                         |
| `POST`   | `/api/v1/agents/{id}/keys`                  | Create additional key                |
| `GET`    | `/api/v1/agents/{id}/keys`                  | List keys                            |
| `POST`   | `/api/v1/agents/{id}/keys/rotate`           | Rotate key (24hr grace)              |
| `DELETE` | `/api/v1/agents/{id}/keys/{key_id}`         | Revoke key                           |
| `POST`   | `/api/v1/agents/{id}/policies`              | Create policy (deactivates previous) |
| `GET`    | `/api/v1/agents/{id}/policies`              | List all policies                    |
| `GET`    | `/api/v1/agents/{id}/policies/active`       | Get active policy                    |
| `POST`   | `/gateway/enforce`                          | Policy enforcement decision          |
| `GET`    | `/gateway/circuit-breaker`                  | Circuit breaker status               |
| `GET`    | `/api/v1/audit`                             | Audit log (paginated)                |
| `GET`    | `/api/v1/audit/verify`                      | Verify audit chain integrity         |
