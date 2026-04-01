"""Convenience factory for creating AI Identity-secured LangChain agents.

``create_ai_identity_agent()`` wires together the callback handler, toolkit
enforcement, and the identity-aware chat model in a single function call.
"""

from __future__ import annotations

from typing import Any, List, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

from langchain_ai_identity.callback import AIIdentityCallbackHandler
from langchain_ai_identity.chat_models import AIIdentityChatOpenAI
from langchain_ai_identity.tools import AIIdentityToolkit

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Use the available tools to answer the user's questions accurately and concisely."
)


def create_ai_identity_agent(
    tools: List[BaseTool],
    agent_id: str,
    ai_identity_api_key: str,
    openai_api_key: str,
    model: str = "gpt-4o",
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
    fail_closed: bool = True,
    ai_identity_timeout: float = 5.0,
    verbose: bool = False,
    max_iterations: int = 10,
    return_intermediate_steps: bool = False,
    extra_llm_kwargs: Optional[dict] = None,
    extra_executor_kwargs: Optional[dict] = None,
) -> AgentExecutor:
    """Create a LangChain AgentExecutor secured by AI Identity.

    This factory function assembles:

    - An :class:`~langchain_ai_identity.chat_models.AIIdentityChatOpenAI` that
      enforces the agent's policy before every LLM call.
    - An :class:`~langchain_ai_identity.tools.AIIdentityToolkit` that enforces
      policy before every tool call.
    - An :class:`~langchain_ai_identity.callback.AIIdentityCallbackHandler`
      that logs every event to the AI Identity audit trail.

    Example::

        from langchain_community.tools import DuckDuckGoSearchRun
        from langchain_ai_identity import create_ai_identity_agent

        agent = create_ai_identity_agent(
            tools=[DuckDuckGoSearchRun()],
            agent_id="<your-agent-uuid>",
            ai_identity_api_key="aid_sk_...",
            openai_api_key="sk-...",
        )
        result = agent.invoke({"input": "What is the latest news about AI security?"})
        print(result["output"])

    Args:
        tools: List of LangChain :class:`~langchain_core.tools.BaseTool` instances.
        agent_id: UUID of the registered AI Identity agent.
        ai_identity_api_key: The ``aid_sk_`` prefixed key returned at agent creation.
        openai_api_key: OpenAI API key.
        model: OpenAI model name (default ``"gpt-4o"``).
        system_prompt: System prompt for the agent (default is a generic helpful assistant).
        fail_closed: When ``True`` (default) gateway or audit failures halt the
            agent with an exception.  When ``False``, failures emit a warning
            and the agent continues (fail-open).
        ai_identity_timeout: HTTP timeout in seconds for AI Identity calls (default 5.0).
        verbose: If ``True``, AgentExecutor prints intermediate steps.
        max_iterations: Maximum number of agent reasoning steps (default 10).
        return_intermediate_steps: If ``True``, the result dict includes
            ``intermediate_steps`` with the agent's reasoning trace.
        extra_llm_kwargs: Additional keyword arguments forwarded to
            :class:`~langchain_ai_identity.chat_models.AIIdentityChatOpenAI`.
        extra_executor_kwargs: Additional keyword arguments forwarded to
            :class:`~langchain.agents.AgentExecutor`.

    Returns:
        A fully configured :class:`~langchain.agents.AgentExecutor` ready to
        receive ``agent.invoke({"input": "..."})`` calls.
    """
    extra_llm_kwargs = extra_llm_kwargs or {}
    extra_executor_kwargs = extra_executor_kwargs or {}

    # 1. Create the identity-aware LLM
    llm = AIIdentityChatOpenAI(
        agent_id=agent_id,
        ai_identity_api_key=ai_identity_api_key,
        openai_api_key=openai_api_key,
        model=model,
        fail_closed=fail_closed,
        ai_identity_timeout=ai_identity_timeout,
        **extra_llm_kwargs,
    )

    # 2. Wrap tools with gateway enforcement
    toolkit = AIIdentityToolkit(
        tools=tools,
        agent_id=agent_id,
        api_key=ai_identity_api_key,
        fail_closed=fail_closed,
        timeout=ai_identity_timeout,
    )
    enforced_tools = toolkit.get_tools()

    # 3. Build the prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # 4. Create the OpenAI tools agent (supports parallel tool calls)
    agent = create_openai_tools_agent(llm=llm, tools=enforced_tools, prompt=prompt)

    # 5. Create a dedicated audit callback handler for the executor
    audit_handler = AIIdentityCallbackHandler(
        agent_id=agent_id,
        api_key=ai_identity_api_key,
        fail_closed=fail_closed,
        timeout=ai_identity_timeout,
    )

    # 6. Assemble the executor
    executor = AgentExecutor(
        agent=agent,
        tools=enforced_tools,
        verbose=verbose,
        max_iterations=max_iterations,
        return_intermediate_steps=return_intermediate_steps,
        callbacks=[audit_handler],
        handle_parsing_errors=True,
        **extra_executor_kwargs,
    )

    return executor
