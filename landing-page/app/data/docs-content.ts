export interface DocSection {
  id: string;
  title: string;
  content: DocBlock[];
}

export type DocBlock =
  | { type: "text"; body: string }
  | { type: "code"; language: string; title?: string; body: string }
  | { type: "steps"; items: { title: string; description: string; code?: string }[] }
  | { type: "cards"; items: { title: string; description: string; icon?: string }[] }
  | { type: "links"; items: { label: string; href: string; description: string }[] };

export const docSections: DocSection[] = [
  {
    id: "quickstart",
    title: "Quickstart",
    content: [
      {
        type: "text",
        body: "Get up and running with AI Identity in under 5 minutes. Follow these four steps to register your first agent, obtain an API key, route traffic through the gateway, and explore forensic logs.",
      },
      {
        type: "steps",
        items: [
          {
            title: "1. Create an Agent",
            description:
              "Register a new AI agent with a unique identity. Every agent gets a cryptographic fingerprint that follows it across every request.",
            code: `curl -X POST https://ai-identity-gateway.onrender.com/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "support-bot",
    "description": "Customer support assistant",
    "allowed_models": ["gpt-4o", "claude-sonnet-4-20250514"]
  }'`,
          },
          {
            title: "2. Get an API Key",
            description:
              "Generate a scoped API key for your agent. Keys can be restricted by model, rate limit, and expiration date.",
            code: `curl -X POST https://ai-identity-gateway.onrender.com/v1/agents/ag_abc123/keys \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "production-key",
    "scopes": ["chat:completions", "embeddings"],
    "rate_limit": 100,
    "expires_in_days": 90
  }'`,
          },
          {
            title: "3. Point Your Gateway",
            description:
              "Replace your LLM provider base URL with the AI Identity gateway. All requests are transparently proxied with identity headers injected.",
            code: `# Instead of calling OpenAI directly:
# POST https://api.openai.com/v1/chat/completions

# Point to the AI Identity gateway:
curl -X POST https://ai-identity-gateway.onrender.com/v1/chat/completions \\
  -H "Authorization: Bearer aid_sk_your_agent_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4o",
    "messages": [
      {"role": "user", "content": "Hello, world!"}
    ]
  }'`,
          },
          {
            title: "4. Explore Forensics",
            description:
              "Every request through the gateway is logged with a tamper-proof audit trail. Query the forensics API to see what your agents have been doing.",
            code: `curl https://ai-identity-gateway.onrender.com/v1/agents/ag_abc123/logs \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -G \\
  -d "limit=10" \\
  -d "since=2025-01-01T00:00:00Z"`,
          },
        ],
      },
    ],
  },
  {
    id: "core-concepts",
    title: "Core Concepts",
    content: [
      {
        type: "text",
        body: "AI Identity is built around four pillars that together provide a comprehensive governance layer for autonomous AI agents.",
      },
      {
        type: "cards",
        items: [
          {
            title: "Identity",
            icon: "fingerprint",
            description:
              "Every AI agent gets a unique, verifiable identity. Identities are cryptographically signed and can be validated by any downstream service. Think of it as a passport for your AI \u2014 it proves who the agent is, who created it, and what it is allowed to do.",
          },
          {
            title: "Policy",
            icon: "shield",
            description:
              "Define fine-grained access policies per agent. Control which models an agent can call, what endpoints it can hit, rate limits, token budgets, and time-of-day restrictions. Policies are evaluated at the gateway before every request is forwarded.",
          },
          {
            title: "Compliance",
            icon: "check",
            description:
              "Automated compliance reporting for EU AI Act, SOC 2, and internal governance frameworks. AI Identity continuously monitors agent behavior and flags anomalies against your defined policies, generating audit-ready reports on demand.",
          },
          {
            title: "Forensics",
            icon: "search",
            description:
              "Full request/response logging with tamper-proof audit trails. Every LLM call is captured with metadata including latency, token usage, model, and agent identity. Logs are immutable and can be exported for external review or incident investigation.",
          },
        ],
      },
    ],
  },
  {
    id: "gateway",
    title: "Gateway Architecture",
    content: [
      {
        type: "text",
        body: "The AI Identity Gateway sits between your application and your LLM providers. It acts as a transparent proxy that injects identity headers, enforces policies, and logs every interaction \u2014 all without changing your existing code.",
      },
      {
        type: "code",
        language: "text",
        title: "Request flow",
        body: `Your App  \u2192  AI Identity Gateway  \u2192  LLM Provider (OpenAI, Anthropic, etc.)
                     \u2502
                     \u251c\u2500 Validate agent identity
                     \u251c\u2500 Check policy (rate limit, model access, budget)
                     \u251c\u2500 Inject audit headers (X-Agent-ID, X-Request-ID)
                     \u251c\u2500 Log request metadata
                     \u2514\u2500 Forward to upstream provider`,
      },
      {
        type: "text",
        body: "The gateway is a drop-in replacement for any OpenAI-compatible API. Simply change your base URL and use your AI Identity agent key instead of a provider key.",
      },
      {
        type: "code",
        language: "python",
        title: "Python \u2014 using the OpenAI SDK with AI Identity",
        body: `from openai import OpenAI

# Point the OpenAI client at the AI Identity gateway
client = OpenAI(
    base_url="https://ai-identity-gateway.onrender.com/v1",
    api_key="aid_sk_your_agent_key",
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarize today's news"}],
)
print(response.choices[0].message.content)`,
      },
      {
        type: "code",
        language: "typescript",
        title: "TypeScript \u2014 using the OpenAI SDK with AI Identity",
        body: `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://ai-identity-gateway.onrender.com/v1",
  apiKey: "aid_sk_your_agent_key",
});

const response = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Summarize today's news" }],
});
console.log(response.choices[0].message.content);`,
      },
    ],
  },
  {
    id: "integrations",
    title: "Integrations",
    content: [
      {
        type: "text",
        body: "AI Identity works with all major agent frameworks. Because the gateway is OpenAI-compatible, integration usually requires changing just one line \u2014 the base URL.",
      },
      {
        type: "code",
        language: "python",
        title: "LangChain",
        body: `from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o",
    base_url="https://ai-identity-gateway.onrender.com/v1",
    api_key="aid_sk_your_agent_key",
)

response = llm.invoke("What is AI Identity?")
print(response.content)`,
      },
      {
        type: "code",
        language: "python",
        title: "CrewAI",
        body: `import os
os.environ["OPENAI_API_BASE"] = "https://ai-identity-gateway.onrender.com/v1"
os.environ["OPENAI_API_KEY"] = "aid_sk_your_agent_key"

from crewai import Agent, Task, Crew

researcher = Agent(
    role="Researcher",
    goal="Find the latest AI governance news",
    backstory="You are an expert AI policy analyst.",
    llm="gpt-4o",
)

task = Task(
    description="Summarize recent developments in AI regulation",
    expected_output="A concise briefing document",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff()
print(result)`,
      },
      {
        type: "code",
        language: "python",
        title: "AutoGen",
        body: `from autogen import AssistantAgent, UserProxyAgent

config_list = [{
    "model": "gpt-4o",
    "base_url": "https://ai-identity-gateway.onrender.com/v1",
    "api_key": "aid_sk_your_agent_key",
}]

assistant = AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list},
)

user_proxy = UserProxyAgent(
    name="user",
    human_input_mode="NEVER",
    code_execution_config=False,
)

user_proxy.initiate_chat(
    assistant, message="Explain how AI identity governance works."
)`,
      },
      {
        type: "code",
        language: "bash",
        title: "Direct cURL",
        body: `# List your agents
curl https://ai-identity-gateway.onrender.com/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY"

# Create a chat completion through the gateway
curl -X POST https://ai-identity-gateway.onrender.com/v1/chat/completions \\
  -H "Authorization: Bearer aid_sk_your_agent_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Check agent usage and forensic logs
curl https://ai-identity-gateway.onrender.com/v1/agents/ag_abc123/usage \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
      },
    ],
  },
  {
    id: "authentication",
    title: "Authentication",
    content: [
      {
        type: "text",
        body: "AI Identity uses API key authentication. There are two types of keys: organization keys (for managing agents and viewing logs) and agent keys (for making LLM requests through the gateway).",
      },
      {
        type: "cards",
        items: [
          {
            title: "Organization Keys",
            icon: "key",
            description:
              "Prefixed with aid_org_. Used for management operations: creating agents, generating agent keys, viewing logs, and configuring policies. Keep these secure and never expose them in client-side code.",
          },
          {
            title: "Agent Keys",
            icon: "bot",
            description:
              "Prefixed with aid_sk_. Scoped to a single agent. Used for making LLM requests through the gateway. Each key inherits the policies attached to its agent. Rotate these regularly.",
          },
        ],
      },
      {
        type: "code",
        language: "bash",
        title: "Authentication header format",
        body: `# Organization-level operations
curl https://ai-identity-gateway.onrender.com/v1/agents \\
  -H "Authorization: Bearer aid_org_your_org_key"

# Agent-level LLM requests
curl -X POST https://ai-identity-gateway.onrender.com/v1/chat/completions \\
  -H "Authorization: Bearer aid_sk_your_agent_key" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]}'`,
      },
    ],
  },
  {
    id: "api-reference",
    title: "API Reference",
    content: [
      {
        type: "text",
        body: "Full interactive API documentation is available in two formats. Both are auto-generated from the OpenAPI spec and stay in sync with the latest deployed version.",
      },
      {
        type: "links",
        items: [
          {
            label: "ReDoc",
            href: "https://api.ai-identity.co/redoc",
            description:
              "Clean, readable API reference with request/response schemas, example payloads, and authentication details. Best for reading and understanding the API.",
          },
          {
            label: "Swagger UI",
            href: "https://api.ai-identity.co/docs",
            description:
              "Interactive API explorer where you can try endpoints directly from the browser. Best for testing and debugging.",
          },
        ],
      },
      {
        type: "text",
        body: "The API follows RESTful conventions. All endpoints accept and return JSON. Timestamps are ISO 8601 in UTC. Pagination uses cursor-based pagination with limit and after parameters.",
      },
      {
        type: "code",
        language: "bash",
        title: "Common API endpoints",
        body: `# Agents
GET    /v1/agents                    # List all agents
POST   /v1/agents                    # Create a new agent
GET    /v1/agents/:id                # Get agent details
PATCH  /v1/agents/:id                # Update an agent
DELETE /v1/agents/:id                # Delete an agent

# Keys
POST   /v1/agents/:id/keys           # Create an agent key
GET    /v1/agents/:id/keys           # List agent keys
DELETE /v1/agents/:id/keys/:key_id   # Revoke a key

# Policies
GET    /v1/policies                  # List policies
POST   /v1/policies                  # Create a policy
PATCH  /v1/policies/:id              # Update a policy

# Forensics / Logs
GET    /v1/agents/:id/logs           # Get agent request logs
GET    /v1/agents/:id/usage          # Get usage summary

# Gateway (OpenAI-compatible)
POST   /v1/chat/completions          # Proxied chat completion
POST   /v1/embeddings                # Proxied embeddings`,
      },
    ],
  },
];
