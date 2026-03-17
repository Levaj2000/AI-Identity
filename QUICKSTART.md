# AI Identity — Quickstart Guide

**Zero to first agent identity + gateway-proxied request in 15 minutes.**

> Prefer an interactive walkthrough? Try the [Live Demo](https://ai-identity.co/demo) — it runs these same steps against the real API.

---

## Prerequisites

- A terminal with `curl` (or Python 3.8+)
- An AI Identity API key — sign up at [dashboard.ai-identity.co](https://dashboard.ai-identity.co) or use the dev key below for local development

## Base URLs

| Environment | API | Gateway |
|-------------|-----|---------|
| Production  | `https://ai-identity-api.onrender.com` | `https://ai-identity-gateway.onrender.com` |
| Local dev   | `http://localhost:8001` | `http://localhost:8002` |

Set your base URL and API key for the examples below:

```bash
export AI_API=https://ai-identity-api.onrender.com
export AI_GW=https://ai-identity-gateway.onrender.com
export API_KEY=your-api-key-here   # or test-dev-key-12345678 for local dev
```

---

## Step 1: Sign Up & Get Your API Key (~2 min)

**Option A — Dashboard:**
Go to [dashboard.ai-identity.co](https://dashboard.ai-identity.co), sign in, and copy your API key from the overview page.

**Option B — Health check first:**
Verify the API is reachable before you start:

```bash
curl -s $AI_API/health | jq
```
```json
{
  "status": "ok",
  "version": "0.4.0",
  "service": "ai-identity-api"
}
```

<details>
<summary>Python</summary>

```python
import requests

API = "https://ai-identity-api.onrender.com"
GW  = "https://ai-identity-gateway.onrender.com"
API_KEY = "your-api-key-here"
headers = {"X-API-Key": API_KEY}

r = requests.get(f"{API}/health")
print(r.json())  # {"status": "ok", ...}
```
</details>

---

## Step 2: Create an Agent (~3 min)

Register your first agent with a name, description, and capabilities:

```bash
curl -s -X POST $AI_API/api/v1/agents \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Support Bot",
    "description": "Handles tier-1 support tickets via chat",
    "capabilities": ["chat_completion", "function_calling"],
    "metadata": {"framework": "langchain", "environment": "production"}
  }' | jq
```

```json
{
  "agent": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Support Bot",
    "status": "active",
    "capabilities": ["chat_completion", "function_calling"],
    "metadata": {"framework": "langchain", "environment": "production"}
  },
  "api_key": "aid_sk_a1b2c3d4e5f6g7h8..."
}
```

**Save both values:**

```bash
export AGENT_ID=550e8400-e29b-41d4-a716-446655440000
export AGENT_KEY=aid_sk_a1b2c3d4e5f6g7h8...
```

> The `api_key` is shown **only once** at creation. Store it securely.

<details>
<summary>Python</summary>

```python
r = requests.post(f"{API}/api/v1/agents", headers=headers, json={
    "name": "Support Bot",
    "description": "Handles tier-1 support tickets via chat",
    "capabilities": ["chat_completion", "function_calling"],
    "metadata": {"framework": "langchain", "environment": "production"},
})
data = r.json()
agent_id = data["agent"]["id"]
agent_key = data["api_key"]
print(f"Agent ID:  {agent_id}")
print(f"Agent Key: {agent_key}")
```
</details>

---

## Step 3: Store an Upstream Credential (~2 min)

Store your upstream provider key (e.g., OpenAI) in the encrypted credential vault. AI Identity encrypts it with Fernet (AES-128-CBC) — the plaintext is never stored or returned.

```bash
curl -s -X POST $AI_API/api/v1/agents/$AGENT_ID/credentials \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "label": "production-key",
    "api_key": "sk-proj-your-openai-key-here"
  }' | jq
```

```json
{
  "id": 1,
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "provider": "openai",
  "label": "production-key",
  "key_prefix": "sk-proj-",
  "status": "active",
  "created_at": "2026-03-17T10:00:00Z"
}
```

Only the `key_prefix` (first 8 chars) is visible — for identification, not retrieval.

<details>
<summary>Python</summary>

```python
r = requests.post(
    f"{API}/api/v1/agents/{agent_id}/credentials",
    headers=headers,
    json={
        "provider": "openai",
        "label": "production-key",
        "api_key": "sk-proj-your-openai-key-here",
    },
)
cred = r.json()
print(f"Credential stored: {cred['provider']} ({cred['key_prefix']}...)")
```
</details>

---

## Step 4: Send a Request Through the Gateway (~3 min)

The gateway enforces per-agent policy before any request hits the upstream provider. Send a chat completion request through the proxy:

```bash
# This request will be ALLOWED — runtime key on a runtime endpoint
curl -s -X POST "$AI_GW/gateway/enforce?agent_id=$AGENT_ID&endpoint=/v1/chat/completions&method=POST&key_type=runtime" | jq
```

```json
{
  "decision": "allow",
  "status_code": 200,
  "message": "Request allowed by default-allow policy"
}
```

Now try a request that should be **denied** — a runtime key accessing a management endpoint:

```bash
# This request will be DENIED — runtime key can't access management endpoints
curl -s -X POST "$AI_GW/gateway/enforce?agent_id=$AGENT_ID&endpoint=/api/v1/agents&method=GET&key_type=runtime" | jq
```

```json
{
  "decision": "deny",
  "status_code": 403,
  "message": "Runtime keys cannot access management endpoints",
  "deny_reason": "runtime_key_on_management_endpoint"
}
```

This is the key insight: **agent runtime keys can call AI APIs but cannot manage other agents.** Separation of concerns, enforced at the gateway.

<details>
<summary>Python</summary>

```python
# Allowed: runtime key on runtime endpoint
r = requests.post(f"{GW}/gateway/enforce", params={
    "agent_id": agent_id,
    "endpoint": "/v1/chat/completions",
    "method": "POST",
    "key_type": "runtime",
})
print(r.json())  # {"decision": "allow", ...}

# Denied: runtime key on management endpoint
r = requests.post(f"{GW}/gateway/enforce", params={
    "agent_id": agent_id,
    "endpoint": "/api/v1/agents",
    "method": "GET",
    "key_type": "runtime",
})
print(r.json())  # {"decision": "deny", "deny_reason": "runtime_key_on_management_endpoint"}
```
</details>

---

## Step 5: View the Audit Log (~2 min)

Every gateway decision is recorded in a tamper-proof, HMAC-chained audit log:

```bash
curl -s "$AI_API/api/v1/audit?agent_id=$AGENT_ID&limit=5" \
  -H "X-API-Key: $API_KEY" | jq
```

```json
{
  "items": [
    {
      "id": 1,
      "agent_id": "550e8400-...",
      "endpoint": "/v1/chat/completions",
      "method": "POST",
      "decision": "allow",
      "entry_hash": "a3f2b8c1d4e5...",
      "prev_hash": "GENESIS",
      "created_at": "2026-03-17T10:01:00Z"
    },
    {
      "id": 2,
      "agent_id": "550e8400-...",
      "endpoint": "/api/v1/agents",
      "method": "GET",
      "decision": "deny",
      "entry_hash": "f7e8d9c0b1a2...",
      "prev_hash": "a3f2b8c1d4e5...",
      "created_at": "2026-03-17T10:01:05Z"
    }
  ],
  "total": 2,
  "limit": 5,
  "offset": 0
}
```

Each entry's `prev_hash` links to the previous entry's `entry_hash`, forming an immutable chain. If anyone tampers with a record, the chain breaks.

**Verify the chain integrity:**

```bash
curl -s "$AI_API/api/v1/audit/verify?agent_id=$AGENT_ID" \
  -H "X-API-Key: $API_KEY" | jq
```

```json
{
  "valid": true,
  "total_entries": 2,
  "entries_verified": 2,
  "first_broken_id": null,
  "message": "All 2 audit entries verified — chain intact"
}
```

<details>
<summary>Python</summary>

```python
# View audit log
r = requests.get(
    f"{API}/api/v1/audit",
    headers=headers,
    params={"agent_id": agent_id, "limit": 5},
)
for entry in r.json()["items"]:
    print(f"  {entry['decision']:5s}  {entry['endpoint']}")

# Verify chain integrity
r = requests.get(
    f"{API}/api/v1/audit/verify",
    headers=headers,
    params={"agent_id": agent_id},
)
result = r.json()
print(f"Chain valid: {result['valid']} ({result['entries_verified']} entries)")
```
</details>

---

## What You Just Built

In 15 minutes, you set up a complete agent identity system:

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Your Agent  │────▸│   Gateway    │────▸│  Upstream AI  │
│  (Step 2)    │     │  (Step 4)    │     │   Provider    │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  Audit Log   │
                    │  (Step 5)    │
                    └──────────────┘
```

- **Per-agent identity** — no more shared API keys across agents
- **Encrypted credential vault** — upstream keys are Fernet-encrypted at rest
- **Policy enforcement** — runtime vs. management key separation at the gateway
- **Tamper-proof audit trail** — HMAC-SHA256 chained log of every decision

---

## Key Management

Once your agent is running, you'll need to rotate keys without downtime:

### Rotate a key (zero-downtime)

Issues a new key and gives the old one a 24-hour grace period:

```bash
curl -s -X POST $AI_API/api/v1/agents/$AGENT_ID/keys/rotate \
  -H "X-API-Key: $API_KEY" | jq
```

Both keys work for 24 hours. Deploy the new key, and the old one auto-revokes.

### Revoke a key immediately

```bash
curl -s -X DELETE $AI_API/api/v1/agents/$AGENT_ID/keys/{key_id} \
  -H "X-API-Key: $API_KEY"
```

---

## Troubleshooting

### `401 Unauthorized`
- **Check your API key** — is `X-API-Key` header set correctly?
- **Key revoked?** — rotated keys expire after 24 hours. Check key status: `GET /api/v1/agents/{id}/keys`
- **Wrong environment?** — production keys don't work on localhost and vice versa

### `403 Forbidden` from the gateway
- **`runtime_key_on_management_endpoint`** — you're using a runtime key (`aid_sk_`) to call a management API (`/api/v1/agents`). Use your admin key instead.
- **`admin_key_on_runtime_endpoint`** — the inverse. Use the agent's runtime key for AI API calls.
- **`agent_inactive`** — the agent has been revoked. Create a new one.

### `404 Not Found`
- **Agent doesn't exist** — double-check the `agent_id` UUID
- **Wrong base URL** — API endpoints use `$AI_API`, gateway uses `$AI_GW`

### `429 Too Many Requests`
- **Rate limited** — the gateway allows 60 requests/second per agent, 100/second per IP
- Check the `Retry-After` response header for how long to wait

### `503 Service Unavailable`
- **Circuit breaker open** — the gateway has detected repeated failures and is protecting upstream services
- Check circuit breaker status: `GET $AI_GW/gateway/circuit-breaker`
- The breaker auto-recovers after 30 seconds

### Gateway returns `decision: "error"`
- **Policy evaluation timeout** — the gateway enforces a 500ms timeout on policy evaluation. If exceeded, it **fails closed** (denies the request). This is by design — safety over availability.

---

## API Reference

### Identity Service (`$AI_API`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/agents` | Create agent + initial key |
| `GET` | `/api/v1/agents` | List agents |
| `GET` | `/api/v1/agents/{id}` | Get agent details |
| `PUT` | `/api/v1/agents/{id}` | Update agent |
| `DELETE` | `/api/v1/agents/{id}` | Revoke agent + all keys |
| `POST` | `/api/v1/agents/{id}/keys` | Create additional key |
| `GET` | `/api/v1/agents/{id}/keys` | List keys (prefix + status) |
| `POST` | `/api/v1/agents/{id}/keys/rotate` | Rotate key (24hr grace) |
| `DELETE` | `/api/v1/agents/{id}/keys/{key_id}` | Revoke key |
| `POST` | `/api/v1/agents/{id}/credentials` | Store upstream credential |
| `GET` | `/api/v1/agents/{id}/credentials` | List credentials |
| `PUT` | `/api/v1/agents/{id}/credentials/{cred_id}/rotate` | Rotate upstream key |
| `DELETE` | `/api/v1/agents/{id}/credentials/{cred_id}` | Revoke credential |
| `GET` | `/api/v1/audit` | Query audit log |
| `GET` | `/api/v1/audit/verify` | Verify audit chain integrity |

### Gateway (`$AI_GW`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Gateway health + circuit breaker state |
| `POST` | `/gateway/enforce` | Policy enforcement (fail-closed) |
| `GET` | `/gateway/circuit-breaker` | Circuit breaker status |

---

## Interactive Docs

- **Swagger UI**: `$AI_API/docs`
- **ReDoc**: `$AI_API/redoc`
- **OpenAPI spec**: `$AI_API/openapi.json`
- **Live Demo**: [ai-identity.co/demo](https://ai-identity.co/demo)

## Local Development

```bash
git clone https://github.com/Levaj2000/AI-Identity.git
cd AI-Identity
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start both services
uvicorn api.app.main:app --reload --port 8001
uvicorn gateway.app.main:app --reload --port 8002

# Run tests
python -m pytest api/tests/ -v

# Use the dev key for local testing
export API_KEY=test-dev-key-12345678
```
