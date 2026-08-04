"""Query the audit log and verify chain integrity.

Every request an agent makes — allowed or denied — is appended to a
tamper-evident, HMAC-chained audit log: each entry's hash covers the
previous entry's hash, so any edit, deletion, or reordering breaks the
chain at a provable point.

Run:
    export AI_IDENTITY_API_KEY="aid_sk_..."
    export AGENT_ID="..."                     # an agent with some traffic
    python 03_audit_and_verify.py
"""

import asyncio
import os

from ai_identity import AIIdentityClient


async def main() -> None:
    agent_id = os.environ["AGENT_ID"]
    async with AIIdentityClient(api_key=os.environ["AI_IDENTITY_API_KEY"]) as client:
        # Recent activity, newest first.
        entries = await client.audit.list(agent_id=agent_id, limit=10)
        print(f"{entries.total} audit entries for agent {agent_id}; showing {len(entries.items)}:")
        for e in entries.items:
            print(f"  [{e.created_at:%Y-%m-%d %H:%M:%S}] {e.decision:5s} {e.method} {e.endpoint}")

        # Aggregates: allow/deny counts, spend, latency, hot endpoints.
        stats = await client.audit.stats(agent_id=agent_id)
        print(
            f"\nAllowed {stats.allowed_count} / denied {stats.denied_count} "
            f"of {stats.total_events} events, est. cost ${stats.total_cost_usd:.4f}"
        )

        # Walk the full HMAC chain server-side. If anything was altered,
        # first_broken_id pinpoints where.
        verification = await client.audit.verify_chain(agent_id)
        print(
            f"\nChain valid: {verification.valid} "
            f"({verification.entries_verified}/{verification.total_entries} entries verified)"
        )
        if not verification.valid:
            print(f"Chain breaks at entry {verification.first_broken_id}: {verification.message}")

        # For exported evidence bundles there is also an offline path that
        # requires no API and no trust in this service: the MIT-licensed
        # verifier CLI at cli/ai_identity_verify.py in this repository.


if __name__ == "__main__":
    asyncio.run(main())
