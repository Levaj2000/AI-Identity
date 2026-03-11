# AI Identity API — Quick Start

AI Identity gives every AI agent a verifiable identity, cryptographic API keys,
and (soon) policy-based guardrails. Three steps to get started:

1. **Create an agent** with a name and capabilities
2. **Store the API key** returned at creation (it's shown only once)
3. **Manage keys** — rotate, revoke, or issue additional keys without downtime

## Base URLs

| Environment | URL |
|-------------|-----|
| Production  | `https://ai-identity-api.onrender.com` |
| Local dev   | `http://localhost:8001` |

## Interactive Docs

- **Swagger UI**: [/docs](http://localhost:8001/docs)
- **ReDoc**: [/redoc](http://localhost:8001/redoc)
- **OpenAPI spec**: [/openapi.json](http://localhost:8001/openapi.json)

## Authentication

All endpoints require an `X-API-Key` header. For local development, use
the seeded dev key:

```
X-API-Key: test-dev-key-12345678
```

---

## Step 1: Create an Agent

```bash
curl -s -X POST http://localhost:8001/api/v1/agents \
  -H "X-API-Key: test-dev-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support Bot",
    "description": "Handles tier-1 support tickets via chat",
    "capabilities": ["chat_completion", "function_calling"],
    "metadata": {"framework": "langchain", "environment": "production"}
  }'
```

**Response (201):**
```json
{
  "agent": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Customer Support Bot",
    "status": "active",
    "capabilities": ["chat_completion", "function_calling"],
    "metadata": {"framework": "langchain", "environment": "production"},
    ...
  },
  "api_key": "aid_sk_a1b2c3d4..."
}
```

Save the `api_key` value — it cannot be retrieved again.

## Step 2: List Your Agents

```bash
curl -s http://localhost:8001/api/v1/agents \
  -H "X-API-Key: test-dev-key-12345678"
```

Filter by status or capability:

```bash
# Only active agents
curl -s "http://localhost:8001/api/v1/agents?status=active" \
  -H "X-API-Key: test-dev-key-12345678"

# Only agents with chat_completion capability
curl -s "http://localhost:8001/api/v1/agents?capability=chat_completion" \
  -H "X-API-Key: test-dev-key-12345678"
```

## Step 3: Manage API Keys

### Create an additional key

```bash
curl -s -X POST http://localhost:8001/api/v1/agents/{agent_id}/keys \
  -H "X-API-Key: test-dev-key-12345678"
```

### List keys (prefix + status only)

```bash
curl -s http://localhost:8001/api/v1/agents/{agent_id}/keys \
  -H "X-API-Key: test-dev-key-12345678"
```

### Rotate a key (zero-downtime)

Issues a new key and gives the old key a 24-hour grace period:

```bash
curl -s -X POST http://localhost:8001/api/v1/agents/{agent_id}/keys/rotate \
  -H "X-API-Key: test-dev-key-12345678"
```

**Response (201):**
```json
{
  "new_key": { "status": "active", ... },
  "api_key": "aid_sk_f7e8d9c0...",
  "rotated_key": { "status": "rotated", "expires_at": "2026-03-12T12:00:00Z", ... }
}
```

Both keys work for 24 hours. After the grace period, the old key is
automatically revoked.

### Revoke a specific key

```bash
curl -s -X DELETE http://localhost:8001/api/v1/agents/{agent_id}/keys/{key_id} \
  -H "X-API-Key: test-dev-key-12345678"
```

## Step 4: Update an Agent

```bash
curl -s -X PUT http://localhost:8001/api/v1/agents/{agent_id} \
  -H "X-API-Key: test-dev-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{
    "capabilities": ["chat_completion", "embeddings", "function_calling"],
    "metadata": {"environment": "staging", "version": "2.0"}
  }'
```

## Step 5: Revoke an Agent

Soft-deletes the agent and revokes all its keys:

```bash
curl -s -X DELETE http://localhost:8001/api/v1/agents/{agent_id} \
  -H "X-API-Key: test-dev-key-12345678"
```

---

## Local Development

```bash
# Clone and set up
git clone https://github.com/Levaj2000/AI-Identity.git
cd AI-Identity
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start the API server
uvicorn api.app.main:app --reload --port 8001

# Run tests
python -m pytest api/tests/ -v

# Open the docs
open http://localhost:8001/docs
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/agents` | Create agent (+ initial key) |
| `GET` | `/api/v1/agents` | List agents |
| `GET` | `/api/v1/agents/{id}` | Get agent details |
| `PUT` | `/api/v1/agents/{id}` | Update agent |
| `DELETE` | `/api/v1/agents/{id}` | Revoke agent |
| `POST` | `/api/v1/agents/{id}/keys` | Create additional key |
| `GET` | `/api/v1/agents/{id}/keys` | List keys |
| `POST` | `/api/v1/agents/{id}/keys/rotate` | Rotate key (24hr grace) |
| `DELETE` | `/api/v1/agents/{id}/keys/{key_id}` | Revoke key |
