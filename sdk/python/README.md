# AI Identity Python SDK

Official Python SDK for the [AI Identity](https://ai-identity.co) API — identity, governance, and forensics for AI agents.

## Installation

```bash
pip install ai-identity
```

## Quick Start

### Async (recommended)

```python
from ai_identity import AIIdentityClient

async with AIIdentityClient(api_key="aid_sk_...") as client:
    # Create an agent
    result = await client.agents.create(
        name="support-bot",
        description="Tier 1 customer support",
    )
    print(f"Agent ID: {result.agent.id}")
    print(f"API Key: {result.api_key}")  # Store securely!

    # List agents
    agents = await client.agents.list(status="active")
    for agent in agents.items:
        print(f"  {agent.name} ({agent.status})")

    # Create a policy
    await client.policies.create(
        agent_id=result.agent.id,
        rules={"blocked_endpoints": ["/admin/*"], "max_tokens_per_request": 4096},
    )

    # Verify audit chain integrity
    verification = await client.audit.verify_chain(result.agent.id)
    print(f"Chain valid: {verification.valid}")
```

### Sync (for scripts and notebooks)

```python
from ai_identity import SyncAIIdentityClient

client = SyncAIIdentityClient(api_key="aid_sk_...")
agents = client.agents.list()
print(f"Total agents: {agents.total}")
client.close()
```

## Resources

| Resource | Methods |
|----------|---------|
| `client.agents` | `create`, `list`, `get`, `update`, `delete` |
| `client.keys` | `create`, `list`, `rotate`, `revoke` |
| `client.policies` | `create`, `list` |
| `client.credentials` | `create`, `list`, `rotate`, `revoke` |
| `client.audit` | `list`, `stats`, `verify_chain` |

## Error Handling

```python
from ai_identity import AIIdentityClient, AuthenticationError, NotFoundError

async with AIIdentityClient(api_key="aid_sk_...") as client:
    try:
        agent = await client.agents.get("nonexistent-id")
    except NotFoundError:
        print("Agent not found")
    except AuthenticationError:
        print("Invalid API key")
```

## Configuration

```python
client = AIIdentityClient(
    api_key="aid_sk_...",
    base_url="https://api.ai-identity.co",  # Custom base URL
    timeout=60.0,  # Request timeout in seconds
)
```

## API Documentation

Full API reference: [https://api.ai-identity.co/docs](https://api.ai-identity.co/docs)

## License

MIT
