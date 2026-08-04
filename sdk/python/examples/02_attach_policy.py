"""Create an agent and attach an enforcement policy.

Policies are evaluated by the gateway on every request the agent makes.
Enforcement is fail-closed: an agent with no active policy is denied, and
a deny rule always wins over an allow rule.

Run:
    export AI_IDENTITY_API_KEY="aid_sk_..."
    python 02_attach_policy.py
"""

import asyncio
import os

from ai_identity import AIIdentityClient


async def main() -> None:
    async with AIIdentityClient(api_key=os.environ["AI_IDENTITY_API_KEY"]) as client:
        created = await client.agents.create(
            name="billing-assistant",
            description="Reads invoices, never touches admin surfaces",
        )
        agent = created.agent
        print(f"Created agent {agent.id}")

        # Rule keys the gateway evaluates: allowed_endpoints, denied_endpoints,
        # allowed_methods. Endpoints support trailing-wildcard patterns.
        policy = await client.policies.create(
            agent.id,
            rules={
                "allowed_endpoints": ["/v1/chat", "/v1/invoices/*"],
                "denied_endpoints": ["/v1/admin/*"],  # deny always wins
                "allowed_methods": ["GET", "POST"],
            },
        )
        print(f"Attached policy {policy.id}")

        # Every policy attached to the agent:
        for p in await client.policies.list(agent.id):
            print(f"  policy {p.id}: {p.rules}")


if __name__ == "__main__":
    asyncio.run(main())
