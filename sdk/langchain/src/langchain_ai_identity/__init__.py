"""langchain-ai-identity — Secure your LangChain agents with per-agent identity,
policy enforcement, and tamper-proof audit logs.

Quickstart::

    from langchain_community.tools import DuckDuckGoSearchRun
    from langchain_ai_identity import create_ai_identity_agent

    agent = create_ai_identity_agent(
        tools=[DuckDuckGoSearchRun()],
        agent_id="<your-agent-uuid>",
        ai_identity_api_key="aid_sk_...",
        openai_api_key="sk-...",
    )
    result = agent.invoke({"input": "What is the latest news on AI safety?"})
    print(result["output"])

See Also:
    - Documentation: https://ai-identity.co/docs/langchain
    - AI Identity platform: https://ai-identity.co
    - GitHub: https://github.com/ai-identity/langchain-ai-identity
"""

from langchain_ai_identity.agent import create_ai_identity_agent
from langchain_ai_identity.callback import (
    AIIdentityAsyncCallbackHandler,
    AIIdentityCallbackHandler,
)
from langchain_ai_identity.chat_models import AIIdentityChatOpenAI
from langchain_ai_identity.tools import AIIdentityToolkit

__version__ = "0.1.0"
__author__ = "AI Identity"
__email__ = "jeff@ai-identity.co"

__all__ = [
    "AIIdentityCallbackHandler",
    "AIIdentityAsyncCallbackHandler",
    "AIIdentityToolkit",
    "AIIdentityChatOpenAI",
    "create_ai_identity_agent",
]
