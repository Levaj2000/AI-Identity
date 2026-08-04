"""Register a new agent and manage its lifecycle.

Walks through the first thing every integration does: create an agent
identity, capture its show-once API key, then read it back and update it.

Run:
    export AI_IDENTITY_API_KEY="aid_sk_..."   # your account key
    python 01_register_agent.py
"""

import asyncio
import os

from ai_identity import AIIdentityClient


async def main() -> None:
    async with AIIdentityClient(api_key=os.environ["AI_IDENTITY_API_KEY"]) as client:
        # Create the agent. The response includes a plaintext API key for the
        # agent itself — it is shown exactly once, so store it securely now.
        created = await client.agents.create(
            name="support-bot",
            description="Tier 1 customer support agent",
            capabilities=["chat"],
            metadata={"team": "support", "env": "staging"},
        )
        agent = created.agent
        print(f"Created agent {agent.name} ({agent.id})")
        print(f"Agent API key (shown once): {created.api_key[:12]}…")

        # Read it back.
        fetched = await client.agents.get(agent.id)
        print(f"Status: {fetched.status}, created {fetched.created_at:%Y-%m-%d}")

        # Update metadata without touching anything else.
        updated = await client.agents.update(agent.id, metadata={"team": "support", "env": "prod"})
        print(f"Metadata now: {updated.metadata}")

        # List all active agents in the account.
        agents = await client.agents.list(status="active")
        print(f"Active agents: {agents.total}")
        for a in agents.items:
            print(f"  - {a.name} ({a.id})")


if __name__ == "__main__":
    asyncio.run(main())
