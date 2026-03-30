# AI Identity TypeScript SDK

Official TypeScript SDK for the [AI Identity](https://ai-identity.co) API — identity, governance, and forensics for AI agents.

## Installation

```bash
npm install @ai-identity/sdk
```

## Quick Start

```typescript
import { AIIdentityClient } from "@ai-identity/sdk";

const client = new AIIdentityClient({ apiKey: "aid_sk_..." });

// Create an agent
const result = await client.agents.create({
  name: "support-bot",
  description: "Tier 1 customer support",
});
console.log(`Agent ID: ${result.agent.id}`);
console.log(`API Key: ${result.api_key}`); // Store securely!

// List agents
const agents = await client.agents.list({ status: "active" });
for (const agent of agents.items) {
  console.log(`  ${agent.name} (${agent.status})`);
}

// Create a policy
await client.policies.create(result.agent.id, {
  rules: { blocked_endpoints: ["/admin/*"], max_tokens_per_request: 4096 },
});

// Verify audit chain integrity
const verification = await client.audit.verifyChain(result.agent.id);
console.log(`Chain valid: ${verification.valid}`);
```

## Resources

| Resource | Methods |
|----------|---------|
| `client.agents` | `create`, `list`, `get`, `update`, `delete` |
| `client.keys` | `create`, `list`, `rotate`, `revoke` |
| `client.policies` | `create`, `list` |
| `client.credentials` | `create`, `list`, `rotate`, `revoke` |
| `client.audit` | `list`, `stats`, `verifyChain` |

## Error Handling

```typescript
import { AIIdentityClient, NotFoundError, AuthenticationError } from "@ai-identity/sdk";

const client = new AIIdentityClient({ apiKey: "aid_sk_..." });

try {
  await client.agents.get("nonexistent-id");
} catch (err) {
  if (err instanceof NotFoundError) {
    console.log("Agent not found");
  } else if (err instanceof AuthenticationError) {
    console.log("Invalid API key");
  }
}
```

## Configuration

```typescript
const client = new AIIdentityClient({
  apiKey: "aid_sk_...",
  baseUrl: "https://ai-identity-api.onrender.com", // Custom base URL
  timeout: 60_000, // Request timeout in ms
});
```

## Requirements

- Node.js 18+ (uses native `fetch`)
- Zero runtime dependencies

## API Documentation

Full API reference: [https://ai-identity-api.onrender.com/docs](https://ai-identity-api.onrender.com/docs)

## License

MIT
