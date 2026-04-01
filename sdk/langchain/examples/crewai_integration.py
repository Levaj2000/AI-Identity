"""CrewAI + AI Identity integration example.

This example shows how to use AI Identity's toolkit enforcement with CrewAI
agents.  CrewAI uses LangChain-compatible tools under the hood, so
``AIIdentityToolkit`` wraps them seamlessly.

Architecture
------------
    CrewAI Agent
        └── Tool call → AIIdentityToolkit.get_tools()
                └── /gateway/enforce (AI Identity)
                        └── Original tool execution (if allowed)

Prerequisites
-------------
    pip install langchain-ai-identity crewai crewai-tools duckduckgo-search

Usage
-----
    export OPENAI_API_KEY="sk-..."
    export AI_IDENTITY_API_KEY="aid_sk_..."
    export AI_IDENTITY_AGENT_ID="<your-agent-uuid>"
    python examples/crewai_integration.py

Note
----
CrewAI tools inherit from LangChain's BaseTool, so AIIdentityToolkit wraps them
without any code changes.  All tool calls go through AI Identity gateway
enforcement and are recorded in the tamper-proof audit log.
"""

from __future__ import annotations

import os
from typing import List

from langchain_core.tools import BaseTool

from langchain_ai_identity import AIIdentityCallbackHandler, AIIdentityToolkit

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AGENT_ID = os.environ.get("AI_IDENTITY_AGENT_ID", "your-agent-id")
AI_IDENTITY_API_KEY = os.environ.get("AI_IDENTITY_API_KEY", "aid_sk_...")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "sk-...")


def build_secured_tools(raw_tools: List[BaseTool]) -> List[BaseTool]:
    """Wrap any list of LangChain-compatible tools with AI Identity enforcement.

    Args:
        raw_tools: List of LangChain (or CrewAI) tools.

    Returns:
        Wrapped tools — every call goes through AI Identity gateway first.
    """
    toolkit = AIIdentityToolkit(
        tools=raw_tools,
        agent_id=AGENT_ID,
        api_key=AI_IDENTITY_API_KEY,
        fail_closed=True,  # deny on policy error — never silently skip enforcement
    )
    return toolkit.get_tools()


def run_crew() -> None:
    """Set up and run a CrewAI crew with AI Identity-enforced tools."""
    try:
        from crewai import Agent, Crew, Process, Task
        from crewai_tools import SerperDevTool
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise ImportError(
            "Install CrewAI extras: pip install langchain-ai-identity[crewai] crewai-tools"
        ) from exc

    # ---------------------------------------------------------------------------
    # 1. Define raw tools (CrewAI tools are LangChain-compatible)
    # ---------------------------------------------------------------------------
    raw_tools = [
        SerperDevTool(),  # web search via Serper API
    ]

    # ---------------------------------------------------------------------------
    # 2. Wrap all tools with AI Identity policy enforcement
    # ---------------------------------------------------------------------------
    secured_tools = build_secured_tools(raw_tools)

    # ---------------------------------------------------------------------------
    # 3. Set up audit callback — CrewAI agents accept LangChain callbacks
    # ---------------------------------------------------------------------------
    audit_callback = AIIdentityCallbackHandler(
        agent_id=AGENT_ID,
        api_key=AI_IDENTITY_API_KEY,
        fail_closed=True,
    )

    # ---------------------------------------------------------------------------
    # 4. Create the LLM with audit callback attached
    # ---------------------------------------------------------------------------
    llm = ChatOpenAI(
        model="gpt-4o",
        openai_api_key=OPENAI_API_KEY,
        callbacks=[audit_callback],
    )

    # ---------------------------------------------------------------------------
    # 5. Define CrewAI agents using secured tools
    # ---------------------------------------------------------------------------
    researcher = Agent(
        role="AI Security Researcher",
        goal="Find the latest developments in AI agent security and identity.",
        backstory=(
            "You are an expert in AI systems security with a focus on multi-agent "
            "architectures, identity management, and policy enforcement."
        ),
        tools=secured_tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    writer = Agent(
        role="Technical Writer",
        goal="Produce a clear, concise summary of AI security research findings.",
        backstory="You specialize in distilling complex technical topics for developers.",
        tools=[],  # writer doesn't need tools
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # ---------------------------------------------------------------------------
    # 6. Define tasks
    # ---------------------------------------------------------------------------
    research_task = Task(
        description=(
            "Research the latest developments in AI agent identity and security. "
            "Focus on: (1) identity standards emerging for AI agents, "
            "(2) policy enforcement approaches, (3) audit log standards."
        ),
        expected_output="A bullet-point list of key findings with sources.",
        agent=researcher,
    )

    write_task = Task(
        description=(
            "Based on the research, write a 3-paragraph developer blog intro "
            "about why AI agent identity matters in 2025."
        ),
        expected_output="Three paragraphs of developer-focused blog content.",
        agent=writer,
        context=[research_task],
    )

    # ---------------------------------------------------------------------------
    # 7. Run the crew
    # ---------------------------------------------------------------------------
    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process=Process.sequential,
        verbose=True,
    )

    print("\n=== Starting CrewAI run with AI Identity enforcement ===\n")
    result = crew.kickoff()
    print("\n=== Crew output ===")
    print(result)
    print(
        "\n[AI Identity] All tool calls were enforced via the gateway. "
        "Check the audit log at https://ai-identity-api.onrender.com/api/v1/audit"
    )


# ---------------------------------------------------------------------------
# Alternative: minimal manual integration without CrewAI
# ---------------------------------------------------------------------------

def manual_integration_example() -> None:
    """Show that AIIdentityToolkit works with any framework that uses BaseTool.

    If you're using a custom agent framework, you can integrate AI Identity
    enforcement by wrapping your tools before passing them to your framework.
    """
    from langchain_community.tools import DuckDuckGoSearchRun

    # Raw tools — any LangChain-compatible BaseTool
    raw_tools = [DuckDuckGoSearchRun()]

    # Wrap with AI Identity — that's the entire integration
    toolkit = AIIdentityToolkit(
        tools=raw_tools,
        agent_id=AGENT_ID,
        api_key=AI_IDENTITY_API_KEY,
        fail_closed=True,
    )
    secured_tools = toolkit.get_tools()

    print("Tools secured with AI Identity enforcement:")
    for tool in secured_tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")

    # Now pass `secured_tools` to your custom agent framework
    # Every tool._run() will check AI Identity before executing


if __name__ == "__main__":
    import sys

    if "--manual" in sys.argv:
        manual_integration_example()
    else:
        run_crew()
