"""Basic AI Identity + LangChain agent example.

This is the minimal working example — five lines of setup, then run.

Prerequisites
-------------
    pip install langchain-ai-identity duckduckgo-search

Usage
-----
    export OPENAI_API_KEY="sk-..."
    export AI_IDENTITY_API_KEY="aid_sk_..."
    export AI_IDENTITY_AGENT_ID="<your-agent-uuid>"
    python examples/basic_agent.py
"""

import os

from langchain_community.tools import DuckDuckGoSearchRun

from langchain_ai_identity import create_ai_identity_agent

# ---------------------------------------------------------------------------
# Configuration — pull from environment variables in production
# ---------------------------------------------------------------------------
AGENT_ID = os.environ.get("AI_IDENTITY_AGENT_ID", "your-agent-id")
AI_IDENTITY_API_KEY = os.environ.get("AI_IDENTITY_API_KEY", "aid_sk_...")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "sk-...")

# ---------------------------------------------------------------------------
# Create the agent — all identity, policy, and audit wiring happens here
# ---------------------------------------------------------------------------
agent = create_ai_identity_agent(
    tools=[DuckDuckGoSearchRun()],
    agent_id=AGENT_ID,
    ai_identity_api_key=AI_IDENTITY_API_KEY,
    openai_api_key=OPENAI_API_KEY,
    model="gpt-4o",
    verbose=True,
)

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = agent.invoke({"input": "What is the latest news about AI agent security?"})
    print("\n--- Agent Output ---")
    print(result["output"])
