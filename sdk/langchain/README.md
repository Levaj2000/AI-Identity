# langchain-ai-identity

Secure your LangChain agents with per-agent identity, policy enforcement, and tamper-proof audit logs — in 5 lines of code.

[![PyPI version](https://img.shields.io/pypi/v/langchain-ai-identity.svg)](https://pypi.org/project/langchain-ai-identity/)
[![Python versions](https://img.shields.io/pypi/pyversions/langchain-ai-identity.svg)](https://pypi.org/project/langchain-ai-identity/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

[AI Identity](https://ai-identity.co) is the identity layer for AI agents — Okta for AI. Every agent gets a verifiable UUID identity, a cryptographic API key, policy-based guardrails, and an HMAC-chained audit log. This package makes it trivial to wire that into any LangChain agent.

---

## Installation

```bash
pip install langchain-ai-identity
```

For CrewAI support:

```bash
pip install "langchain-ai-identity[crewai]"
```

---

## Quick Start

```python
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_ai_identity import create_ai_identity_agent

agent = create_ai_identity_agent(
    tools=[DuckDuckGoSearchRun()],
    agent_id="your-agent-uuid",          # from AI Identity dashboard
    ai_identity_api_key="aid_sk_...",    # show-once key from agent creation
    openai_api_key="sk-...",
)

result = agent.invoke({"input": "What is the latest news about AI agent security?"})
print(result["output"])
```

That's it. Every tool call is policy-enforced. Every LLM call is audited. Nothing else to configure.

---

## How It Works

```
Your Agent
    │
    ├── LLM call (ChatOpenAI)
    │       │
    │       ▼
    │   AIIdentityChatOpenAI
    │       │
    │       ├── POST /gateway/enforce → AI Identity Gateway ──► OpenAI (if allowed)
    │       └── Audit log → AI Identity API
    │
    └── Tool call (search, calculator, …)
            │
            ▼
        AIIdentityToolkit
            │
            ├── POST /gateway/enforce → AI Identity Gateway ──► Tool._run() (if allowed)
            └── Audit log → AI Identity API
```

Every request to an LLM or tool is pre-checked against the agent's **policy** before executing. If the policy denies it, the call is blocked and the denial is logged. All events — whether allowed or denied — are appended to a tamper-proof HMAC-chained audit log.

---

## What Gets Enforced

### Policy rules

Policies live in AI Identity and control which endpoints and methods an agent is allowed to call. Rules can be as broad or fine-grained as you need:

```python
# Creating a policy via the AI Identity SDK (ai-identity package)
from ai_identity import SyncAIIdentityClient

client = SyncAIIdentityClient(api_key="your-dev-api-key")
client.policies.create(
    agent_id="your-agent-uuid",
    rules=[
        {"endpoint": "/v1/chat/completions", "method": "POST", "effect": "allow"},
        {"endpoint": "/tools/search",         "method": "POST", "effect": "allow"},
        {"endpoint": "/tools/send_email",     "method": "POST", "effect": "deny"},
    ],
)
```

### Key scoping

- **Runtime keys** (`aid_sk_...`) — used by agents at runtime.  Rejected on management endpoints.
- **Admin keys** (`aid_admin_...`) — used for API management.  Rejected on proxy/tool endpoints.

The gateway enforces key type separation automatically. A compromised runtime key cannot be used to create new agents or rotate credentials.

### Fail modes

```python
agent = create_ai_identity_agent(
    ...,
    fail_closed=True,   # default — gateway error or denial raises an exception
    fail_closed=False,  # fail-open — gateway error logs a warning and continues
)
```

---

## Drop-in Replacement

Swap `ChatOpenAI` for `AIIdentityChatOpenAI` in any existing LangChain chain:

```python
# Before
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o", openai_api_key="sk-...")

# After — adds gateway enforcement and automatic audit logging
from langchain_ai_identity import AIIdentityChatOpenAI
llm = AIIdentityChatOpenAI(
    model="gpt-4o",
    openai_api_key="sk-...",
    agent_id="your-agent-uuid",
    ai_identity_api_key="aid_sk_...",
)
```

All existing LangChain chains, LCEL expressions, and agents work unchanged.

---

## Attach the Callback to Any Chain

If you already have a chain and just want audit logging (without gateway enforcement), attach the callback handler:

```python
from langchain_ai_identity import AIIdentityCallbackHandler

handler = AIIdentityCallbackHandler(
    agent_id="your-agent-uuid",
    api_key="aid_sk_...",
    fail_closed=False,  # log warnings, never crash the chain
)

# Attach to any LangChain object that accepts callbacks
chain = some_existing_chain.with_config(callbacks=[handler])
```

---

## Wrap Tools with Policy Enforcement

Use `AIIdentityToolkit` to add enforcement to any list of tools, independent of the LLM:

```python
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_ai_identity import AIIdentityToolkit

toolkit = AIIdentityToolkit(
    tools=[DuckDuckGoSearchRun(), WikipediaQueryRun()],
    agent_id="your-agent-uuid",
    api_key="aid_sk_...",
)

# Pre-flight check — see what's allowed before you run
for tool_name in ["duckduckgo_search", "wikipedia"]:
    result = toolkit.check_tool_access(tool_name)
    print(tool_name, "→", result["decision"])

# Get the wrapped tools to pass to your agent
safe_tools = toolkit.get_tools()
```

---

## Audit Logs

Every event is logged to an append-only, HMAC-chained audit log. Query it programmatically:

```python
import httpx
from datetime import datetime, timedelta, timezone

start = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()

with httpx.Client() as client:
    resp = client.get(
        "https://ai-identity-api.onrender.com/api/v1/audit",
        params={"agent_id": "your-agent-uuid", "start_date": start},
        headers={"X-API-Key": "aid_sk_..."},
    )
    entries = resp.json()["items"]
    for entry in entries:
        print(entry["event_type"], "→", entry["decision"])
```

### Verify chain integrity

```python
with httpx.Client() as client:
    resp = client.get(
        "https://ai-identity-api.onrender.com/api/v1/audit/verify",
        params={"agent_id": "your-agent-uuid"},
        headers={"X-API-Key": "aid_sk_..."},
    )
    data = resp.json()
    print("Chain valid:", data["valid"])
    print("Entries checked:", data["entries_checked"])
```

If `valid` is `False`, the response includes the exact position of the first hash break — useful for incident investigation.

### Forensics report (SOC 2)

```python
with httpx.Client() as client:
    resp = client.get(
        "https://ai-identity-api.onrender.com/api/v1/audit/report",
        params={
            "agent_id": "your-agent-uuid",
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-12-31T23:59:59Z",
            "format": "json",
        },
        headers={"X-API-Key": "aid_sk_..."},
    )
    report = resp.json()
    print("Chain of custody valid:", report["chain_of_custody"]["valid"])
```

---

## CrewAI Integration

CrewAI tools are LangChain-compatible — wrap them with `AIIdentityToolkit` before passing to `Agent`:

```python
from crewai import Agent, Crew, Task, Process
from crewai_tools import SerperDevTool
from langchain_openai import ChatOpenAI
from langchain_ai_identity import AIIdentityCallbackHandler, AIIdentityToolkit

toolkit = AIIdentityToolkit(
    tools=[SerperDevTool()],
    agent_id="your-agent-uuid",
    api_key="aid_sk_...",
)

researcher = Agent(
    role="Researcher",
    goal="Find information on AI agent identity.",
    backstory="Expert in AI security.",
    tools=toolkit.get_tools(),  # enforced tools
    llm=ChatOpenAI(
        model="gpt-4o",
        callbacks=[AIIdentityCallbackHandler(
            agent_id="your-agent-uuid",
            api_key="aid_sk_...",
        )],
    ),
)
```

See `examples/crewai_integration.py` for the full example.

---

## API Reference

| Class / Function | Description |
|---|---|
| `create_ai_identity_agent()` | Factory: create a fully wired AgentExecutor in one call |
| `AIIdentityChatOpenAI` | Drop-in `ChatOpenAI` with gateway enforcement + auto audit callback |
| `AIIdentityToolkit` | Wraps tool lists with per-call gateway enforcement |
| `AIIdentityCallbackHandler` | Sync LangChain callback that logs to the AI Identity audit API |
| `AIIdentityAsyncCallbackHandler` | Async version of the callback handler |

---

## Configuration Reference

### `create_ai_identity_agent()`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `tools` | `List[BaseTool]` | required | LangChain tools to secure |
| `agent_id` | `str` | required | Agent UUID from AI Identity |
| `ai_identity_api_key` | `str` | required | `aid_sk_...` runtime key |
| `openai_api_key` | `str` | required | OpenAI API key |
| `model` | `str` | `"gpt-4o"` | OpenAI model name |
| `fail_closed` | `bool` | `True` | Raise on denial/error vs. warn-and-continue |
| `ai_identity_timeout` | `float` | `5.0` | Gateway call timeout in seconds |
| `verbose` | `bool` | `False` | Print agent reasoning steps |
| `max_iterations` | `int` | `10` | Max agent reasoning steps |

---

## Links

- [AI Identity Platform](https://ai-identity.co)
- [API Documentation](https://ai-identity-api.onrender.com/docs)
- [Gateway Documentation](https://ai-identity-gateway.onrender.com/docs)
- [GitHub](https://github.com/ai-identity/langchain-ai-identity)
- [Issues & Support](https://github.com/ai-identity/langchain-ai-identity/issues)

---

## License

MIT — see [LICENSE](./LICENSE).
