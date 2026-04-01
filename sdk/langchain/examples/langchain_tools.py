"""Full toolkit example — multiple tools, policy enforcement in action, audit log.

This example demonstrates:
  1. Attaching multiple tools to an AI Identity-secured agent.
  2. Observing a tool call that's allowed vs. one that's denied by policy.
  3. Reading the audit log after the agent runs to verify the tamper-proof trail.

Prerequisites
-------------
    pip install langchain-ai-identity duckduckgo-search wikipedia

Usage
-----
    export OPENAI_API_KEY="sk-..."
    export AI_IDENTITY_API_KEY="aid_sk_..."
    export AI_IDENTITY_AGENT_ID="<your-agent-uuid>"
    python examples/langchain_tools.py
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.tools import BaseTool, ToolException

from langchain_ai_identity import AIIdentityCallbackHandler, AIIdentityToolkit, create_ai_identity_agent

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AGENT_ID = os.environ.get("AI_IDENTITY_AGENT_ID", "your-agent-id")
AI_IDENTITY_API_KEY = os.environ.get("AI_IDENTITY_API_KEY", "aid_sk_...")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "sk-...")
AI_IDENTITY_API_BASE = "https://ai-identity-api.onrender.com"

# ---------------------------------------------------------------------------
# Demonstrate policy enforcement in action
# ---------------------------------------------------------------------------


class RestrictedTool(BaseTool):
    """A toy tool that simulates a privileged action (e.g. sending email).

    In a real setup you'd register a policy rule in AI Identity that denies
    calls to ``/tools/restricted_action`` — this example shows how the toolkit
    surfaces that denial gracefully.
    """

    name: str = "restricted_action"
    description: str = "Perform a restricted privileged action (demo only)."

    def _run(self, query: str) -> str:  # type: ignore[override]
        return f"Privileged action executed: {query}"

    async def _arun(self, query: str) -> str:  # type: ignore[override]
        return self._run(query)


def demonstrate_pre_flight_check(toolkit: AIIdentityToolkit) -> None:
    """Show how to check tool access without actually running the tool."""
    print("\n--- Pre-flight gateway check ---")
    for tool_name in ["duckduckgo_search", "wikipedia", "restricted_action"]:
        result = toolkit.check_tool_access(tool_name)
        decision = result.get("decision", "unknown")
        reason = result.get("reason", "")
        status = "✓ ALLOW" if decision == "allow" else f"✗ DENY  ({reason})"
        print(f"  {tool_name:25s} {status}")


def read_audit_log(agent_id: str, api_key: str, since_minutes: int = 5) -> None:
    """Fetch and display recent audit log entries for the agent."""
    print("\n--- Audit log (last 5 minutes) ---")
    start = (datetime.now(tz=timezone.utc) - timedelta(minutes=since_minutes)).isoformat()
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{AI_IDENTITY_API_BASE}/api/v1/audit",
                params={"agent_id": agent_id, "start_date": start, "limit": 20},
                headers={"X-API-Key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        entries = data.get("items", data.get("entries", []))
        if not entries:
            print("  No entries found (the audit API may buffer writes briefly).")
            return

        for entry in entries:
            ts = entry.get("created_at", entry.get("timestamp", "?"))
            event = entry.get("event_type", entry.get("endpoint", "?"))
            decision = entry.get("decision", "?")
            latency = entry.get("latency_ms", "")
            latency_str = f" ({latency:.0f}ms)" if latency else ""
            print(f"  [{ts}] {event:35s} → {decision}{latency_str}")

    except Exception as exc:  # noqa: BLE001
        print(f"  Could not fetch audit log: {exc}")


def verify_audit_chain(agent_id: str, api_key: str) -> None:
    """Verify HMAC chain integrity of the audit log for this agent."""
    print("\n--- Audit chain verification ---")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{AI_IDENTITY_API_BASE}/api/v1/audit/verify",
                params={"agent_id": agent_id},
                headers={"X-API-Key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        valid = data.get("valid", data.get("chain_valid", False))
        entries_checked = data.get("entries_checked", "?")
        status = "✓ VALID" if valid else "✗ CHAIN BROKEN"
        print(f"  Chain integrity: {status}  ({entries_checked} entries checked)")
        if not valid:
            print(f"  Break detail: {data.get('first_break', data.get('detail', ''))}")

    except Exception as exc:  # noqa: BLE001
        print(f"  Could not verify audit chain: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tools = [
        DuckDuckGoSearchRun(),
        WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()),
        RestrictedTool(),
    ]

    # Build the toolkit separately so we can call pre-flight checks
    toolkit = AIIdentityToolkit(
        tools=tools,
        agent_id=AGENT_ID,
        api_key=AI_IDENTITY_API_KEY,
        fail_closed=True,
    )

    # Show which tools are allowed before we even run
    demonstrate_pre_flight_check(toolkit)

    # Build the agent using the same toolkit (reuses wrapped tools)
    agent = create_ai_identity_agent(
        tools=toolkit.get_tools(),
        agent_id=AGENT_ID,
        ai_identity_api_key=AI_IDENTITY_API_KEY,
        openai_api_key=OPENAI_API_KEY,
        model="gpt-4o",
        verbose=True,
        fail_closed=True,
    )

    print("\n--- Running agent (allowed tool call) ---")
    try:
        result = agent.invoke(
            {"input": "Search for recent papers on multi-agent AI systems and summarize."}
        )
        print("\nAgent output:", result["output"])
    except Exception as exc:
        print(f"Agent error: {exc}")

    print("\n--- Running agent (tool call that may be denied by policy) ---")
    try:
        result = agent.invoke(
            {"input": "Use the restricted_action tool to send a test message."}
        )
        print("\nAgent output:", result["output"])
    except ToolException as exc:
        print(f"Tool denied (expected): {exc}")
    except Exception as exc:
        print(f"Agent error: {exc}")

    # Give the audit API a moment to flush
    time.sleep(2)

    # Read the audit trail and verify chain integrity
    read_audit_log(AGENT_ID, AI_IDENTITY_API_KEY)
    verify_audit_chain(AGENT_ID, AI_IDENTITY_API_KEY)


if __name__ == "__main__":
    main()
